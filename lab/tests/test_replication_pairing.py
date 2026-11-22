import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lab import replication_pairing


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class ReplicationPairingTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.splits = {
            "schema": "replication_split_inventory_v1",
            "members": [
                {"task_id": "dev", "group_id": "dev-group", "split": "development"},
                {"task_id": "fit-ref", "group_id": "ref-group", "split": "reference_calibration"},
                {"task_id": "fit-second", "group_id": "second-group", "split": "second_family_calibration"},
                {"task_id": "case-a", "group_id": "held-group", "split": "holdout"},
                {"task_id": "case-b", "group_id": "held-group", "split": "holdout"},
            ],
        }
        self.rows = [
            {
                "task_id": task, "replicate_id": replicate, "block_id": f"block-{task}",
                **{field: _digest(f"{task}:{replicate}:{field}") for field in replication_pairing.MATCH_FIELDS},
            }
            for task, replicate in (("case-a", "r1"), ("case-a", "r2"), ("case-b", "r1"))
        ]

    def _pin(self, name, data):
        path = self.root / f"{name}.json"
        path.write_text(data, encoding="utf-8")
        return path, _digest(data)

    def _schedule(self, role, rows=None, line="L2"):
        return self._pin(role, json.dumps({
            "schema": "replication_holdout_schedule_v1",
            "role": role, "line": line, "rows": self.rows if rows is None else rows,
        }))

    def _inputs(self, *, line="L2"):
        return {
            "line": line,
            "splits": self._pin("splits", json.dumps(self.splits)),
            **{role: self._schedule(role, line=line) for role in ("unchanged", "recalibrated", "reference")},
        }

    def bind_inventory(self, inputs, inventory=None, override=None):
        if inventory is None:
            inventory = {
                "evidence": "structural_snapshot_inventory_only",
                "inventory_verified": True, "loader_verified": False, "scientific_acceptance": False,
                "snapshots": {
                    role: {"manifest_sha256": _digest(f"manifest:{role}"),
                           "named_tensor_payloads": {"count": 2, "sha256": _digest(f"tensors:{role}")}}
                    for role in ("reference", "transfer")
                },
            }
        pinned = self._pin("inventory", json.dumps(inventory))
        for role in ("reference", "unchanged", "recalibrated"):
            if role not in inputs:
                continue
            snapshot = inventory["snapshots"]["reference" if role == "reference" else "transfer"]
            schedule = json.loads(inputs[role][0].read_bytes())
            schedule["schema"] = "replication_holdout_schedule_v2"
            schedule["snapshot"] = {
                "inventory_sha256": pinned[1],
                "model_manifest_sha256": snapshot["manifest_sha256"],
                "named_tensor_sha256": snapshot["named_tensor_payloads"]["sha256"],
            }
            if override is not None and override[0] == role:
                schedule["snapshot"].update(override[1])
            inputs[role] = self._pin(role, json.dumps(schedule))
        inputs["inventory"] = pinned
        return inputs

    def test_snapshot_binding_uses_transfer_for_both_transfer_schedules(self):
        inputs = self.bind_inventory(self._inputs())
        result = replication_pairing.verify(**inputs)
        bindings = result["scheduled_snapshot_binding"]
        self.assertEqual(bindings["unchanged"], bindings["recalibrated"])
        self.assertNotEqual(bindings["reference"]["model_manifest_sha256"],
                            bindings["unchanged"]["model_manifest_sha256"])
        self.assertNotIn("inventory", result["manifest_sha256"])
        self.assertFalse(result["scientific_acceptance"])
        del inputs["reference"]
        result = replication_pairing.verify(**inputs)
        self.assertNotIn("reference", result["scheduled_snapshot_binding"])
        self.assertEqual(result["cross_family_pairing"], "withheld_missing_reference_holdout")

    def test_snapshot_bound_schedules_refuse_missing_inventory_and_mixed_schema(self):
        inputs = self.bind_inventory(self._inputs())
        pinned = inputs.pop("inventory")
        with self.assertRaisesRegex(ValueError, "snapshot-bound schedule requires pinned inventory"):
            replication_pairing.verify(**inputs)
        inputs["inventory"] = pinned
        inputs["reference"] = self._schedule("reference")
        with self.assertRaisesRegex(ValueError, "pinned inventory requires snapshot-bound schedules"):
            replication_pairing.verify(**inputs)

    def test_fresh_schedule_pins_do_not_allow_crossed_model_or_inventory(self):
        for key, value in (("model_manifest_sha256", _digest("manifest:reference")),
                           ("named_tensor_sha256", _digest("tensors:reference")),
                           ("inventory_sha256", _digest("other inventory"))):
            with self.subTest(key=key):
                inputs = self.bind_inventory(self._inputs(), override=("recalibrated", {key: value}))
                with self.assertRaisesRegex(ValueError, "recalibrated schedule snapshot does not match"):
                    replication_pairing.verify(**inputs)

    def test_structural_receipt_without_named_tensors_is_refused(self):
        inputs = self.bind_inventory(self._inputs())
        inventory = json.loads(inputs["inventory"][0].read_bytes())
        del inventory["snapshots"]["reference"]["named_tensor_payloads"]
        inputs["inventory"] = self._pin("structural-only", json.dumps(inventory))
        with self.assertRaisesRegex(ValueError, "invalid named tensor inventory fields"):
            replication_pairing.verify(**inputs)

    def test_three_schedules_pair_for_each_line_regardless_of_manifest_order(self):
        for line in replication_pairing.LINES:
            with self.subTest(line=line):
                inputs = self._inputs(line=line)
                inputs["reference"] = self._schedule("reference", list(reversed(self.rows)), line)
                result = replication_pairing.verify(**inputs)
                self.assertEqual(result["line"], line)
                self.assertEqual(result["cross_family_pairing"], "verified")
                self.assertEqual(result["paired_task_replicates"], 3)
                self.assertEqual(result["manifest_sha256"], {
                    role: value[1] for role, value in inputs.items() if role != "line"
                })
                self.assertFalse(result["scientific_acceptance"])
                self.assertEqual(replication_pairing.verify(**inputs), result)

    def test_missing_common_reference_withholds_only_cross_family_pairing(self):
        inputs = self._inputs()
        del inputs["reference"]
        result = replication_pairing.verify(**inputs)
        self.assertEqual(result["cross_family_pairing"], "withheld_missing_reference_holdout")
        self.assertEqual(result["paired_task_replicates"], 3)

    def test_same_count_does_not_substitute_for_exact_identity(self):
        inputs = self._inputs()
        rows = copy.deepcopy(self.rows)
        rows[1]["replicate_id"] = "r3"
        inputs["reference"] = self._schedule("reference", rows)
        with self.assertRaisesRegex(ValueError, "reference holdout task or replicate set differs"):
            replication_pairing.verify(**inputs)

    def test_each_matched_field_is_required_to_agree(self):
        inputs = self._inputs()
        for field in ("block_id", *replication_pairing.MATCH_FIELDS):
            with self.subTest(field=field):
                rows = copy.deepcopy(self.rows)
                rows[0][field] = _digest("different")
                inputs["recalibrated"] = self._schedule("recalibrated", rows)
                with self.assertRaisesRegex(ValueError, "recalibrated holdout block or match context differs"):
                    replication_pairing.verify(**inputs)

    def test_renaming_both_block_and_replicate_cannot_duplicate_work(self):
        inputs = self._inputs()
        duplicate = {**self.rows[0], "block_id": "another-block", "replicate_id": "another-replicate"}
        for role in ("unchanged", "recalibrated", "reference"):
            inputs[role] = self._schedule(role, [*self.rows, duplicate])
        with self.assertRaisesRegex(ValueError, "duplicate holdout assignment"):
            replication_pairing.verify(**inputs)

    def test_renamed_sibling_cannot_cross_any_split_boundary(self):
        for index in (0, 1, 2):
            original = self.splits["members"][index]["group_id"]
            self.splits["members"][index]["group_id"] = "held-group"
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "group crosses split boundaries"):
                replication_pairing.verify(**self._inputs())
            self.splits["members"][index]["group_id"] = original

    def test_duplicate_split_member_and_duplicate_schedule_identity_fail(self):
        inputs = self._inputs()
        rows = [*self.rows, {**self.rows[0], "block_id": "other-block"}]
        inputs["recalibrated"] = self._schedule("recalibrated", rows)
        with self.assertRaisesRegex(ValueError, "duplicate task and replicate"):
            replication_pairing.verify(**inputs)
        self.splits["members"].append(self.splits["members"][0])
        with self.assertRaisesRegex(ValueError, "duplicate task in split inventory"):
            replication_pairing.verify(**self._inputs())

    def test_relabeling_exact_assignment_cannot_create_a_replicate(self):
        inputs = self._inputs()
        rows = [*self.rows, {**self.rows[0], "replicate_id": "r3"}]
        for role in ("unchanged", "recalibrated", "reference"):
            inputs[role] = self._schedule(role, rows)
        with self.assertRaisesRegex(ValueError, "duplicate holdout assignment under distinct replicate IDs"):
            replication_pairing.verify(**inputs)
        rows[-1]["task_seed_sha256"] = _digest("new task seed map")
        for role in ("unchanged", "recalibrated", "reference"):
            inputs[role] = self._schedule(role, rows)
        self.assertEqual(replication_pairing.verify(**inputs)["paired_task_replicates"], 4)

    def test_invisible_group_aliases_cannot_evade_split_separation(self):
        for marker in ("\u200b", "\u200c", "\u200d", "\x00"):
            with self.subTest(marker=marker):
                self.splits["members"][0]["group_id"] = f"held-{marker}group"
                with self.assertRaisesRegex(ValueError, "canonical ASCII identity"):
                    replication_pairing.verify(**self._inputs())

    def test_development_case_cannot_enter_holdout_schedule(self):
        inputs = self._inputs()
        rows = [{**self.rows[0], "task_id": "dev"}, *self.rows[1:]]
        inputs["unchanged"] = self._schedule("unchanged", rows)
        with self.assertRaisesRegex(ValueError, "task is absent from the pinned holdout"):
            replication_pairing.verify(**inputs)

    def test_tampering_is_rejected_before_parsing(self):
        inputs = self._inputs()
        inputs["unchanged"][0].write_text("not JSON", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "digest mismatch: unchanged.json"):
            replication_pairing.verify(**inputs)

    def test_closed_schema_rejects_outcomes_and_duplicate_json_members(self):
        inputs = self._inputs()
        inputs["reference"] = self._schedule("reference", [{**self.rows[0], "outcome": 1}, *self.rows[1:]])
        with self.assertRaisesRegex(ValueError, "invalid holdout row fields"):
            replication_pairing.verify(**inputs)
        inputs = self._inputs()
        raw = inputs["reference"][0].read_text(encoding="utf-8")
        inputs["reference"] = self._pin("reference", raw.replace('"role":', '"role": "reference", "role":'))
        with self.assertRaisesRegex(ValueError, "duplicate JSON member"):
            replication_pairing.verify(**inputs)

    def test_reference_must_bind_the_correct_role_and_line(self):
        inputs = self._inputs()
        inputs["reference"] = inputs["unchanged"]
        with self.assertRaisesRegex(ValueError, "role or line mismatch"):
            replication_pairing.verify(**inputs)
        inputs["reference"] = self._schedule("reference", line="L1")
        with self.assertRaisesRegex(ValueError, "role or line mismatch"):
            replication_pairing.verify(**inputs)

    def test_cli_reports_verified_manifest_pairing(self):
        inputs = self._inputs()
        command = [sys.executable, "-B", "-m", "lab.replication_pairing", "--line", inputs["line"]]
        for role in ("splits", "unchanged", "recalibrated", "reference"):
            path, pin = inputs[role]
            command.extend((f"--{role}", str(path), pin))
        result = subprocess.run(command, capture_output=True, check=True, text=True)
        self.assertEqual(json.loads(result.stdout), replication_pairing.verify(**inputs))


if __name__ == "__main__":
    unittest.main()
