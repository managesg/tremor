import hashlib
import json
from pathlib import Path
from shutil import copytree
import signal
from tempfile import TemporaryDirectory
import unittest

from lab import l5_matrix_partial as partial
from lab.l5_grader_custody import digest as record_digest


class L5MatrixPartialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = Path(cls.enterClassContext(TemporaryDirectory()))
        cls.root = scratch / "prefix"
        cls.index_sha256 = partial.run(cls.root, seed=17)
        cls.scratch = scratch

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def read_tape(path):
        return [json.loads(line) for line in path.read_bytes().splitlines()]

    @staticmethod
    def write_tape(path, rows):
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

    def repin_tape(self, root, tape):
        index_path = root / "index.json"
        index = json.loads(index_path.read_bytes())
        index["files"][tape.relative_to(root).as_posix()] = self.digest(tape)
        index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
        return self.digest(index_path)

    def test_interrupted_cpu_run_preserves_census_without_comparison(self):
        self.assertEqual(self.index_sha256, self.digest(self.root / "index.json"))
        report = partial.verify(self.root, index_sha256=self.index_sha256)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["completed_arms"], 1)
        self.assertEqual(report["started_arms"], 2)
        self.assertEqual(report["planned_arms"], 20)
        self.assertEqual(report["returned_attempts"], 5)
        self.assertEqual(report["open_attempts"], 1)
        self.assertEqual(report["unstarted_arms"], 18)
        self.assertIsNone(report["comparison"])
        self.assertIs(report["scientific_n2_frozen"], False)
        self.assertEqual(report["child_returncode"], -signal.SIGKILL)

        matrix = self.root / "matrix"
        self.assertEqual(sorted(path.name for path in matrix.glob("arm-*")), ["arm-00", "arm-01"])
        first = self.read_tape(matrix / "arm-00" / "work-dispatch.jsonl")
        second = self.read_tape(matrix / "arm-01" / "work-dispatch.jsonl")
        self.assertEqual([row["event"] for row in first], ["attempt", "result"] * 4)
        self.assertEqual([row["event"] for row in second], ["attempt", "result", "attempt"])
        self.assertEqual(second[-1]["ordinal"], 1)

        index = json.loads((self.root / "index.json").read_bytes())
        stop_path = self.root / "host-stop.json"
        stop = json.loads(stop_path.read_bytes())
        self.assertEqual(index["stop_sha256"], self.digest(stop_path))
        self.assertEqual(index["plan_sha256"], self.digest(self.root / "fixture-plan.json"))
        self.assertEqual(stop["plan_sha256"], index["plan_sha256"])
        self.assertGreater(stop["pid"], 1)
        self.assertEqual(stop["returncode"], -signal.SIGKILL)
        self.assertEqual(stop["arm_id"], "arm-01")
        self.assertEqual(stop["ordinal"], 1)
        self.assertEqual(stop["stage"], "pre_dispatch")

    def test_wrong_external_index_pin_is_rejected(self):
        with self.assertRaises(ValueError):
            partial.verify(self.root, index_sha256="0" * 64)

    def test_omitted_known_return_is_rejected_after_repinning(self):
        root = Path(copytree(self.root, self.scratch / "missing-return"))
        tape = root / "matrix/arm-01/work-dispatch.jsonl"
        rows = self.read_tape(tape)
        self.assertEqual(rows[1]["event"], "result")
        self.write_tape(tape, [rows[0], rows[2]])
        with self.assertRaisesRegex(ValueError, "partial matrix differs from exact stopped replay"):
            partial.verify(root, index_sha256=self.repin_tape(root, tape))

    def test_forged_return_for_open_attempt_is_rejected_after_repinning(self):
        root = Path(copytree(self.root, self.scratch / "forged-return"))
        tape = root / "matrix/arm-01/work-dispatch.jsonl"
        rows = self.read_tape(tape)
        opened = dict(rows[-1])
        self.assertEqual(opened.pop("event"), "attempt")
        forged = {**rows[1], "ordinal": opened["ordinal"], "attempt_sha256": record_digest(opened)}
        self.write_tape(tape, [*rows, forged])
        with self.assertRaisesRegex(ValueError, "partial matrix differs from exact stopped replay"):
            partial.verify(root, index_sha256=self.repin_tape(root, tape))

    def test_relabelled_host_stop_cannot_bind_a_settled_attempt(self):
        root = Path(copytree(self.root, self.scratch / "relabelled-stop"))
        stop_path = root / "host-stop.json"
        stop = json.loads(stop_path.read_bytes())
        stop["ordinal"] = 0
        stop_path.write_text(json.dumps(stop, sort_keys=True) + "\n", encoding="utf-8")
        index_path = root / "index.json"
        index = json.loads(index_path.read_bytes())
        index["stop_sha256"] = self.digest(stop_path)
        index_path.write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "host stop differs from the pinned interruption"):
            partial.verify(root, index_sha256=self.digest(index_path))
