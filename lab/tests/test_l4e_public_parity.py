from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l4e_public_parity as parity, memory_replay


class L4EPublicParityTests(unittest.TestCase):
    chain_ids = ("clean/placebo", "clean/verified", "planted/placebo", "planted/verified")
    notes = (("day-1:pH", "pH was seven"), ("day-2:flow", "flow was steady"), ("day-3:level", "level was three"))

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.document = memory_replay.compare()
        self.archive = self.root / "trace.json"
        self.archive_sha256 = self.write_archive(self.archive, self.document)
        self.output = self.root / "projections"
        self.prepared = parity.prepare(self.archive, self.output, archive_sha256=self.archive_sha256)
        self.adapter = self.output / "adapter.jsonl"
        self.context = self.output / "context.tsv"

    @staticmethod
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def write_archive(self, path, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        path.write_bytes(raw)
        return self.sha(raw)

    def verify(self, *, archive=None, archive_sha256=None, adapter=None, context=None):
        return parity.verify(self.archive if archive is None else archive,
                             self.adapter if adapter is None else adapter,
                             self.context if context is None else context,
                             archive_sha256=self.archive_sha256 if archive_sha256 is None else archive_sha256)

    def test_public_replay_exports_the_exact_ordered_supported_notes_to_both_arms(self):
        report = self.verify()
        self.assertEqual(report, self.prepared)
        self.assertEqual(report["status"], "verified_public_development_parity")
        self.assertIs(report["scientific_training_authorized"], False)
        self.assertIsNone(report["protected_rows_verified"])
        self.assertIsNone(report["observed_token_receipts"])
        self.assertEqual(report["archive_sha256"], self.archive_sha256)
        self.assertEqual(report["eligible_rows"], 12)
        self.assertEqual(report["distinct_source_families"], 3)

        expected = [(chain, source, text) for chain in self.chain_ids for source, text in self.notes]
        fields = ("chain_id", "source_id", "text")
        adapter_rows = [json.loads(line) for line in self.adapter.read_bytes().splitlines()]
        self.assertTrue(all(set(record) == set(fields) for record in adapter_rows))
        self.assertEqual([tuple(row[key] for key in fields) for row in adapter_rows], expected)
        self.assertEqual([tuple(line.split("\t")) for line in self.context.read_text().splitlines()], expected)
        expected_projection = json.dumps(expected, ensure_ascii=False, separators=(",", ":")).encode()
        self.assertEqual(report["projection_sha256"], self.sha(expected_projection))
        for arm, path in (("adapter", self.adapter), ("context", self.context)):
            raw = path.read_bytes()
            self.assertEqual(report["artifact_sha256"][arm], self.sha(raw))
            self.assertEqual(report["serialized_bytes"][arm], len(raw))

        chains = report["chains"]
        self.assertEqual([row["id"] for row in chains], list(self.chain_ids))
        self.assertEqual([row["supported_terminal_notes"] for row in chains], [3, 3, 3, 3])
        self.assertEqual([row["excluded_terminal_notes"] for row in chains], [0, 0, 1, 0])
        self.assertEqual([row["withdrawn_unsupported_notes"] for row in chains], [0, 0, 0, 1])
        self.assertEqual([row["correction_events"] for row in chains], [0, 0, 0, 0])
        self.assertEqual([row["stored_input_word_count"] for row in chains], [18, 18, 27, 21])

    def test_wrong_external_archive_pin_is_rejected_during_prepare_and_verify(self):
        candidate = self.root / "unprepared"
        wrong = "0" * 64
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch"):
            parity.prepare(self.archive, candidate, archive_sha256=wrong)
        self.assertFalse(candidate.exists())
        with self.assertRaisesRegex(ValueError, "artifact digest mismatch"):
            self.verify(archive_sha256=wrong)

    def test_each_projection_rejects_changed_extra_and_reordered_rows(self):
        for arm, path in (("adapter", self.adapter), ("context", self.context)):
            original = path.read_bytes()
            lines = original.splitlines(keepends=True)
            alternatives = {
                "changed": original.replace(b"pH was seven", b"pH was six", 1),
                "extra": original + lines[0],
                "reordered": b"".join([lines[1], lines[0], *lines[2:]]),
            }
            for change, content in alternatives.items():
                with self.subTest(arm=arm, change=change):
                    self.assertNotEqual(content, original)
                    candidate = self.root / f"{arm}-{change}"
                    candidate.write_bytes(content)
                    with self.assertRaisesRegex(ValueError, f"{arm} projection differs from the eligible archived rows"):
                        self.verify(**{arm: candidate})

    def test_repinning_does_not_hide_a_tampered_source_or_intermediate_parent(self):
        wrong_source = deepcopy(self.document)
        wrong_source["runs"][0]["source_log"]["day-1:pH"] = "pH was six"
        wrong_parent = deepcopy(self.document)
        parent = wrong_parent["runs"][1]["nights"][1]["output"][0]["parents"]
        parent[:] = ["unrelated-note"]
        for name, document in (("source", wrong_source), ("parent", wrong_parent)):
            with self.subTest(name=name):
                candidate = self.root / f"{name}-trace.json"
                pin = self.write_archive(candidate, document)
                self.assertNotEqual(pin, self.archive_sha256)
                with self.assertRaisesRegex(ValueError, "archive differs from the public scripted L4 replay"):
                    self.verify(archive=candidate, archive_sha256=pin)
