"""Offline tests for ChargePin deployment/rollback; never starts Docker."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[2] / "ops" / "deploy.py"
SPEC = importlib.util.spec_from_file_location("chargepin_deploy", SRC)
deploy_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy_mod)

OLD = "c39e5c50d936d45cade1e880737e3e34ab5ff70a"
NEW = "1" * 40


class DeploymentRollbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        state = Path(self.temp.name)
        self.state_patch = patch.object(deploy_mod, "STATE_DIR", state)
        self.sha_patch = patch.object(deploy_mod, "STABLE_SHA", state / "last_successful_sha")
        self.state_patch.start()
        self.sha_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.addCleanup(self.sha_patch.stop)
        # deploy() intentionally blocks actual Windows deployment. These are
        # offline unit tests, so emulate only the Linux lock dependency and
        # keep Docker fully mocked below.
        self.platform_patch = patch.object(deploy_mod.os, "name", "posix")
        self.fcntl_patch = patch.dict(
            sys.modules,
            {"fcntl": types.SimpleNamespace(LOCK_EX=1, flock=lambda *_args: None)},
        )
        self.platform_patch.start()
        self.fcntl_patch.start()
        self.addCleanup(self.platform_patch.stop)
        self.addCleanup(self.fcntl_patch.stop)
        deploy_mod.STABLE_SHA.write_text(OLD + "\n", encoding="utf-8")
        self.calls = []

    def fake_compose(self, sha, *args):
        self.calls.append((sha, args))

    def failure(self):
        return subprocess.CalledProcessError(1, ["docker", "compose"])

    def test_failed_image_pull_leaves_running_deployment_untouched(self):
        def fail_pull(sha, *args):
            self.fake_compose(sha, *args)
            raise self.failure()
        with patch.object(deploy_mod, "compose", side_effect=fail_pull):
            self.assertEqual(1, deploy_mod.deploy(NEW))
        self.assertEqual([(NEW, ("pull", "backend", "frontend"))], self.calls)
        self.assertEqual(OLD, deploy_mod.STABLE_SHA.read_text().strip())

    def test_unhealthy_new_release_restores_previous_sha(self):
        def unhealthy(sha, *args):
            self.fake_compose(sha, *args)
            if sha == NEW and args[0] == "up":
                raise self.failure()
        with patch.object(deploy_mod, "compose", side_effect=unhealthy):
            self.assertEqual(1, deploy_mod.deploy(NEW))
        self.assertEqual(
            [(NEW, "pull"), (NEW, "up"), (OLD, "pull"), (OLD, "up")],
            [(sha, args[0]) for sha, args in self.calls],
        )
        for sha, args in self.calls:
            if args[0] == "up":
                self.assertEqual(("backend", "frontend"), args[4:6])
                self.assertIn("--no-deps", args)
        self.assertEqual(OLD, deploy_mod.STABLE_SHA.read_text().strip())

    def test_rollback_failure_keeps_last_successful_sha(self):
        def fail_both(sha, *args):
            self.fake_compose(sha, *args)
            if args[0] == "up":
                raise self.failure()
        with patch.object(deploy_mod, "compose", side_effect=fail_both):
            self.assertEqual(1, deploy_mod.deploy(NEW))
        self.assertEqual(OLD, deploy_mod.STABLE_SHA.read_text().strip())
        self.assertEqual(4, len(self.calls))

    def test_success_records_new_sha(self):
        with patch.object(deploy_mod, "compose", side_effect=self.fake_compose):
            self.assertEqual(0, deploy_mod.deploy(NEW))
        self.assertEqual(NEW, deploy_mod.STABLE_SHA.read_text().strip())
        self.assertEqual(2, len(self.calls))


if __name__ == "__main__":
    unittest.main()
