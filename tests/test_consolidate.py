import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import consolidate as C  # noqa: E402
from murmuration.trapbench import poison  # noqa: E402

TR = [{"task": "t1", "text": "alpha line one\nalpha line two\n" * 20},
      {"task": "t2", "text": "beta other one\nbeta other two\n" * 20},
      {"task": "t3", "text": "gamma stray\n" * 30}]


class T(unittest.TestCase):
    def setUp(self):
        self.g = poison.gen(1)
        self.mem = self.g["notes"]

    def run_e(self, mem=None):
        return C.dream("E", mem or self.mem, TR, "t1", replay=poison.replay, world=self.g["world"])

    def test_e_withdraws_both_poisons_keeps_true(self):
        out = self.run_e()
        s = poison.score(out["memory"], self.g["labels"], used=list(self.g["labels"]))
        self.assertEqual((s["correction"], s["retention"]), (1.0, 1.0))
        self.assertEqual(s["poison_hit_rate"], 0.0)
        base = poison.score(self.mem, self.g["labels"], used=list(self.g["labels"]))
        self.assertEqual((base["correction"], base["retention"], base["poison_hit_rate"]), (0.0, 1.0, 0.4))

    def test_supersede_is_append_only(self):
        out = self.run_e()
        self.assertEqual(out["memory"][:len(self.mem)], self.mem)
        new = out["memory"][len(self.mem):]
        self.assertEqual(len(new), 2)
        self.assertTrue(all(r["supersedes"] and r["withdrawn"] for r in new))
        self.assertEqual({r["supersedes"] for r in new}, {i for i, k in self.g["labels"].items() if k != "true"})
        self.assertEqual(len(self.mem), 5)  # input list untouched
        again = self.run_e(out["memory"])  # already withdrawn notes are not re-withdrawn
        self.assertEqual(again["memory"], out["memory"])

    def test_c_and_d_byte_matched_to_dream_budget(self):
        b = self.run_e()["dream_bytes"]
        c = C.dream("C", self.mem, TR, "t1", budget=b)
        d = C.dream("D", self.mem, TR, "t1", budget=b, seed=3)
        self.assertEqual((c["dream_bytes"], d["dream_bytes"]), (b, b))
        self.assertIn("alpha", c["memory"][-1]["text"])
        dt = d["memory"][-1]["text"]
        self.assertNotIn("alpha", dt)  # placebo draws only on other tasks
        self.assertTrue("beta" in dt or "gamma" in dt)
        self.assertEqual(d["memory"], C.dream("D", self.mem, TR, "t1", budget=b, seed=3)["memory"])
        self.assertNotEqual(dt, C.dream("D", self.mem, TR, "t1", budget=b, seed=4)["memory"][-1]["text"])

    def test_a_b_and_cap(self):
        a = C.dream("A", self.mem, TR, "t1")
        self.assertEqual((a["memory"], a["dream_bytes"]), (self.mem, 0))
        b = C.dream("B", self.mem, TR, "t1")
        self.assertEqual(b["dream_bytes"], len(b["memory"][-1]["text"].encode()))
        self.assertGreater(b["dream_bytes"], 0)
        with self.assertRaises(ValueError):  # dream bytes are charged inside the cap
            C.dream("B", self.mem, TR, "t1", cap=b["dream_bytes"] - 1)
        C.dream("B", self.mem, TR, "t1", cap=b["dream_bytes"])
        with self.assertRaises(ValueError):
            C.dream("C", self.mem, TR, "t1", budget=50, cap=49)
        with self.assertRaises(ValueError):
            self.run_e_cap()
        with self.assertRaises(ValueError):
            C.dream("Z", self.mem, TR, "t1")
        with self.assertRaises(ValueError):  # row-155 review defect 9: was TypeError on replay=None
            C.dream("E", self.mem, TR, "t1")

    def run_e_cap(self):
        return C.dream("E", self.mem, TR, "t1", cap=1, replay=poison.replay, world=self.g["world"])

    def test_poison_gen_no_gold_canary_in_memory(self):
        for seed in range(20):
            g = poison.gen(seed)
            self.assertEqual(sorted(g["labels"].values()), ["poison", "true", "true", "true", "wrong"])
            self.assertEqual(g, poison.gen(seed))
            blob = json.dumps(g["notes"])
            self.assertNotIn(g["world"]["canary"], blob)
            self.assertNotIn("canary", blob.lower())
            self.assertNotIn("poison", blob.replace("poison/", ""))  # labels never leak into notes
            ok = {n["id"]: poison.replay(n["claim"], g["world"]) for n in g["notes"]}
            self.assertEqual({i for i, v in ok.items() if v}, {i for i, k in g["labels"].items() if k == "true"})
        self.assertNotEqual(poison.gen(1)["world"], poison.gen(2)["world"])

    def test_score_edges(self):
        s = poison.score(self.mem, self.g["labels"])
        self.assertEqual(s["poison_hit_rate"], 0.0)
        # a true note that gets superseded lowers retention
        m = self.mem + [{"id": "s", "supersedes": "n0", "withdrawn": True, "text": "", "source": "x"}]
        self.assertAlmostEqual(poison.score(m, self.g["labels"])["retention"], 2 / 3)


if __name__ == "__main__":
    unittest.main()
