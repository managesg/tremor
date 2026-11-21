import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_host_response, r3_l2_completion_receipt, r3_l2_relay_generation, spark_calibration_guard
from lab.spark_decision import Generation


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BoundCompletionTests(unittest.TestCase):
    def test_matching_receipts_cannot_rebind_the_replayed_worker_to_another_plan(self):
        with TemporaryDirectory() as scratch:
            bundle = Path(scratch)
            complete = bundle / "completed"
            board = complete / "export/board.jsonl"
            board.parent.mkdir(parents=True)
            host = complete / "host.jsonl"
            plan = complete / "plan.json"
            spec = {"manifest_id": "reviewed", "mode": "planted", "renderer": "json-dumps-v1",
                    "schedule": r3_l2_relay_generation.SCHEDULE, "caps": {"input": 20, "output": 16}}
            plan.write_text(json.dumps(spec))
            def abstain(_prompt, **_caps):
                return Generation('{"kind":"abstain"}', 1, 1, 10, False)

            with l2_host_response.capture(host, abstain) as source:
                export = r3_l2_relay_generation.run(
                    board, generate=source, render=json.dumps,
                    max_input_tokens=20, max_output_tokens=16, plan_sha256=digest(plan),
                )
            export["host_responses_verified"] = True
            export["readout"].pop("trace")

            receipt = {
                "evidence": "scripted_cpu_guard_parent_tape", "stop": "completed",
                "gpu_jobs": 0, "isolated_cpu": True, "container_removed": True,
                "child_reaped": True, "child_returncode": 0, "injected_limit": None,
                "watchdog_stop_sha256": None, "container_id": "a" * 64, "export": export,
                "isolation": {
                    "container_id": "a" * 64, "image": spark_calibration_guard.IMAGE,
                    "network": "none", "cpu_limit": 1, "memory_bytes": 128 * 1024 * 1024,
                    "capabilities_dropped": ["ALL"],
                    "mounts": {"/export": "rw", "/fixture/lab": "ro", "/fixture/src": "ro", "/plan.json": "ro"},
                },
                "artifacts": {
                    "board_sha256": digest(board), "host_response_sha256": digest(host),
                    "generation_sha256": digest(board.with_suffix(".relay-generation.jsonl")),
                },
            }

            def check():
                receipt["artifacts"]["manifest_sha256"] = digest(plan)
                summary, terminal = bundle / "completed.report.json", complete / "guard-terminal.json"
                summary.write_text(json.dumps(receipt))
                terminal.write_text(json.dumps(receipt) + "\n")
                return r3_l2_completion_receipt.verify_bound(
                    bundle, completion_sha256=digest(summary), terminal_sha256=digest(terminal),
                    plan_sha256=digest(plan),
                )

            self.assertTrue(check()["cpu_export_replayed"])
            plan.write_text(json.dumps({**spec, "manifest_id": "different"}))
            with self.assertRaisesRegex(ValueError, "relay start does not bind"):
                check()
