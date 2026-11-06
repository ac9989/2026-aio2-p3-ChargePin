"""Tests for watcher policy. No Docker daemon is used."""
import importlib.util
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[2] / "ops" / "autoheal.py"
spec = importlib.util.spec_from_file_location("chargepin_autoheal", SRC)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WatcherTests(unittest.TestCase):
    def setup_watcher(self, *, apply=True, **kwargs):
        self.events = []
        self.restarts = []
        self.watcher = module.Watcher(
            "test-frontend", apply=apply,
            emit=lambda event, container, **details: self.events.append((event, details)),
            restart=lambda name: self.restarts.append(name),
            **kwargs,
        )
        return self.watcher

    def event_names(self):
        return [name for name, _ in self.events]

    def test_healthy_never_restarted(self):
        w = self.setup_watcher()
        w.step("running", "healthy", 100)
        w.step("running", "healthy", 115)
        self.assertFalse(self.restarts)

    def test_single_unhealthy_does_not_restart(self):
        w = self.setup_watcher()
        w.step("running", "unhealthy", 100)
        self.assertEqual([], self.restarts)
        w.step("running", "healthy", 115)
        w.step("running", "unhealthy", 130)
        self.assertEqual([], self.restarts)

    def test_two_unhealthy_triggers_restart_and_measure_recovery(self):
        w = self.setup_watcher()
        w.step("running", "unhealthy", 100)
        w.step("running", "unhealthy", 115)
        self.assertEqual(["test-frontend"], self.restarts)
        w.step("running", "starting", 130)
        w.step("running", "healthy", 145)
        self.assertIn("recovered", self.event_names())
        d = next(detail for event, detail in self.events if event == "recovered")
        self.assertEqual(30, d["duration_seconds"])

    def test_dry_run_does_not_restart(self):
        w = self.setup_watcher(apply=False)
        for t in (100, 115, 130):
            w.step("running", "unhealthy", t)
        self.assertEqual([], self.restarts)
        self.assertEqual(1, self.event_names().count("dry_run_would_restart"))

    def test_stopped_not_restarted(self):
        w = self.setup_watcher()
        for t in (100, 115, 130):
            w.step("exited", "unhealthy", t)
        self.assertEqual([], self.restarts)

    def test_starting_not_restarted(self):
        w = self.setup_watcher()
        for t in (100, 115, 130):
            w.step("running", "starting", t)
        self.assertEqual([], self.restarts)

    def test_rate_limit(self):
        w = self.setup_watcher(max_restarts=1, cooldown=0)
        w.step("running", "unhealthy", 100)
        w.step("running", "unhealthy", 115)
        w.step("running", "healthy", 130)
        w.step("running", "unhealthy", 145)
        w.step("running", "unhealthy", 160)
        self.assertEqual(1, len(self.restarts))
        self.assertIn("restart_rate_limited", self.event_names())

    def test_cooldown(self):
        w = self.setup_watcher(max_restarts=3, cooldown=120)
        w.step("running", "unhealthy", 100)
        w.step("running", "unhealthy", 115)
        w.step("running", "healthy", 130)
        w.step("running", "unhealthy", 145)
        w.step("running", "unhealthy", 160)
        self.assertEqual(1, len(self.restarts))
        self.assertIn("restart_cooldown", self.event_names())

    def test_recovery_timeout(self):
        w = self.setup_watcher(recovery_timeout=20, cooldown=120)
        w.step("running", "unhealthy", 100)
        w.step("running", "unhealthy", 115)
        w.step("running", "starting", 140)
        self.assertIn("recovery_timeout", self.event_names())
        self.assertEqual(1, len(self.restarts))


if __name__ == "__main__":
    unittest.main()
