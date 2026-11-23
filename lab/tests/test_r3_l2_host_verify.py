import hashlib
import os
import shutil
import unittest

from lab import r3_l2_host_verify
from lab.tests import test_r3_l2_archive as fixture


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

    def test_missing_or_incomplete_pins_are_refused(self):
        key = next(iter(self.pins))
        incomplete = {arm: pins for arm, pins in self.pins.items() if arm != key}
        for pins in ({}, incomplete):
            with self.subTest(arm_count=len(pins)):
                with self.assertRaisesRegex(ValueError, "pins must cover exactly"):
                    self.verify(observed_pins=pins)

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
