import hashlib
import json
from pathlib import Path
import signal
from tempfile import TemporaryDirectory
import unittest

from lab import r3_relay_cpu_guard as guard


class R3RelayCPUGuardTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory()))

    def run_and_check_identity(self, scenario, *, returncode):
        root = self.scratch / scenario
        report = guard.run(root, scenario)
        self.assertEqual(report["stop"], scenario)
        self.assertEqual(report["child_returncode"], returncode)
        self.assertIs(report["child_reaped"], True)
        self.assertEqual(report["gpu_jobs"], 0)
        names = {"board_sha256": "board.jsonl", "generation_sha256": "board.relay-generation.jsonl",
                 "host_response_sha256": "host.jsonl", "manifest_sha256": "plan.json"}
        self.assertEqual(report["artifacts"], {
            key: hashlib.sha256((root / name).read_bytes()).hexdigest() for key, name in names.items()
        })
        self.assertEqual(json.loads((root / "guard-terminal.json").read_bytes()), report)
        return root, report

    def test_completed_child_yields_the_expected_relay_score(self):
        root, report = self.run_and_check_identity("completed", returncode=0)
        self.assertFalse((root / "guard-stop.json").exists())
        self.assertEqual(report["export"]["status"], "complete")
        self.assertEqual(report["export"]["readout"]["first_generation_relay_mean"], 1.0)

    def test_completed_controls_keep_their_own_status_and_no_planted_readout(self):
        for mode, status in (("clean", "no_planted_roots"), ("trigger_only", "trigger_only")):
            with self.subTest(mode=mode):
                root = self.scratch / mode
                report = guard.run(root, "completed", mode=mode)
                self.assertEqual(report["stop"], "completed")
                self.assertEqual(report["child_returncode"], 0)
                self.assertEqual(json.loads((root / "plan.json").read_bytes())["mode"], mode)
                self.assertEqual(report["export"]["status"], status)
                self.assertIsNone(report["export"]["readout"])
                self.assertEqual(report["export"]["usage"]["output_tokens"], 48)

    def test_injected_limits_kill_and_reap_without_a_relay_score(self):
        for scenario in ("memory_floor", "wall_limit"):
            with self.subTest(scenario=scenario):
                root, report = self.run_and_check_identity(scenario, returncode=-signal.SIGKILL)
                decision = json.loads((root / "guard-stop.json").read_bytes())
                self.assertEqual(decision, {"stop": scenario, "pid": report["pid"],
                                            "sample": report["minimum_sample_kib"]})
                export = report["export"]
                self.assertEqual(export["status"], "incomplete_prefix")
                self.assertEqual(export["open_opportunity"], 1)
                self.assertIsNone(export["readout"])
                self.assertEqual(export["worker_usage"]["output_tokens"], 8)
                if scenario == "memory_floor":
                    self.assertIsNone(export["host_only_usage"])
                    self.assertEqual(export["unknown_attempts"], 1)
                else:
                    self.assertEqual(export["host_only_usage"]["output_tokens"], 8)
                    self.assertEqual(export["unknown_attempts"], 0)

    def test_unknown_scenario_is_rejected_without_creating_an_output(self):
        root = self.scratch / "unknown"
        with self.assertRaises(ValueError):
            guard.run(root, "unknown")
        self.assertFalse(root.exists())
