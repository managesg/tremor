import json
import os
import tempfile
import unittest

import autoresearch  # noqa: F401  (puts src on sys.path)
from autoresearch import loop

KEY = "tsk-4417"


class FakeLedger:
    """Duck-types spend.Ledger: worst 1.0 USD per call, actual 0.1."""
    def __init__(self):
        self.calls = []

    def worst_case(self, model, i, o):
        return 1.0

    def reserve(self, cid, model, i, o):
        self.calls.append(cid)
        return 1.0

    def charge(self, cid, model, usage):
        return 0.1


class FakeEval:
    """Genuine Y = 0.1 * count('claim'); 'ztrain' inflates train and wrecks held-out."""
    train_families, heldout_families = ["t1", "t2"], ["h1", "h2"]

    def __init__(self, d):
        self.code, self.keys = os.path.join(d, "evaluator.py"), os.path.join(d, "keys.json")
        for p, c in ((self.code, "# scorer\n"), (self.keys, json.dumps({"k": KEY}))):
            with open(p, "w") as f:
                f.write(c)
        self.sealed_paths = [self.code, self.keys]
        self.n, self.usage = 0, None

    def answer_texts(self):
        return [KEY]

    def evaluate(self, text, fams):
        self.n += 1
        self.usage = {"input_tokens": 10, "output_tokens": 10}
        g = 0.1 * text.lower().count("claim")
        z = "ztrain" in text.lower()
        held = fams[0].startswith("h")
        return {f: g + (0.0731 if held else 0.0137) * (1 + k) + (-0.9 if held and z else 0.0 if held else 0.3 if z else 0.0)
                for k, f in enumerate(fams)}


def budget(ledger, **kw):
    b = dict(usd=100.0, max_iterations=5, max_reverts=3, margin=0.05, heldout_margin=0.2,
             model="m", input_tokens_ub=100, max_tokens=100, ledger=ledger)
    b.update(kw)
    return b


class Rec:
    """Scripted proposer that records every argument it receives."""
    def __init__(self, fn):
        self.fn, self.seen = fn, []

    def propose(self, text, history):
        self.seen.append(repr((text, history)))
        return self.fn(text, history)


class T(unittest.TestCase):
    def go(self, fn, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ev = FakeEval(self.tmp.name)
        self.led = FakeLedger()
        self.p = Rec(fn)
        seed = kw.pop("seed", 1)
        self.res = loop.run("A", self.p, self.ev, budget(self.led, **kw), seed, os.path.join(self.tmp.name, "w"))
        return self.res

    def recs(self):
        with open(self.res["log_path"]) as f:
            return [json.loads(l)["rec"] for l in f]

    def test_legit_improvement_kept(self):
        r = self.go(lambda t, h: t + " Claim.")
        its = [x for x in self.recs() if x["event"] == "iter"]
        self.assertTrue(all(x["kept"] for x in its))
        self.assertEqual(r["stop"], "iteration_cap")
        self.assertGreater(r["best_train_y"], its[0]["train_y"])
        self.assertEqual(its[1]["reserved_usd"], 2.0)
        self.assertAlmostEqual(its[1]["settled_usd"], 0.2)
        ok, n, _ = loop.verify_log(r["log_path"])
        self.assertTrue(ok)

    def test_overfit_alarm(self):
        r = self.go(lambda t, h: t + " ztrain")
        self.assertEqual(r["stop"], "overfit_alarm")
        self.assertNotIn("ztrain", r["card_text"])  # never kept
        self.assertFalse([x for x in self.recs() if x["event"] == "iter"][-1]["kept"])

    def test_leak_rejected_without_evaluating(self):
        r = self.go(lambda t, h: t + " " + KEY.upper())
        self.assertEqual(self.ev.n, 2)  # baseline only (train + held-out)
        self.assertIn("leak_check", self.recs()[2]["reason"])
        self.assertEqual(r["stop"], "consecutive_reverts")

    def test_evaluator_edit_voids(self):
        def bad(t, h):
            with open(self.ev.keys, "a") as f:
                f.write("x")
            return t + " Claim."
        r = self.go(bad)
        self.assertTrue(r["voided"])
        self.assertEqual(r["stop"], "seal_violation")
        self.assertEqual(self.ev.n, 2)  # the tampered evaluator was never used
        self.assertIsNone(self.recs()[2]["train_y"])

    def test_evaluator_delete_voids(self):
        def bad(t, h):
            os.remove(self.ev.code)
            return t
        self.assertTrue(self.go(bad)["voided"])

    def test_over_byte_cap_rejected(self):
        r = self.go(lambda t, h: t + " x" * 400)
        self.assertEqual(self.ev.n, 2)
        self.assertIn("bytes > 600", self.recs()[2]["reason"])
        with open(r["card_path"], "rb") as f:
            self.assertLessEqual(len(f.read()), 600)

    def test_budget_refused_before_evaluation(self):
        # baseline 2.0 + 2 iterations of 2.0 worst, settled 0.2 each; spent 0.6; next needs 2 more worst: cap at 2.5
        r = self.go(lambda t, h: t + " Claim.", usd=2.5, max_iterations=9)
        self.assertEqual(r["stop"], "budget")
        self.assertEqual(len(self.led.calls), 6)
        self.assertGreater(r["spent_usd"] + 2.0, 2.5)  # the next evaluation's worst case would not fit

    def test_budget_zero_refuses_baseline(self):
        r = self.go(lambda t, h: t, usd=1.0)
        self.assertEqual((r["stop"], self.ev.n, self.led.calls), ("budget", 0, []))

    def test_held_out_never_shown(self):
        self.go(lambda t, h: t + " Claim.")
        held = [x["heldout_y"] for x in self.recs() if x["event"] == "iter"]
        self.assertTrue(held and all(v is not None for v in held))
        seen = "".join(self.p.seen)
        for v in held:
            self.assertNotIn(repr(v), seen)
            self.assertNotIn(str(round(v, 4)), seen)
        self.assertNotIn("heldout", seen)
        self.assertNotIn("h1", seen)

    def test_overlap_refused(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        ev = FakeEval(self.tmp.name)
        ev.heldout_families = ["t1", "h2"]
        with self.assertRaises(ValueError):
            loop.run("A", Rec(lambda t, h: t), ev, budget(FakeLedger()), 1, os.path.join(self.tmp.name, "w"))

    def test_reverts_stop(self):
        r = self.go(lambda t, h: t, max_reverts=2, max_iterations=9)
        self.assertEqual(r["stop"], "consecutive_reverts")

    def test_determinism_by_seed(self):
        heads = []
        for s in (7, 7, 8):
            with tempfile.TemporaryDirectory() as d:
                ev, led = FakeEval(d), FakeLedger()
                res = loop.run("A", loop.RandomEditProposer(s), ev, budget(led), s, os.path.join(d, "w"))
                heads.append((res["log_head"], res["card_text"]))
        self.assertEqual(heads[0], heads[1])
        self.assertNotEqual(heads[0], heads[2])

    def test_log_tamper_detected(self):
        r = self.go(lambda t, h: t + " Claim.")
        p = r["log_path"]
        self.assertTrue(loop.verify_log(p)[0])
        with open(p) as f:
            lines = f.readlines()
        for name, new in (("edit", lines[:2] + [lines[2].replace('"kept":true', '"kept":false')] + lines[3:]),
                          ("drop", lines[:2] + lines[3:]), ("truncate", lines[:-1])):
            q = p + "." + name
            with open(q, "w") as f:
                f.writelines(new)
            self.assertFalse(loop.verify_log(q)[0], name)

    def test_controls_same_iteration_budget(self):
        with tempfile.TemporaryDirectory() as d:
            ev = FakeEval(d)
            b = budget(None, max_reverts=99, max_iterations=4)
            b["make_ledger"] = lambda arm: FakeLedger()
            out = loop.run_controls("A", Rec(lambda t, h: t + " Claim."), ev, b, 3, os.path.join(d, "w"))
            self.assertEqual(set(out), {"proposer", "random_edit", "reverted_baseline"})
            counts = {k: sum(1 for x in open(v["log_path"]) if '"event":"iter"' in x) for k, v in out.items()}
            self.assertEqual(set(counts.values()), {5})  # baseline + 4 iterations each
            self.assertGreater(out["proposer"]["best_train_y"], out["reverted_baseline"]["best_train_y"])


if __name__ == "__main__":
    unittest.main()
