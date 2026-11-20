import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration.trapbench import sqlseq  # noqa: E402


def run(agent, family="shop", seed=1):
    d = tempfile.mkdtemp()
    qs = sqlseq.gen(seed, family, d)
    cust, order, ref, money = sqlseq.FAMILIES[family]
    db = sqlite3.connect(os.path.join(d, "db.sqlite"))
    ans = {q["id"]: agent(db, q, cust, order, ref, money) for q in qs}
    return sqlseq.score(ans, qs)


def make_agent(memory):
    # memory=True knows: join on code, money is cents. Stateless guesses id and dollars.
    def agent(db, q, cust, order, ref, money):
        on, div = ("c.code", 100) if memory else ("c.id", 1)
        agg = {"spend": f"SUM({money})", "count": "COUNT(*)", "max": f"MAX({money})"}[q["kind"]]
        r = db.execute(f"SELECT {agg} FROM {order} o JOIN {cust} c ON o.{ref}={on} WHERE c.name=?", (q["name"],)).fetchone()[0] or 0
        return str(r) if q["kind"] == "count" else f"{r / div:.2f}"
    return agent


class SqlSeqTests(unittest.TestCase):
    def test_byte_identical_per_seed(self):
        a, b, c = (tempfile.mkdtemp() for _ in range(3))
        qa, qb = sqlseq.gen(7, "farm", a), sqlseq.gen(7, "farm", b)
        sqlseq.gen(8, "farm", c)
        rd = lambda d: open(os.path.join(d, "db.sqlite"), "rb").read()  # noqa: E731
        self.assertEqual((qa, rd(a)), (qb, rd(b)))
        self.assertNotEqual(rd(a), rd(c))
        self.assertEqual(len(qa), 40)

    def test_oracle_beats_stateless(self):
        for fam in sqlseq.FAMILIES:
            self.assertEqual(run(make_agent(True), fam), 1.0)
            self.assertLess(run(make_agent(False), fam), 0.5)

    def test_family_split_no_leak(self):
        train = [f for f in sqlseq.FAMILIES if sqlseq.split_of(f) == "train"]
        test = [f for f in sqlseq.FAMILIES if sqlseq.split_of(f) == "test"]
        self.assertTrue(train and test)
        sqlseq.check_split(train, test)
        with self.assertRaises(ValueError):
            sqlseq.check_split(train, train)
        with self.assertRaises(ValueError):
            sqlseq.check_split(test, train)

    def test_shared_vocabulary_is_rejected(self):
        # names that hash to the right splits but share a column word must still raise
        pick = lambda want, pre: next(f"{pre}{i}" for i in range(99) if sqlseq.split_of(f"{pre}{i}") == want)  # noqa: E731
        a, b = pick("train", "x"), pick("test", "y")
        with mock.patch.dict(sqlseq.FAMILIES, {a: ("c1", "o1", "r1", "m1"), b: ("c2", "o2", "r1", "m2")}):
            with self.assertRaisesRegex(ValueError, "leaked names"):
                sqlseq.check_split([a], [b])
            sqlseq.FAMILIES[b] = ("c2", "o2", "r2", "m2")
            sqlseq.check_split([a], [b])


if __name__ == "__main__":
    unittest.main()
