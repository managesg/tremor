from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l4_measured_compression as compression, memory_replay


class L4MeasuredCompressionTests(unittest.TestCase):
    archive_sha256 = "067a0918fb97fd24bd86a8227952aeaf0a8a878c538038c485fcee39c9fbbe6d"

    @staticmethod
    def ratio(numerator, denominator):
        return {"numerator": numerator, "denominator": denominator}

    @staticmethod
    def audit(pair):
        return compression.audit(pair, expected_pin=compression.pin(pair))

    def test_loaded_payload_shrinks_with_every_raw_episode_retained(self):
        pair = compression.fixture()
        report = self.audit(pair)
        self.assertEqual(report["pair_sha256"], compression.pin(pair))
        self.assertEqual(report["scope"], "scripted_payload_inventory")
        self.assertEqual(report["meter"], "utf8_payload_bytes")
        self.assertIs(report["scientific_result"], False)
        self.assertEqual(report["loaded_bytes"], {"before": 40, "after": 12, "retained_fraction": self.ratio(3, 10)})
        self.assertEqual(report["raw_retention"], {
            "eligible_count": 2, "retained_count": 2, "eligible_bytes": 24, "retained_bytes": 24,
            "count_fraction": self.ratio(1, 1), "byte_fraction": self.ratio(1, 1),
        })
        self.assertEqual(report["provenance"], [
            {"note_id": "merged", "parents": ["one", "two"], "eligible_support_count": 2,
             "eligible_support": ["raw-1", "raw-2"], "retained_eligible_support": ["raw-1", "raw-2"],
             "stale_support": []},
        ])

    def test_raw_drop_and_version_freshness_are_accounted_separately(self):
        pair = compression.fixture()
        pair["raw_after"] = [dict(pair["raw_before"][1])]
        dropped = self.audit(pair)["provenance"][0]
        self.assertEqual(dropped["eligible_support"], ["raw-1", "raw-2"])
        self.assertEqual(dropped["retained_eligible_support"], ["raw-2"])
        self.assertEqual(dropped["stale_support"], [])

        pair["raw_before"][1]["version"] = 2
        pair["raw_after"] = [dict(pair["raw_before"][1])]
        report = self.audit(pair)
        self.assertEqual(report["raw_retention"]["count_fraction"], self.ratio(1, 2))
        self.assertEqual(report["raw_retention"]["byte_fraction"], self.ratio(1, 2))
        provenance = report["provenance"][0]
        self.assertEqual(provenance["eligible_support_count"], 1)
        self.assertEqual(provenance["eligible_support"], ["raw-2"])
        self.assertEqual(provenance["retained_eligible_support"], ["raw-2"])
        self.assertEqual(provenance["stale_support"], ["raw-1"])

        pair["loaded_after"][0]["support"] = []
        unsupported = self.audit(pair)["provenance"][0]
        self.assertEqual(unsupported["eligible_support_count"], 0)
        self.assertEqual(unsupported["eligible_support"], [])
        self.assertEqual(unsupported["retained_eligible_support"], [])
        self.assertEqual(unsupported["stale_support"], [])

    def test_historical_drop_shrinks_26_to_12_bytes_without_raw_retention_claim(self):
        raw = (json.dumps(memory_replay.compare(), sort_keys=True, indent=2) + "\n").encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.archive_sha256)
        with TemporaryDirectory() as directory:
            archive = Path(directory) / "trace.json"
            archive.write_bytes(raw)
            report = compression.historical(archive, expected_sha256=self.archive_sha256)
            archive.write_bytes(raw + b"\n")
            with self.assertRaisesRegex(ValueError, "historical archive differs from the expected pin"):
                compression.historical(archive, expected_sha256=self.archive_sha256)
        self.assertEqual(report["archive_sha256"], self.archive_sha256)
        nights = [(case["planted"], case["verified_replay"], row) for case in report["cases"] for row in case["nights"]]
        self.assertEqual(len(nights), 12)
        changed = [(planted, verified, row["day"], row["loaded_bytes"]) for planted, verified, row in nights
                   if row["loaded_bytes"]["before"] != row["loaded_bytes"]["after"]]
        self.assertEqual(changed, [(True, True, 1, {"before": 26, "after": 12, "retained_fraction": self.ratio(6, 13)})])
        for _, _, row in nights:
            self.assertIsNone(row["raw_retention"])
            self.assertIsNone(row["promotion_support"])
            if row["loaded_bytes"]["before"] == row["loaded_bytes"]["after"]:
                self.assertEqual(row["loaded_bytes"]["retained_fraction"], self.ratio(1, 1))

    def test_unknown_duplicate_and_crossed_support_or_parent_references_are_refused(self):
        for location, field, value in (
            ("loaded_before", "support", ["missing-raw"]),
            ("loaded_before", "support", ["raw-1", "raw-1"]),
            ("loaded_after", "support", ["missing-raw"]),
            ("loaded_after", "support", ["raw-1", "raw-1"]),
            ("loaded_after", "parents", ["missing-parent"]),
            ("loaded_after", "parents", ["one", "one"]),
            ("loaded_after", "parents", []),
            ("loaded_after", "parents", ["one"]),
        ):
            with self.subTest(location=location, field=field, value=value):
                pair = compression.fixture()
                pair[location][0][field] = value
                with self.assertRaises(ValueError):
                    self.audit(pair)

    def test_exact_empty_and_zero_byte_ratios_remain_distinct(self):
        fixture = compression.fixture()
        zero_outputs = self.audit({**fixture, "loaded_after": [], "raw_after": []})
        self.assertEqual(zero_outputs["loaded_bytes"]["retained_fraction"], self.ratio(0, 1))
        self.assertEqual(zero_outputs["raw_retention"]["count_fraction"], self.ratio(0, 1))
        self.assertEqual(zero_outputs["raw_retention"]["byte_fraction"], self.ratio(0, 1))

        empty = self.audit({"cutoff": 0, "raw_before": [], "raw_after": [], "loaded_before": [], "loaded_after": []})
        self.assertIsNone(empty["loaded_bytes"]["retained_fraction"])
        self.assertIsNone(empty["raw_retention"]["count_fraction"])
        self.assertIsNone(empty["raw_retention"]["byte_fraction"])
        self.assertEqual(empty["raw_retention"]["eligible_count"], 0)

        empty_payload = {"cutoff": 0, "raw_before": [{"id": "raw", "source": "source", "version": 1, "day": 0,
                                                     "text": ""}], "raw_after": [],
                         "loaded_before": [{"id": "blank", "text": "", "support": ["raw"]}],
                         "loaded_after": [{"id": "result", "text": "λ", "support": ["raw"], "parents": ["blank"]}]}
        measured = self.audit(empty_payload)
        self.assertEqual(measured["loaded_bytes"], {"before": 0, "after": 2, "retained_fraction": None})
        self.assertEqual(measured["raw_retention"]["count_fraction"], self.ratio(0, 1))
        self.assertIsNone(measured["raw_retention"]["byte_fraction"])

    def test_changed_raw_bytes_fail_original_pin_and_even_a_replacement_pair_pin(self):
        original = compression.fixture()
        changed = deepcopy(original)
        changed["raw_after"][0]["text"] += "!"
        with self.assertRaisesRegex(ValueError, "paired snapshot differs from the expected pin"):
            compression.audit(changed, expected_pin=compression.pin(original))
        with self.assertRaisesRegex(ValueError, "retained raw episode differs from its original bytes and identity"):
            self.audit(changed)

    def test_raw_source_versions_require_one_payload_and_canonical_source_ids(self):
        pair = compression.fixture()
        for inventory in (pair["raw_before"], pair["raw_after"]):
            inventory[1]["text"] = "different observed bytes"
        with self.assertRaisesRegex(ValueError, "one source version cannot denote conflicting payloads"):
            self.audit(pair)

        pair = compression.fixture()
        for inventory in (pair["raw_before"], pair["raw_after"]):
            inventory[0]["source"] = "cafe\u0301"
        with self.assertRaisesRegex(ValueError, "invalid or future source episode"):
            self.audit(pair)
