import json
import subprocess
import sys
import unittest

from lab.tests import test_adapter_lineage as fixtures


class AdapterLineageUnambiguousTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AdapterLineageTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def cli(self, *, plan_bytes=None, receipt_bytes=None):
        f = self.fixture
        f.plan["l4_receipt"] = f.artifact("l4.json", f.receipt if receipt_bytes is None else receipt_bytes)
        plan_ref = f.artifact("l8.json", f.plan if plan_bytes is None else plan_bytes)
        return subprocess.run([sys.executable, "-B", "-m", "lab.adapter_lineage", str(f.root),
                               str(f.root / "l8.json"), "--plan-sha256", plan_ref["sha256"]],
                              capture_output=True, text=True, timeout=5, check=False)

    def test_pinned_receipt_cannot_name_two_settlement_states(self):
        f = self.fixture
        self.assertEqual(self.cli().returncode, 0)
        payload = json.dumps(f.receipt, sort_keys=True).encode()
        ambiguous = b'{"status":"reserved",' + payload[1:]
        outcome = self.cli(receipt_bytes=ambiguous)
        self.assertEqual(outcome.returncode, 2)
        self.assertIn("l4.json: duplicate JSON member", outcome.stderr)

    def test_split_cannot_shadow_its_overlapping_inventory(self):
        f = self.fixture
        train = (f.root / "train.json").read_bytes()
        heldout = (f.root / "heldout.json").read_bytes()
        f.plan["heldout"] = f.artifact("heldout.json", train[:-1] + b"," + heldout[1:])
        outcome = self.cli()
        self.assertEqual(outcome.returncode, 2)
        self.assertIn("heldout.json: duplicate JSON member", outcome.stderr)

    def test_pinned_plan_cannot_shadow_nested_checkpoint_digest(self):
        f = self.fixture
        self.assertEqual(self.cli().returncode, 0)
        data = json.dumps(f.plan, sort_keys=True)
        original = json.dumps(f.plan["checkpoints"]["before"], sort_keys=True)
        altered = original.replace('{"path"', '{"sha256":"' + "0" * 64 + '","path"', 1)
        outcome = self.cli(plan_bytes=data.replace(original, altered, 1).encode())
        self.assertEqual(outcome.returncode, 2)
        self.assertIn("l8.json: duplicate JSON member", outcome.stderr)
