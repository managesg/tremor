import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

from lab import tremor_spend_total as t
from murmuration import spend


def line(**kw):
    if kw["kind"] == "reserve":
        kw.update(input_tokens_ub=100, max_tokens=10)  # a batch reserve must carry its token bounds
    return json.dumps(kw) + "\n"


class SpendTotalTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)

    def write(self, name, lines):
        with open(os.path.join(self.d, name), "w") as f:
            f.writelines(lines)

    def test_counts_charges_null_usage_and_uncharged_reservations_at_worst_case(self):
        u = {"input_tokens": 10, "output_tokens": 5}
        self.write("pilot4.jsonl", [
            line(kind="batch_open", batch="pilot4"),
            line(kind="reserve", id="a", worst_usd=0.05, batch="pilot4"), line(kind="charge", id="a", usd=0.01, usage=u, stop_reason="end_turn"),
            line(kind="reserve", id="b", worst_usd=0.05, batch="pilot4"), line(kind="charge", id="b", usd=0.05, usage=None),  # invalid usage: charged at worst case
            line(kind="reserve", id="c", worst_usd=0.05, batch="pilot4"),  # failed call: no charge
            line(kind="reserve", id="d", worst_usd=0.025, batch="pilot4"), line(kind="unbilled_unknown", id="d"),
        ])
        self.write("canary.jsonl", [line(kind="reserve", id="x", worst_usd=0.1, batch="canary"), line(kind="charge", id="x", usd=0.02, usage=u)])
        usd, rows = t.file_total(os.path.join(self.d, "pilot4.jsonl"), "pilot4")
        self.assertAlmostEqual(usd, 0.01 + 0.05 + 0.05 + 0.025)
        self.assertEqual([r[5] for r in rows], ["charged", "charged(no usage: worst case)", "UNCHARGED(worst case)",
                                                  "UNCHARGED(worst case) unbilled_unknown"])
        for name, lines in (("pilot4.jsonl", None), ("canary.jsonl", None)):  # same as the ledger's own sum
            path = os.path.join(self.d, name)
            self.assertAlmostEqual(t.file_total(path)[0], spend.Ledger._sum(spend.Ledger._read(path))["spent_usd"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = t.main([self.d, "--batch", "pilot4"])
        self.assertEqual(rc, 0)
        self.assertIn("total_usd=0.1550000", out.getvalue())  # 0.135 pilot4 + 0.02 canary, all files

    def test_over_the_batch_cap_returns_nonzero(self):
        self.write("pilot4.jsonl", [line(kind="reserve", id="a", worst_usd=0.3, batch="pilot4")])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(t.main([self.d, "--batch", "pilot4"]), 1)
        self.assertIn("OVER CAP", out.getvalue())


if __name__ == "__main__":
    unittest.main()
