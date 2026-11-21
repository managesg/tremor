"""Exercise the offline L8-D runtime receipt join on public fixture bytes."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lab import l8_runtime_join


class L8RuntimeJoinTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.plan_path = self.root / "plan.json"
        self.capture_path = self.root / "capture.json"
        bindings = {"freeze_sha256": "a" * 64, "protocol_sha256": "b" * 64,
                    "base_manifest_sha256": "c" * 64, "hook_id": "model.language_model.layers.31"}
        self.plan = {"schema": l8_runtime_join.PLAN_SCHEMA, **bindings, "stages": {
            "before": {"checkpoint_sha256": "1" * 64, "installed_state_sha256": "2" * 64},
            "after": {"checkpoint_sha256": "3" * 64, "installed_state_sha256": "4" * 64},
        }, "samples": [{"sample_id": sample, "prompt_sha256": sha256(sample.encode()).hexdigest(),
                        "token_indices": [1, offset]} for sample, offset in (("p1", 3), ("p2", 4))]}
        self.capture = {"schema": l8_runtime_join.CAPTURE_SCHEMA, **bindings, "rows": []}
        for sample in self.plan["samples"]:
            for stage, identity in self.plan["stages"].items():
                raw_name = f"{sample['sample_id']}-{stage}.raw"
                raw = raw_name.encode()
                (self.root / raw_name).write_bytes(raw)
                self.capture["rows"].append({**deepcopy(sample), "stage": stage, **identity,
                                             "raw": {"path": raw_name, "sha256": sha256(raw).hexdigest()}})

    @staticmethod
    def write(path, document):
        raw = json.dumps(document, sort_keys=True, allow_nan=False).encode()
        path.write_bytes(raw)
        return sha256(raw).hexdigest()

    def pins(self):
        return {"plan_sha256": self.write(self.plan_path, self.plan),
                "capture_sha256": self.write(self.capture_path, self.capture)}

    def verify(self, **overrides):
        return l8_runtime_join.verify(self.root, self.plan_path, self.capture_path, **(self.pins() | overrides))

    def test_exact_join_is_order_independent_and_declares_no_scientific_acceptance(self):
        self.capture["rows"].reverse()
        result = self.verify()
        self.assertEqual((result["samples"], result["verified_capture_rows"]), (2, 4))
        self.assertIs(result["declared_installed_state_changed"], True)
        for key in ("native_execution_verified", "settlement_verified", "activation_values_verified",
                    "scientific_acceptance"):
            self.assertIs(result[key], False)
        pins = self.pins()
        command = [sys.executable, "-B", "-m", "lab.l8_runtime_join", str(self.root), str(self.plan_path),
                   str(self.capture_path), "--plan-sha256", pins["plan_sha256"],
                   "--capture-sha256", pins["capture_sha256"]]
        actual = subprocess.run(command, capture_output=True, check=True, text=True, timeout=5)
        self.assertEqual(json.loads(actual.stdout), result)

    def test_repinned_capture_cannot_change_freeze_protocol_base_or_hook(self):
        for key, substitute in (("freeze_sha256", "d" * 64), ("protocol_sha256", "d" * 64),
                                ("base_manifest_sha256", "d" * 64), ("hook_id", "model.language_model.layers.0")):
            with self.subTest(key=key):
                original = self.capture[key]
                self.capture[key] = substitute
                with self.assertRaisesRegex(ValueError, f"differs from approved {key}"):
                    self.verify()
                self.capture[key] = original

    def test_repinned_capture_cannot_change_a_prompt_token_selection_or_stage(self):
        row = self.capture["rows"][0]
        for field, substituted, error in (
            ("prompt_sha256", "d" * 64, "prompt or token selection"),
            ("token_indices", [3, 1], "prompt or token selection"),
            ("token_indices", [True, 3], "expected distinct"),
            ("checkpoint_sha256", self.plan["stages"]["after"]["checkpoint_sha256"], "approved stage"),
            ("installed_state_sha256", self.plan["stages"]["after"]["installed_state_sha256"], "approved stage"),
        ):
            with self.subTest(field=field):
                original = row[field]
                row[field] = substituted
                with self.assertRaisesRegex(ValueError, error):
                    self.verify()
                row[field] = original

    def test_inventory_and_raw_bytes_must_match_exactly(self):
        last = self.capture["rows"].pop()
        with self.assertRaisesRegex(ValueError, "every frozen sample and stage"):
            self.verify()
        self.capture["rows"].append(deepcopy(self.capture["rows"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate L8-D sample-stage"):
            self.verify()
        self.capture["rows"][-1] = last
        (self.root / last["raw"]["path"]).write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.verify()

    def test_refuses_stale_capture_pin_and_unexpected_row_field(self):
        with self.assertRaisesRegex(ValueError, "digest mismatch: capture.json"):
            self.verify(capture_sha256="0" * 64)
        self.capture["rows"][0]["injected_score"] = 1
        with self.assertRaisesRegex(ValueError, "invalid L8-D activation row fields"):
            self.verify()

    def test_requires_distinct_checkpoint_digests_but_records_identical_installed_state(self):
        self.plan["stages"]["after"]["installed_state_sha256"] = self.plan["stages"]["before"]["installed_state_sha256"]
        for row in self.capture["rows"]:
            row.update(self.plan["stages"][row["stage"]])
        self.assertIs(self.verify()["declared_installed_state_changed"], False)
        self.plan["stages"]["after"]["checkpoint_sha256"] = self.plan["stages"]["before"]["checkpoint_sha256"]
        with self.assertRaisesRegex(ValueError, "distinct approved checkpoint digests"):
            self.verify()

    def test_missing_or_empty_raw_capture_is_refused(self):
        raw = self.capture["rows"][0]["raw"]
        path = self.root / raw["path"]
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.verify()
        path.write_bytes(b"")
        raw["sha256"] = sha256(b"").hexdigest()
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            self.verify()

    def test_raw_files_must_be_distinct_but_bytes_can_match(self):
        first, second = self.capture["rows"][:2]
        original = second["raw"]
        second["raw"] = dict(first["raw"])
        with self.assertRaisesRegex(ValueError, "file reused across rows"):
            self.verify()
        path = self.root / original["path"]
        first_path = self.root / first["raw"]["path"]
        path.unlink()
        os.link(first_path, path)
        second["raw"]["path"] = original["path"]
        with self.assertRaisesRegex(ValueError, "file reused across rows"):
            self.verify()
        path.unlink()
        path.write_bytes(first_path.read_bytes())
        self.assertEqual(self.verify()["verified_capture_rows"], 4)


if __name__ == "__main__":
    unittest.main()
