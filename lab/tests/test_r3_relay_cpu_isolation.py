from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import r3_l2_relay_replay as replay, r3_relay_cpu_guard as relay_guard, spark_calibration_guard


REPO = Path(relay_guard.__file__).resolve().parent.parent


def options(command, name):
    values = []
    for index, arg in enumerate(command):
        if arg == name:
            values.append(command[index + 1])
        elif arg.startswith(name + "="):
            values.append(arg.split("=", 1)[1])
    return values


class R3RelayCpuIsolationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.export = self.root / "export"
        self.export.mkdir()
        self.board = self.export / "board.jsonl"
        self.plan = self.root / "plan.json"
        self.plan.write_bytes(b"{}")
        self.pin = hashlib.sha256(self.plan.read_bytes()).hexdigest()

    def command(self):
        with (
            mock.patch.object(relay_guard.subprocess, "run", side_effect=AssertionError("called Docker")),
            mock.patch.object(relay_guard.subprocess, "Popen", side_effect=AssertionError("started Docker")),
        ):
            return relay_guard._isolated_command(self.root, self.board, self.plan, self.pin)

    def test_worker_command_uses_pinned_cpu_only_isolation(self):
        command = self.command()
        self.assertEqual(command[:len(spark_calibration_guard.DOCKER) + 1],
                         [*spark_calibration_guard.DOCKER, "create"])
        self.assertEqual(command.count(spark_calibration_guard.IMAGE), 1)
        self.assertIn(self.pin, command)
        flags = {arg.split("=", 1)[0] for arg in command if arg.startswith("-")}
        self.assertTrue({"--gpus", "--device", "--privileged"}.isdisjoint(flags))
        self.assertEqual(options(command, "--runtime"), ["runc"])
        self.assertEqual(options(command, "--pull"), ["never"])
        self.assertEqual(options(command, "--network"), ["none"])
        self.assertIn("--read-only", command)
        self.assertEqual(options(command, "--user"), [f"{os.getuid()}:{os.getgid()}"])
        self.assertEqual(options(command, "--cap-drop"), ["ALL"])
        self.assertTrue(any(value in ("no-new-privileges", "no-new-privileges=true")
                            for value in options(command, "--security-opt")))
        self.assertEqual(options(command, "--memory"), ["128m"])

    def test_only_worker_inputs_and_export_are_bind_mounted(self):
        command = self.command()
        self.assertFalse(options(command, "--volume") or options(command, "-v"))
        observed = {}
        destinations = set()
        for raw in options(command, "--mount"):
            fields = dict(part.split("=", 1) if "=" in part else (part, True) for part in raw.split(","))
            self.assertEqual(fields["type"], "bind")
            source = Path(fields.get("source", fields.get("src")))
            destination = fields.get("target", fields.get("dst", fields.get("destination")))
            self.assertIsInstance(destination, str)
            self.assertNotIn(source, observed)
            self.assertNotIn(destination, destinations)
            destinations.add(destination)
            observed[source] = (destination, fields.get("readonly", fields.get("ro")) in (True, "true"))
        self.assertEqual(observed, {REPO / "lab": ("/fixture/lab", True), REPO / "src": ("/fixture/src", True),
                                    self.plan: ("/plan.json", True), self.export: ("/export", False)})
        for path in (self.root, self.root / "host.jsonl", self.root / "guard-stop.json",
                     self.root / "guard-terminal.json", self.root / "worker.stderr"):
            self.assertNotIn(path, observed)

    def test_output_beneath_a_readonly_source_is_refused_before_creating_it(self):
        for source in (REPO / "lab", REPO / "src"):
            with (
                self.subTest(source=source),
                mock.patch.object(Path, "mkdir", side_effect=AssertionError("created protected output")) as mkdir,
                mock.patch.object(relay_guard.subprocess, "run", side_effect=AssertionError("called Docker")),
                mock.patch.object(relay_guard.subprocess, "Popen", side_effect=AssertionError("started Docker")) as popen,
            ):
                for scenario in ("completed", "memory_floor"):
                    with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                        relay_guard.run(source / "_isolated_relay_should_not_create", scenario, isolated=True)
                mkdir.assert_not_called()
                popen.assert_not_called()

    def test_isolated_fault_injection_is_refused_before_creating_output(self):
        output = self.root / "unused"
        with (
            mock.patch.object(relay_guard.subprocess, "run", side_effect=AssertionError("called Docker")),
            mock.patch.object(relay_guard.subprocess, "Popen", side_effect=AssertionError("started Docker")),
            self.assertRaises(ValueError),
        ):
            relay_guard.run(output, "memory_floor", isolated=True)
        self.assertFalse(output.exists())

    def test_export_reader_checks_file_type_link_count_and_size_before_reading(self):
        self.board.write_bytes(b"bounded artifact\n")
        self.assertEqual(replay._artifact_bytes(self.board), b"bounded artifact\n")
        symlink, fifo, hard_link, oversized = (self.export / name for name in
                                                ("symlink", "fifo", "hard-link", "oversized"))
        symlink.symlink_to(self.board)
        os.mkfifo(fifo)
        os.link(self.board, hard_link)
        with oversized.open("wb") as stream:
            stream.truncate(replay.FIXTURE_BYTE_LIMIT + 1)

        original_open, original_fdopen = os.open, os.fdopen

        def safe_open(path, flags, *args, **kwargs):
            self.assertTrue(flags & os.O_NOFOLLOW)
            self.assertTrue(flags & os.O_NONBLOCK)
            return original_open(path, flags, *args, **kwargs)

        @contextmanager
        def metadata_only(fd, *args, **kwargs):
            with original_fdopen(fd, *args, **kwargs) as stream:
                yield mock.Mock(wraps=stream, read=mock.Mock(side_effect=AssertionError("read unsafe artifact")))

        for path in (symlink, fifo, hard_link, oversized):
            with (
                self.subTest(path=path.name),
                mock.patch.object(replay.os, "open", side_effect=safe_open),
                mock.patch.object(replay.os, "fdopen", side_effect=metadata_only),
                self.assertRaises((OSError, ValueError)),
            ):
                replay._artifact_bytes(path)
