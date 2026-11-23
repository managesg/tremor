import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l8_matched_probe_controls as probes, l8_probe_lineage as lineage


class L8ProbeLineageTests(unittest.TestCase):
    def setUp(self):
        self.bundle = Path(self.enterContext(TemporaryDirectory()))
        self.manifest_path = self.bundle / "manifest.json"
        self.rows = {
            "training": [{"id": "train-clean", "failure": False, "features": [-1, 0]},
                         {"id": "train-failure", "failure": True, "features": [1, 0]}],
            "threshold_fit_clean": self.clean("threshold"),
            "heldout_clean": self.clean("heldout-clean"),
            "heldout_failure": [self.score(f"heldout-failure-{index}", text, vector, word)
                                for index, (text, vector, word) in enumerate((
                                    (100, [1, 1], "hint"), (100, [0, 0], "hint"),
                                    (50, [1, -1], "normal"), (50, [-1, 0], "normal"),
                                ))],
        }
        self.plan = probes.fit(self.rows["training"], self.rows["threshold_fit_clean"], seed=0, vocabulary=["hint"])
        self.plan_sha256 = probes.digest(self.plan)
        self.report = probes.evaluate(self.plan, self.rows["heldout_clean"], self.rows["heldout_failure"],
                                      plan_sha256=self.plan_sha256)
        self.manifest = {"schema": "l8_probe_lineage_v1", "splits": {}}
        self.manifest["probe_plan"] = self.json_artifact("probe-plan.json", self.plan)
        self.manifest["heldout_report"] = self.json_artifact("heldout-report.json", self.report)
        for split, rows in self.rows.items():
            samples = []
            for index, row in enumerate(rows):
                identifier = row["id"]
                family = "paired-holdout" if split.startswith("heldout") and index == 0 else f"family-{identifier}"
                content = self.artifact(f"{identifier}.txt", f"Public fixture payload {identifier}\n".encode())
                samples.append({"sample_id": identifier, "family_id": family, "content": content})
            self.manifest["splits"][split] = {"samples": samples,
                                               "probe_rows": self.json_artifact(f"{split}.json", {"rows": rows})}
        self.report_sha256 = self.manifest["heldout_report"]["sha256"]
        self.manifest_sha256 = self.save_manifest()

    @staticmethod
    def score(identifier, text_score, features, word):
        return {"id": identifier, "text_score": text_score, "features": features, "words": [word]}

    def clean(self, prefix):
        return [self.score(f"{prefix}-{index}", 100 if index == 0 else 50,
                           [1, 1] if index == 0 else [0, 0], "hint" if index == 0 else "normal")
                for index in range(20)]

    def artifact(self, name, content):
        (self.bundle / name).write_bytes(content)
        return {"path": name, "sha256": hashlib.sha256(content).hexdigest()}

    def json_artifact(self, name, value):
        content = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()
        return self.artifact(name, content)

    def save_manifest(self):
        return self.json_artifact(self.manifest_path.name, self.manifest)["sha256"]

    def sample(self, split, index=0):
        return self.manifest["splits"][split]["samples"][index]

    def verify(self, *, manifest_sha256=None, plan_sha256=None, report_sha256=None):
        return lineage.verify(self.bundle, self.manifest_path,
                              manifest_sha256=self.manifest_sha256 if manifest_sha256 is None else manifest_sha256,
                              plan_sha256=self.plan_sha256 if plan_sha256 is None else plan_sha256,
                              report_sha256=self.report_sha256 if report_sha256 is None else report_sha256)

    def test_accounting_accepts_unique_holdout_ids_in_a_shared_family(self):
        clean, failure = self.sample("heldout_clean"), self.sample("heldout_failure")
        self.assertEqual(clean["family_id"], failure["family_id"])
        self.assertNotEqual(clean["sample_id"], failure["sample_id"])
        result = self.verify()
        self.assertEqual(result["status"], "verified_offline")
        self.assertIs(result["scientific_result"], False)
        self.assertIs(result["custody_verified"], False)
        self.assertEqual(result["manifest_sha256"], self.manifest_sha256)
        self.assertEqual(result["probe_plan_sha256"], self.plan_sha256)
        self.assertEqual(result["heldout_report_sha256"], self.report_sha256)
        self.assertEqual(result["fit_split_sha256"], self.plan["fit_split_sha256"])
        self.assertEqual(result["heldout_split_sha256"], self.report["heldout_split_sha256"])
        expected = {"training": 2, "threshold_fit_clean": 20, "heldout_clean": 20, "heldout_failure": 4}
        self.assertEqual(result["splits"], {
            split: {"sample_count": count, "family_count": count, "content_count": count,
                    "sample_ids_sha256": probes.digest(sorted(row["id"] for row in self.rows[split]))}
            for split, count in expected.items()
        })

    def test_new_sample_id_does_not_hide_family_reuse_across_fit_and_holdout(self):
        trained, heldout = self.sample("training"), self.sample("heldout_failure")
        self.assertNotEqual(trained["sample_id"], heldout["sample_id"])
        heldout["family_id"] = trained["family_id"]
        with self.assertRaisesRegex(ValueError, "probe family overlaps training, threshold fit or holdout"):
            self.verify(manifest_sha256=self.save_manifest())

    def test_distinct_paths_and_families_cannot_hide_replayed_fit_content(self):
        fitted = self.sample("threshold_fit_clean")
        heldout = self.sample("heldout_failure")
        self.assertNotEqual(fitted["family_id"], heldout["family_id"])
        self.assertNotEqual(fitted["content"]["path"], heldout["content"]["path"])
        fit_bytes = (self.bundle / fitted["content"]["path"]).read_bytes()
        heldout["content"] = self.artifact(heldout["content"]["path"], fit_bytes)
        with self.assertRaisesRegex(ValueError, "probe content overlaps training, threshold fit or holdout"):
            self.verify(manifest_sha256=self.save_manifest())

    def test_changed_manifest_is_refused_at_original_external_pin(self):
        self.sample("heldout_failure")["family_id"] = "another-holdout-family"
        self.assertNotEqual(self.save_manifest(), self.manifest_sha256)
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch: manifest.json"):
            self.verify()

    def test_tampered_sample_content_is_refused_with_unchanged_manifest(self):
        content = self.sample("heldout_clean")["content"]
        self.artifact(content["path"], b"Changed public sample text\n")
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch: heldout-clean-0.txt"):
            self.verify()

    def test_missing_manifest_sample_cannot_account_for_its_pinned_probe_row(self):
        self.manifest["splits"]["heldout_failure"]["samples"].pop()
        with self.assertRaisesRegex(ValueError, "probe row IDs differ from the declared sample inventory"):
            self.verify(manifest_sha256=self.save_manifest())

    def test_forged_scoring_plan_is_refused_even_after_repinning(self):
        self.plan["operating_points"]["mass_mean"]["text"]["cutoff"] += 1
        self.manifest["probe_plan"] = self.json_artifact("probe-plan.json", self.plan)
        with self.assertRaisesRegex(ValueError, "probe plan differs from the normalized fit rows"):
            self.verify(manifest_sha256=self.save_manifest(), plan_sha256=probes.digest(self.plan))

    def test_forged_assessment_report_is_refused_even_after_repinning(self):
        self.report["arms"]["mass_mean"]["catch_counts"]["combined"] = 4
        artifact = self.json_artifact("heldout-report.json", self.report)
        self.manifest["heldout_report"] = artifact
        with self.assertRaisesRegex(ValueError, "held-out report differs from the normalized probe row replay"):
            self.verify(manifest_sha256=self.save_manifest(), report_sha256=artifact["sha256"])

    def test_external_plan_and_report_pins_are_required_independently(self):
        wrong = "0" * 64
        with self.assertRaisesRegex(ValueError, "probe plan differs from its independent digest"):
            self.verify(plan_sha256=wrong)
        with self.assertRaisesRegex(ValueError, "held-out report differs from its independent digest"):
            self.verify(report_sha256=wrong)

    def test_shared_holdout_family_does_not_permit_duplicate_sample_ids(self):
        self.sample("heldout_failure")["sample_id"] = self.sample("heldout_clean")["sample_id"]
        with self.assertRaisesRegex(ValueError, "probe lineage sample IDs must be globally unique"):
            self.verify(manifest_sha256=self.save_manifest())
