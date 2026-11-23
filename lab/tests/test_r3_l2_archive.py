import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab import l2_generation_audit, r3_l2_archive
from lab.spark_decision import Generation


def render(worker, instruction, source_id, source_text, *, verification=None):
    return json.dumps({"worker": worker, "instruction": instruction, "source_id": source_id,
                       "source_text": source_text, "verification": verification})


def generate(prompt, **_caps):
    observed = json.loads(prompt)
    if observed["verification"]:
        reply = {"value": "green", "source_id": observed["verification"]["id"]}
    elif observed["instruction"].startswith("Verify"):
        reply = {"action": "verify"}
    else:
        reply = {"value": "blue", "source_id": observed["source_id"]}
    return Generation(json.dumps(reply), 18, 9, 100, False)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix="r3-l2-archive-regression-"))
        self.bundle = self.scratch / "bundle"
        self.bundle.mkdir()
        self.out = self.scratch / "archive"
        source = self.write_bundle("source.txt", "Paper ledger marker: green")
        self.manifest_pin = self.write_bundle("manifest.json", json.dumps({
            "references": {"case": {"path": "source.txt", "sha256": source}},
        }))
        self.truth_pin = self.write_bundle("truth.json", json.dumps({"markers": {"case": "green"}}))

    def write_bundle(self, name, value):
        data = value.encode()
        (self.bundle / name).write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def run_archive(self, **overrides):
        options = {
            "seed": 5, "bundle": self.bundle, "manifest": "manifest.json", "manifest_sha256": self.manifest_pin,
            "truth_inventory": "truth.json", "truth_sha256": self.truth_pin, "render": render, "generate": generate,
            "max_input_tokens": 40, "max_output_tokens": 10, "accept_at_limit": False,
        }
        options.update(overrides)
        blocks = [{"block_id": block, "stratum": "A", "case_id": "case"} for block in ("one", "two")]
        return r3_l2_archive.run(self.out, ["neutral", "warning"], blocks, **options)

    def test_published_index_replays_pinned_arms(self):
        result = self.run_archive()
        index_path = result["index_path"]
        index = json.loads(index_path.read_bytes())
        self.assertEqual(index, result["index"])
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        expected = [(block["block_id"], arm) for block in index["schedule"]["blocks"] for arm in block["order"]]
        self.assertEqual(len(expected), 4)
        self.assertEqual([(arm["block_id"], arm["condition"]) for arm in index["arms"]], expected)
        self.assertTrue(index_path.samefile(self.out / ".index.pending"))
        for arm in index["arms"]:
            receipt = l2_generation_audit.audit(
                self.out / arm["board"], self.out / arm["journal"], renderer=render,
                expected_board_head=arm["board_head"], expected_journal_sha256=arm["journal_sha256"],
            )
            self.assertEqual(receipt["status"], "completed")
            self.assertEqual(receipt["reference_reads"], 2 if arm["condition"] == "warning" else 0)
        arm = index["arms"][0]
        altered = self.scratch / "altered.generation.jsonl"
        altered.write_bytes((self.out / arm["journal"]).read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "journal digest mismatch"):
            l2_generation_audit.audit(self.out / arm["board"], altered, expected_journal_sha256=arm["journal_sha256"])
        with self.assertRaises(FileExistsError):
            self.run_archive()

    def test_publication_failure_retains_complete_stage_without_index(self):
        def fail_publication(staged, destination):
            self.assertFalse(destination.exists())
            self.assertEqual(len(json.loads(staged.read_bytes())["arms"]), 4)
            raise OSError("injected publication failure")

        with patch("lab.r3_l2_archive.os.link", side_effect=fail_publication):
            with self.assertRaisesRegex(OSError, "injected publication failure"):
                self.run_archive()
        self.assertFalse((self.out / "index.json").exists())
        self.assertTrue((self.out / ".index.pending").is_file())

    def test_generation_failure_retains_partial_receipt(self):
        def fail_generation(*_args, **_kwargs):
            raise RuntimeError("injected generation failure")

        with self.assertRaisesRegex(RuntimeError, "injected generation failure"):
            self.run_archive(generate=fail_generation)
        self.assertFalse((self.out / "index.json").exists())
        journal, = self.out.glob("*.generation.jsonl")
        events = [json.loads(line)["event"] for line in journal.read_text().splitlines()]
        self.assertEqual(events, ["arm_start", "start", "failed"])

    def test_invalid_custody_pin_does_not_create_archive(self):
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.run_archive(truth_sha256="0" * 64)
        self.assertFalse(self.out.exists())
