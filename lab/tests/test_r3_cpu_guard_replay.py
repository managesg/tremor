from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import signal
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import r3_cpu_guard_replay, spark_calibration_guard as guard


class CpuGuardReplayTests(unittest.TestCase):
    def test_completed_and_killed_children_have_distinct_export_eligibility(self):
        with TemporaryDirectory() as scratch:
            for scenario in r3_cpu_guard_replay.SCENARIOS:
                with self.subTest(scenario=scenario):
                    root = Path(scratch) / scenario
                    report = r3_cpu_guard_replay.run(root, scenario)
                    stopped = scenario != "completed"
                    self.assertEqual(report["stop"], scenario)
                    self.assertEqual(report["child_returncode"], -signal.SIGKILL if stopped else 0)
                    self.assertTrue(report["child_reaped"])
                    self.assertEqual(report["export"]["completed_pairs"], int(not stopped))
                    self.assertEqual([arm["unknown_usage_attempts"] for arm in report["export"]["arms"]],
                                     [0, int(stopped)])
                    self.assertEqual(json.loads((root / "guard-terminal.json").read_bytes()), report)
                    if stopped:
                        decision = json.loads((root / "guard-stop.json").read_bytes())
                        self.assertEqual((decision["stop"], decision["pid"]), (scenario, report["pid"]))

    def test_success_first_observed_after_the_deadline_is_not_credited(self):
        elapsed, events = [0], []

        class Child:
            def poll(self):
                return 0 if elapsed[0] > guard.WALL_SECONDS else None

        def missed_poll(_seconds):
            elapsed[0] = guard.WALL_SECONDS + 1

        result = guard.watch(Child(), lambda: events.append("kill"), lambda: guard.FLOOR_KIB + 10,
                             lambda: elapsed[0], missed_poll,
                             on_stop=lambda reason, _: events.append(reason))
        self.assertEqual((result[0], events), ("wall_limit", ["wall_limit"]))

    def test_stop_reason_is_recorded_before_the_termination_adapter(self):
        events = []

        class Child:
            def poll(self):
                return None

        def failing_kill():
            events.append("kill")
            raise RuntimeError("termination adapter failed")

        with self.assertRaisesRegex(RuntimeError, "termination adapter failed"):
            guard.watch(Child(), failing_kill, lambda: guard.FLOOR_KIB, lambda: 0, lambda _: None,
                        on_stop=lambda reason, _: events.append(reason))
        self.assertEqual(events, ["memory_floor", "kill"])

    def test_launch_deadline_does_not_restart_when_watch_begins(self):
        class DelayedAttach:
            def poll(self):
                return 0

        stops = []
        result = guard.watch(DelayedAttach(), lambda: self.fail("already exited"),
                             lambda: guard.FLOOR_KIB + 10, lambda: 101, lambda _: None,
                             deadline=100, on_stop=lambda reason, _: stops.append(reason))
        self.assertEqual((result[0], stops), ("wall_limit", ["wall_limit"]))

    def test_docker_stop_decision_survives_a_failed_kill_adapter(self):
        output = io.StringIO()
        with (
            mock.patch.object(guard, "available_kib", side_effect=[guard.ADMISSION_KIB, guard.ADMISSION_KIB,
                                                                  guard.FLOOR_KIB]),
            mock.patch.object(guard, "claim_receipt"),
            mock.patch.object(guard, "cleanup", return_value=False),
            mock.patch.object(guard.subprocess, "Popen") as attach,
            mock.patch.object(guard.subprocess, "run", side_effect=[mock.Mock(), RuntimeError("fixture kill failed")]),
            redirect_stdout(output),
            self.assertRaisesRegex(RuntimeError, "fixture kill failed"),
        ):
            attach.return_value.poll.return_value = None
            guard._run_calibration("fixture-test", {})
        decision, terminal = map(json.loads, output.getvalue().splitlines())
        self.assertEqual(decision["watchdog_decision"], "memory_floor")
        self.assertEqual(decision["admission_id"], terminal["admission_id"])
        self.assertEqual(decision["container"], terminal["container"])
        self.assertNotIn("stop", terminal)
