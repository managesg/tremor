import json
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import r3_relay_cpu_guard as relay_guard, spark_calibration_guard as guard


IDENTITY = "d3" * 32
OTHER_IDENTITY = "e4" * 32
TERMINAL_FORMAT = "{{json .Id}}\n{{json .State}}"


class R3RelayExactCpuStopTests(unittest.TestCase):
    @staticmethod
    def terminal_output(*, identity=IDENTITY, omit=(), **state_overrides):
        state = {"Status": "exited", "Running": False, "Restarting": False, "OOMKilled": False, "Error": "",
                 "ExitCode": 137, **state_overrides}
        for key in omit:
            del state[key]
        return json.dumps(identity) + "\n" + json.dumps(state) + "\n"

    def assert_bounded_docker_call(self, call, expected_command):
        self.assertEqual(call.args[0], expected_command)
        self.assertIs(call.kwargs["check"], True)
        self.assertIs(call.kwargs["capture_output"], True)
        self.assertIs(call.kwargs["text"], True)
        self.assertGreater(call.kwargs["timeout"], 0)

    def test_kill_targets_only_the_full_created_identity(self):
        response = CompletedProcess([], 0, stdout=IDENTITY + "\n")
        with mock.patch.object(relay_guard.subprocess, "run", return_value=response) as docker:
            self.assertIsNone(relay_guard._kill_isolated(IDENTITY))
        docker.assert_called_once()
        self.assert_bounded_docker_call(docker.call_args, [*guard.DOCKER, "kill", "--signal=KILL", IDENTITY])

    def test_untrusted_identity_never_reaches_docker(self):
        for identity in (IDENTITY[:12], IDENTITY.upper(), IDENTITY + "\n", "container-name"):
            with self.subTest(identity=identity), mock.patch.object(relay_guard.subprocess, "run") as docker:
                with self.assertRaises(ValueError):
                    relay_guard._kill_isolated(identity)
                with self.assertRaises(ValueError):
                    relay_guard._isolated_terminal(identity, 137)
                docker.assert_not_called()

    def test_kill_must_acknowledge_exactly_the_same_identity(self):
        for output in ("", OTHER_IDENTITY + "\n", IDENTITY[:12] + "\n", f"{IDENTITY}\n{IDENTITY}\n"):
            with self.subTest(output=output):
                response = CompletedProcess([], 0, stdout=output)
                with mock.patch.object(relay_guard.subprocess, "run", return_value=response) as docker:
                    with self.assertRaises(ValueError):
                        relay_guard._kill_isolated(IDENTITY)
                docker.assert_called_once()
                self.assert_bounded_docker_call(docker.call_args, [*guard.DOCKER, "kill", "--signal=KILL", IDENTITY])

    def test_inspect_proves_exact_exited_container_for_both_terminal_paths(self):
        for exit_code in (0, 137):
            with self.subTest(exit_code=exit_code):
                response = CompletedProcess([], 0, stdout=self.terminal_output(ExitCode=exit_code))
                with mock.patch.object(relay_guard.subprocess, "run", return_value=response) as docker:
                    terminal = relay_guard._isolated_terminal(IDENTITY, exit_code)
                docker.assert_called_once()
                self.assert_bounded_docker_call(docker.call_args,
                                                [*guard.DOCKER, "inspect", "--type", "container", "--format",
                                                 TERMINAL_FORMAT, IDENTITY])
                self.assertEqual(terminal, {"container_id": IDENTITY, "status": "exited",
                                            "exit_code": exit_code, "oom_killed": False})

    def test_inspect_rejects_wrong_identity_running_oom_bad_exit_or_state_error(self):
        cases = (
            ("replacement", self.terminal_output(identity=OTHER_IDENTITY), 137),
            ("running state", self.terminal_output(Status="running"), 137),
            ("running flag", self.terminal_output(Running=True), 137),
            ("restarting flag", self.terminal_output(Restarting=True), 137),
            ("missing restarting flag", self.terminal_output(omit=("Restarting",)), 137),
            ("OOM exit", self.terminal_output(OOMKilled=True), 137),
            ("wrong exit", self.terminal_output(ExitCode=1), 137),
            ("Boolean exit", self.terminal_output(ExitCode=False), 0),
            ("daemon error", self.terminal_output(Error="daemon reported an error"), 137),
            ("malformed JSON", f'"{IDENTITY}"\nnot-json\n', 137),
        )
        for label, output, expected_exit in cases:
            with self.subTest(label=label):
                response = CompletedProcess([], 0, stdout=output)
                with mock.patch.object(relay_guard.subprocess, "run", return_value=response) as docker:
                    with self.assertRaises(ValueError):
                        relay_guard._isolated_terminal(IDENTITY, expected_exit)
                docker.assert_called_once()

    def test_exact_container_stops_require_the_isolated_path(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "uncreated"
            with (mock.patch.object(relay_guard.subprocess, "run") as docker,
                  mock.patch.object(relay_guard.subprocess, "Popen") as process,
                  self.assertRaises(ValueError)):
                relay_guard.run(output, "memory_floor", exact_container_stops=True)
            docker.assert_not_called()
            process.assert_not_called()
            self.assertFalse(output.exists())
