from copy import deepcopy
import hashlib
from itertools import combinations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l5_grader_custody as grader, l5_matrix_custody as matrix_custody


class L5MatrixCustodyTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(self.enterContext(TemporaryDirectory()))

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    def fixture(self, name):
        root = self.scratch / name
        pin = matrix_custody.run(root, seed=0)
        self.assertEqual(pin, self.digest((root / "custody.json").read_bytes()))
        return root, pin

    @staticmethod
    def tape_paths(root):
        return sorted((root / "matrix").glob("arm-*/work-dispatch.jsonl"))

    @staticmethod
    def records(path):
        return [json.loads(line) for line in path.read_bytes().splitlines()]

    def test_default_capsule_replays_every_work_attempt_with_blind_input(self):
        root, pin = self.fixture("capsule")
        report = matrix_custody.verify(root, custody_sha256=pin)
        self.assertEqual(report["arms"], 20)
        self.assertEqual(report["work_attempts"], 120)
        self.assertEqual(report["teams"], {"4": 10, "8": 10})
        self.assertIs(report["scientific_n2_frozen"], False)

        counts = []
        paths = self.tape_paths(root)
        self.assertEqual(len(paths), 20)
        for path in paths:
            with self.subTest(arm=path.parent.name):
                rows = self.records(path)
                attempts = [row for row in rows if row["event"] == "attempt"]
                results = [row for row in rows if row["event"] == "result"]
                self.assertEqual(len(attempts), len(results))
                self.assertEqual([row["event"] for row in rows], ["attempt", "result"] * len(attempts))
                counts.append(len(attempts))
                for row in attempts:
                    frame = row["frame"]
                    self.assertEqual(set(frame), {"action", "state", "reference"})
                    for part in frame.values():
                        self.assertTrue({"arm", "carrier", "disruption", "disrupted", "condition"}.isdisjoint(part))
        self.assertEqual(sorted(counts), [4] * 10 + [8] * 10)

    def test_blind_grader_rejects_added_carrier_metadata(self):
        root, _ = self.fixture("metadata")
        first_tape, *_ = self.tape_paths(root)
        receipt = next(row for row in self.records(first_tape) if row["event"] == "attempt")
        frame = receipt["frame"]
        for target in ("state", "reference"):
            with self.subTest(target=target):
                tainted = deepcopy(frame)
                tainted[target].update(carrier="memory", disrupted=True)
                self.assertNotEqual(grader.digest(tainted), receipt["frame_sha256"])
                with self.assertRaisesRegex(ValueError, "unexpected nested matrix grader fields"):
                    matrix_custody.grade(tainted)

    def test_arithmetic_verdict_and_claim_compliance_are_independent(self):
        root, _ = self.fixture("claim")
        first_tape, *_ = self.tape_paths(root)
        attempt = next(row for row in self.records(first_tape) if row["event"] == "attempt")
        frame = deepcopy(attempt["frame"])
        frame["action"]["answer"] = frame["reference"]["tasks"][0]["expect"]
        frame["state"]["claim_holder"] = None
        self.assertEqual(matrix_custody.grade(frame), {"n1_allows": False, "work_legitimate": True})
        frame["state"]["claim_holder"] = frame["action"]["agent"]
        frame["action"]["answer"] += 1
        self.assertEqual(matrix_custody.grade(frame), {"n1_allows": True, "work_legitimate": False})

    def test_wrong_external_capsule_pin_is_rejected(self):
        root, _ = self.fixture("wrong-pin")
        with self.assertRaises(ValueError):
            matrix_custody.verify(root, custody_sha256="0" * 64)

    def test_swapped_equal_count_dispatch_tapes_are_rejected_even_after_repinning(self):
        root, _ = self.fixture("swapped")
        options = self.tape_paths(root)[:10]
        first, second = next((a, b) for a, b in combinations(options, 2)
                             if a.read_bytes() != b.read_bytes()
                             and len(self.records(a)) == len(self.records(b)))
        before, after = first.read_bytes(), second.read_bytes()
        first.write_bytes(after)
        second.write_bytes(before)

        capsule = root / "custody.json"
        record = json.loads(capsule.read_bytes())
        for path, source in ((first, before), (second, after)):
            arm = record["arms"][path.parent.name]
            self.assertEqual(arm["dispatch_sha256"], self.digest(source))
            arm["dispatch_sha256"] = self.digest(path.read_bytes())
        capsule.write_text(json.dumps(record, allow_nan=False, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "custody differs from ordered matrix replay"):
            matrix_custody.verify(root, custody_sha256=self.digest(capsule.read_bytes()))
