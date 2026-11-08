"""Server operations contracts: platform (Kubernetes) and Auto Healing."""
import unittest

from dashboard_data import evaluate_compliance
from ops_contract import healing_stats, normalize_healing, normalize_platform, platform_ready


class PlatformContractTests(unittest.TestCase):
    def test_secret_values_and_unknown_kinds_never_survive(self):
        platform = normalize_platform({
            "source": "kubernetes", "namespace": "chargepin", "observed_at": "2026-11-08T00:00:00Z",
            "workloads": [{"kind": "Deployment", "name": "chargepin-backend", "desired": 1, "ready": 1,
                           "image": "ghcr.io/ac9989/chargepin-backend:sha-abc", "restarts": 0},
                          {"kind": "Job", "name": "ignored"}],
            "config": [{"kind": "Secret", "name": "chargepin-secrets", "keys": 6, "data": {"OPENAI_API_KEY": "sk-x"}}],
        })
        self.assertEqual([item["name"] for item in platform["workloads"]], ["chargepin-backend"])
        self.assertNotIn("sk-x", str(platform))
        self.assertTrue(platform_ready(platform))

    def test_missing_or_partial_replicas_are_not_ready(self):
        self.assertIsNone(normalize_platform({"source": "unknown"}))
        self.assertFalse(platform_ready(None))
        partial = normalize_platform({"source": "kubernetes", "workloads": [
            {"kind": "Deployment", "name": "chargepin-frontend", "desired": 2, "ready": 1}]})
        self.assertFalse(platform_ready(partial))


class HealingContractTests(unittest.TestCase):
    def test_recovery_rate_comes_only_from_recorded_events(self):
        healing = normalize_healing({"policy": {"mode": "apply", "consecutive_unhealthy": 2}, "events": [
            {"timestamp_utc": "2026-11-08T00:00:00+00:00", "event": "restart_attempt", "container": "fe"},
            {"timestamp_utc": "2026-11-08T00:00:09+00:00", "event": "recovered", "duration_seconds": 8.48},
            {"timestamp_utc": "2026-11-08T00:10:00+00:00", "event": "restart_attempt"},
            {"timestamp_utc": "2026-11-08T00:12:00+00:00", "event": "recovery_timeout"},
            {"timestamp_utc": "bad", "event": "recovered"},
            {"timestamp_utc": "2026-11-08T00:13:00+00:00", "event": "unknown"},
        ]})
        stats = healing_stats(healing)
        self.assertEqual((stats["attempts"], stats["recovered"], stats["timeouts"]), (2, 1, 1))
        self.assertEqual(stats["rate"], 50.0)
        self.assertEqual(stats["average_seconds"], 8.48)
        self.assertIsNone(healing_stats(None)["rate"])

    def test_live_platform_and_healing_only_promote_implemented_items(self):
        reference = {"items": [{"id": "R-2", "status": "미착수", "live": "k8s_ready"},
                               {"id": "R-2b", "status": "구현", "live": "k8s_ready"},
                               {"id": "R-5", "status": "부분", "live": "healing"}]}
        items = {item["id"]: item for item in evaluate_compliance(
            reference, {"k8s_ready": True, "healing": {"recovered": 1, "attempts": 1}})}
        self.assertEqual(items["R-2"]["status"], "미착수")
        self.assertEqual(items["R-2b"]["status"], "충족")
        self.assertEqual(items["R-5"]["status"], "부분")
        self.assertIn("복구 1건", items["R-5"]["live_note"])


if __name__ == "__main__":
    unittest.main()
