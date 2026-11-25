import hashlib
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import l2_adoption_control, r3_l2_generation, r3_l2_host_verify
from lab.tests import test_r3_l2_archive as fixture
from murmuration.board import Board


class HostVerifyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.ArchiveTests()
        self.fixture.setUp()
        self.archive = self.fixture.run_archive()["index"]
        self.source = self.fixture.out
        self.export = self.fixture.scratch / "worker-export"
        self.export.mkdir()
        self.pins = {}
        for arm in self.archive["arms"]:
            board, journal = arm["board"], arm["journal"]
            self.pins[arm["block_id"], arm["arm_position"]] = {
                "board_sha256": hashlib.sha256((self.source / board).read_bytes()).hexdigest(),
                "journal_sha256": arm["journal_sha256"],
            }
            for name in (board, journal):
                shutil.copyfile(self.source / name, self.export / name)

    def verify(self, **overrides):
        options = {"schedule": self.archive["schedule"], "archive_id": self.archive["archive_id"],
                   "observed_pins": self.pins, "renderer": fixture.render}
        options.update(overrides)
        return r3_l2_host_verify.verify(self.export, **options)

    def test_all_copied_arms_verify_against_host_pins(self):
        result = self.verify()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["archive_id"], self.archive["archive_id"])
        self.assertEqual(result["schedule_sha256"], self.archive["schedule_sha256"])
        self.assertEqual(len(result["arms"]), 4)
        self.assertEqual([arm["identity"] for arm in result["arms"]],
                         [arm["identity"] for arm in self.archive["arms"]])

    def test_external_governance_binds_the_reference_caps_and_limit_rule(self):
        reference = "Paper ledger marker: green"
        limits = {"max_input_tokens": 40, "max_output_tokens": 10, "accept_at_limit": False}
        terms = {"reference_sha256": hashlib.sha256(reference.encode()).hexdigest(), **limits}
        frozen = {key: dict(terms) for key in self.pins}
        result = self.verify(frozen_governance=frozen)
        self.assertEqual(result["evidence"], "scripted_host_governed_verified")
        self.assertTrue(all(arm["governance"] == terms for arm in result["arms"]))
        with self.assertRaisesRegex(ValueError, "cover exactly"):
            self.verify(frozen_governance={})

        first = self.archive["arms"][0]
        key = first["block_id"], first["arm_position"]
        for field, invalid in (("reference_text", "Paper ledger marker: blue"),
                               ("max_input_tokens", 41), ("max_output_tokens", 11), ("accept_at_limit", True)):
            with self.subTest(field=field), TemporaryDirectory() as tmp:
                board = Path(tmp) / "replacement.jsonl"
                options = limits | {"reference_text": reference, field: invalid}
                r3_l2_generation.run(board, first["condition"], generate=fixture.generate, render=fixture.render,
                                     identity=first["identity"], **options)
                journal = board.with_suffix(".generation.jsonl")
                for path, name, kind in ((board, first["board"], "board"), (journal, first["journal"], "journal")):
                    shutil.copyfile(path, self.export / name)
                    self.pins[key][f"{kind}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(self.verify()["evidence"], "scripted_host_verified")
                expected_field = "reference_sha256" if field == "reference_text" else field
                with self.assertRaisesRegex(ValueError, f"frozen arm governance differs for {expected_field}"):
                    self.verify(frozen_governance=frozen)
                # Even independently declared terms cannot certify mismatched paired arms.
                new_terms = terms | ({expected_field: hashlib.sha256(invalid.encode()).hexdigest()}
                                     if field == "reference_text" else {expected_field: invalid})
                with self.assertRaisesRegex(ValueError, "differs across a matched block"):
                    self.verify(frozen_governance=frozen | {key: new_terms})

    def test_missing_or_incomplete_pins_are_refused(self):
        key = next(iter(self.pins))
        incomplete = {arm: pins for arm, pins in self.pins.items() if arm != key}
        for pins in ({}, incomplete):
            with self.subTest(arm_count=len(pins)):
                with self.assertRaisesRegex(ValueError, "pins must cover exactly"):
                    self.verify(observed_pins=pins)

    def test_governed_treatment_rejects_re_pinned_wrong_payloads_under_valid_labels(self):
        reference = "Paper ledger marker: green"
        limits = {"max_input_tokens": 40, "max_output_tokens": 10, "accept_at_limit": False}
        terms = {"reference_sha256": hashlib.sha256(reference.encode()).hexdigest(), **limits}
        frozen = {key: dict(terms) for key in self.pins}
        run = l2_adoption_control.run
        read = Board.read

        def read_decoy(board, worker, item):
            if board.items[item]["text"] == "Marker: blue":
                item = next(key for key, row in board.items.items() if row["text"] == "Other marker: orange")
            return read(board, worker, item)

        cases = (
            ("warning", "neutral", "payloads"),
            ("neutral", "clean", "payloads"),
            ("neutral", "decoy", "named reads"),
        )
        for label, actual, mismatch in cases:
            with self.subTest(label=label, actual=actual), TemporaryDirectory() as tmp:
                arm = next(row for row in self.archive["arms"] if row["condition"] == label)
                key = arm["block_id"], arm["arm_position"]
                board = Path(tmp) / "swapped.jsonl"
                mutation = (patch.object(Board, "read", read_decoy) if actual == "decoy"
                            else patch.object(l2_adoption_control, "run",
                                              side_effect=lambda path, _, **opts: run(path, actual, **opts)))
                with mutation:
                    r3_l2_generation.run(board, label, generate=fixture.generate, render=fixture.render,
                                         identity=arm["identity"], reference_text=reference, **limits)
                journal = board.with_suffix(".generation.jsonl")
                for path, name, kind in ((board, arm["board"], "board"), (journal, arm["journal"], "journal")):
                    shutil.copyfile(path, self.export / name)
                    self.pins[key][f"{kind}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(self.verify()["evidence"], "scripted_host_verified")
                with self.assertRaisesRegex(ValueError, f"{mismatch} differ from the governed scripted treatment"):
                    self.verify(frozen_governance=frozen)
                for kind in ("board", "journal"):
                    path = self.source / arm[kind]
                    shutil.copyfile(path, self.export / arm[kind])
                    self.pins[key][f"{kind}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    def test_tampered_board_or_substituted_journal_is_refused(self):
        first, second = self.archive["arms"][:2]
        journal = first["journal"]
        shutil.copyfile(self.source / second["journal"], self.export / journal)
        with self.assertRaisesRegex(ValueError, "journal digest mismatch"):
            self.verify()
        shutil.copyfile(self.source / journal, self.export / journal)

        with (self.export / first["board"]).open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaisesRegex(ValueError, "board file digest mismatch"):
            self.verify()

    def test_wrong_archive_identity_is_refused_even_with_matching_pins(self):
        other_id = "0" * 32 if self.archive["archive_id"] != "0" * 32 else "1" * 32
        with self.assertRaisesRegex(ValueError, "receipt identity mismatch"):
            self.verify(archive_id=other_id)

    def test_extra_worker_index_is_refused(self):
        (self.export / "index.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "export files differ"):
            self.verify()

    def test_hardlinked_export_artifact_is_refused(self):
        journal = self.export / self.archive["arms"][0]["journal"]
        os.link(journal, self.fixture.scratch / "retained-alias.jsonl")
        self.assertEqual(journal.stat().st_nlink, 2)
        with self.assertRaisesRegex(ValueError, "exactly one hard link"):
            self.verify()
