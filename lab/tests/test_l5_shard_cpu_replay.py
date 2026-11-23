from contextlib import contextmanager
from itertools import count
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from lab import l5_shard_cpu_replay as replay


class L5ShardCpuReplayTests(unittest.TestCase):
    def setUp(self):
        self.output = Path(self.enterContext(TemporaryDirectory())).resolve() / "replay"

    def test_every_worker_receives_one_arm_and_fresh_inventory(self):
        launches, children, observations = [], [], []
        tokens = count()

        @contextmanager
        def launch(worker_path):
            self.assertEqual(worker_path, self.output / "worker.py")
            identity = f"{len(launches) + 1:064x}"
            launches.append(identity)
            yield identity, {"network": "none"}

        @contextmanager
        def start(command, **options):
            self.assertEqual(command, [*replay.guard.DOCKER, "start", "--attach", "--interactive", launches[-1]])
            self.assertEqual(options["stderr"], replay.subprocess.DEVNULL)
            child = object()
            children.append(child)
            yield child

        def exercise(inventory, worker, sessions, child):
            self.assertIs(child, children[-1])
            observations.append((inventory, worker, sessions))
            return {"sessions": []}

        with (
            mock.patch.object(replay.os, "geteuid", return_value=1000),
            mock.patch.object(replay.guard, "available_kib", return_value=replay.guard.FLOOR_KIB + 1) as memory,
            mock.patch.object(replay.broker, "token_hex", side_effect=lambda width: f"{next(tokens):0{2 * width}x}"),
            mock.patch.object(replay, "_docker", side_effect=AssertionError("called real Docker")),
            mock.patch.object(replay, "_isolated_worker", side_effect=launch),
            mock.patch.object(replay.subprocess, "Popen", side_effect=start),
            mock.patch.object(replay, "_exercise", side_effect=exercise),
            mock.patch.object(replay.guard, "_reap_attachment") as reap,
        ):
            report = replay.run(self.output)

        expected = [(size, condition, f"a{index}") for size in (4, 8)
                    for condition in replay.broker.CONDITIONS for index in range(size)]
        self.assertEqual(len(launches), 48)
        self.assertEqual(memory.call_count, len(launches))
        self.assertEqual(reap.call_args_list, [mock.call(child) for child in children])
        self.assertEqual([row["container_id"] for row in report["rows"]], launches)
        self.assertEqual([(row["team_size"], row["condition"], row["worker"]) for row in report["rows"]], expected)
        by_arm = {}
        for (size, condition, worker), (inventory, actual_worker, sessions) in zip(expected, observations, strict=True):
            self.assertEqual(actual_worker, worker)
            self.assertEqual([(row["condition"], row["phase"]) for row in sessions],
                             [(condition, "pre"), (condition, "post")])
            self.assertEqual([row["own_item"] for row in sessions],
                             [inventory.item_ids[worker, phase] for phase in replay.broker.PHASES])
            self.assertIs(by_arm.setdefault((size, condition), inventory), inventory)

        self.assertEqual(len({id(inventory) for inventory in by_arm.values()}), 8)
        self.assertEqual(sum(len(inventory.item_ids) for inventory in by_arm.values()),
                         len({item for inventory in by_arm.values() for item in inventory.item_ids.values()}))
        self.assertEqual(sum(len(inventory.canaries) for inventory in by_arm.values()),
                         len({value for inventory in by_arm.values() for value in inventory.canaries.values()}))

    def test_memory_floor_refuses_to_create_or_attach_a_worker(self):
        with (
            mock.patch.object(replay.os, "geteuid", return_value=1000),
            mock.patch.object(replay.guard, "available_kib", return_value=replay.guard.FLOOR_KIB),
            mock.patch.object(replay, "_isolated_worker") as launch,
            mock.patch.object(replay.subprocess, "Popen") as attach,
            self.assertRaisesRegex(ValueError, "Spark memory floor blocks CPU shard replay"),
        ):
            replay.run(self.output)
        launch.assert_not_called()
        attach.assert_not_called()
        self.assertFalse((self.output / "report.json").exists())

    def test_short_pipe_write_is_refused_before_flush(self):
        stream = mock.Mock()
        stream.write.return_value = 1
        with self.assertRaisesRegex(ValueError, "incomplete L5 host transcript write"):
            replay._send(stream, {"value": "fixture"})
        stream.write.assert_called_once_with(b'{"value":"fixture"}\n')
        stream.flush.assert_not_called()
