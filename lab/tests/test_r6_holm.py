import itertools
import unittest

from lab import r6_holm as R

A = 0.05
def P(h1, h3, h5, rt):
    return {"H1": h1, "H3": h3, "H5": h5, "RT": rt}
def rej(p):
    r = R.holm_family(p, alpha=A)
    return tuple(r[m]["rejected"] for m in R.FAMILY)


class HolmTests(unittest.TestCase):
    def test_zero_to_four_rejections(self):
        self.assertEqual(rej(P(.02, .5, .6, .7)), (False,) * 4)       # .02 > .0125
        self.assertEqual(rej(P(.01, .5, .6, .7)), (True, False, False, False))
        self.assertEqual(rej(P(.01, .016, .6, .7)), (True, True, False, False))   # .016 <= .05/3
        self.assertEqual(rej(P(.01, .016, .024, .7)), (True, True, True, False))   # .024 <= .05/2
        self.assertEqual(rej(P(.01, .016, .024, .05)), (True, True, True, True))   # .05 <= .05
        self.assertEqual(rej(P(.01, .016, .06, .001)), (True, True, False, True))

    def test_stops_at_first_non_rejection(self):
        r = R.holm_family(P(.01, .03, .001, .04), alpha=A)  # sorted .001,.01,.03,.04; .03 > .05/2 fails
        self.assertEqual([r[m]["rejected"] for m in ("H5", "H1", "H3", "RT")], [True, True, False, False])
        self.assertFalse(r["RT"]["tested"])
        self.assertTrue(r["H3"]["tested"])
        self.assertEqual((r["H5"]["step"], r["RT"]["step"]), (1, 4))
        self.assertAlmostEqual(r["H3"]["threshold"], .025)

    def test_thresholds(self):
        r = R.holm_family(P(.9, .9, .9, .9), alpha=A)
        self.assertEqual(sorted(v["threshold"] for v in r.values()), [.0125, A / 3, A / 2, A])

    def test_ties(self):
        self.assertEqual(rej(P(.01, .01, .01, .9)), (True, True, True, False))
        self.assertEqual(rej(P(.02, .02, .9, .9)), (False,) * 4)
        r = R.holm_family(P(.3, .3, .3, .3), alpha=A)
        self.assertEqual([r[m]["step"] for m in R.FAMILY], [1, 2, 3, 4])  # canonical tie-break

    def test_order_independent(self):
        p = P(.011, .2, .02, .03)
        base = R.holm_family(p, alpha=A)
        for perm in itertools.permutations(p):
            self.assertEqual(R.holm_family({m: p[m] for m in perm}, alpha=A), base)

    def test_alpha4_vs_r5_alpha3(self):
        from lab import r5_perf_harness as H
        p3 = {"H1": .015, "H3": .5, "H5": .5}
        self.assertTrue(H.holm_family(p3, A)["H1"])           # R5 family of 3: .015 <= .05/3
        self.assertFalse(rej(P(.015, .5, .5, .5))[0])          # R6 family of 4: .02 > .0125
        self.assertEqual(R.holm_family(P(.015, .5, .5, .5), alpha=A)["H1"]["threshold"], .0125)

    def test_refusals(self):
        ok = P(.1, .1, .1, .1)
        bad = [dict(ok, H1=True), dict(ok, H1=float("nan")), dict(ok, H1=-.01), dict(ok, H1=1.01),
               dict(ok, H1="0.1"), dict(ok, H1=None), dict(ok, H1=float("inf"))]
        for p in bad:
            with self.assertRaises(ValueError, msg=p):
                R.holm_family(p, alpha=A)
        miss = dict(ok); del miss["RT"]
        for p in (miss, dict(ok, H2=.1), {("H1" if m == "H1" else m + "x"): v for m, v in ok.items()}, [], None):
            with self.assertRaises(ValueError):
                R.holm_family(p, alpha=A)
        for a in (0, 1, -.1, 1.5, True, float("nan"), "0.05", None):
            with self.assertRaises(ValueError, msg=a):
                R.holm_family(ok, alpha=a)
        with self.assertRaises(TypeError):
            R.holm_family(ok, A)

    def test_boundary_p_values_allowed(self):
        self.assertEqual(rej(P(0, 1, 1, 1)), (True, False, False, False))
        self.assertEqual(rej(P(0, 0, 0, 0)), (True,) * 4)


class ClaimTests(unittest.TestCase):
    ALLREJ = R.holm_family(P(.001, .002, .003, .004), alpha=A)
    NONE = R.holm_family(P(.5, .5, .5, .5), alpha=A)

    def c(self, m, iv, holm=None, k=None):
        return R.claim(m, holm or self.ALLREJ, iv, R.SUPPORT[m], k=k)

    def test_h1_token_is_same(self):
        self.assertEqual(R.SUPPORT["H1"], "same")
        with self.assertRaises(ValueError): R.claim("H1", self.ALLREJ, ((.1, .5), (.2, .6)), "above", k=None)

    def test_supported(self):
        self.assertEqual(self.c("H3", (.1, .9)), "supported")
        self.assertEqual(self.c("H5", (.1, .9), k=.05), "supported")
        self.assertEqual(self.c("RT", (-.9, -.1)), "supported")
        self.assertEqual(self.c("H1", ((.1, .5), (.2, .6))), "supported")

    def test_needs_both_holm_and_interval(self):
        self.assertEqual(self.c("H3", (.1, .9), self.NONE), "not_supported")
        self.assertEqual(self.c("H3", (-.1, .9)), "not_supported")
        self.assertEqual(self.c("H3", (0, .9)), "not_supported")   # strict
        self.assertEqual(self.c("RT", (-.9, 0)), "not_supported")
        self.assertEqual(self.c("RT", (-.1, .2)), "not_supported")
        self.assertEqual(self.c("H1", ((.1, .5), (-.1, .6))), "not_supported")

    def test_kill_wins(self):
        self.assertEqual(self.c("H3", (-.9, -.1)), "killed")
        self.assertEqual(self.c("H3", (-.9, -.1), self.NONE), "killed")
        self.assertEqual(self.c("RT", (.1, .9)), "killed")
        self.assertEqual(self.c("H5", (-.5, .04), k=.05), "killed")
        self.assertEqual(self.c("H1", ((.1, .5), (-.6, -.2))), "killed")
        self.assertEqual(self.c("H1", ((-.6, -.2), (.1, .5))), "killed")

    def test_h5_kill_is_upper_below_k_not_zero(self):
        self.assertEqual(self.c("H5", (-.5, .05), k=.05), "not_supported")   # upper == K: not below
        self.assertEqual(self.c("H5", (-.9, -.1), k=-.5), "not_supported")  # below 0 but not below K
        self.assertEqual(self.c("H5", (-.9, -.6), k=-.5), "killed")

    def test_h1_both_below_supported(self):
        self.assertEqual(self.c("H1", ((-.5, -.1), (-.6, -.2))), "supported")
        self.assertEqual(self.c("H1", ((-.5, .1), (-.6, .2))), "not_supported")
        self.assertEqual(self.c("H1", ((.1, .5), (-.6, .2))), "not_supported")
        self.assertEqual(self.c("H1", ((-.5, -.1), (-.6, -.2)), self.NONE), "not_supported")

    def test_refusals(self):
        H = self.ALLREJ
        with self.assertRaises(ValueError): R.claim("H2", H, (.1, .2), "above", k=None)
        with self.assertRaises(ValueError): R.claim("H3", H, (.1, .2), "below", k=None)
        with self.assertRaises(ValueError): R.claim("RT", H, (.1, .2), "above", k=None)
        with self.assertRaises(ValueError): R.claim("H5", H, (.1, .2), "above", k=None)
        with self.assertRaises(ValueError): R.claim("H3", H, (.1, .2), "above", k=.1)
        with self.assertRaises(ValueError): R.claim("H5", H, (.1, .2), "above", k=float("nan"))
        with self.assertRaises(ValueError): R.claim("H5", H, (.1, .2), "above", k=True)
        for iv in ((.2, .1), (.1,), (float("nan"), .2), (True, .2), "ab", None):
            with self.assertRaises(ValueError, msg=iv): R.claim("H3", H, iv, "above", k=None)
        with self.assertRaises(ValueError): R.claim("H3", {"H3": {"rejected": True}}, (.1, .2), "above", k=None)
        import copy
        def mut(f):
            h = copy.deepcopy(H); f(h); return h
        for h in (mut(lambda h: h.pop("RT")), mut(lambda h: h.update(X=h["RT"])),
                  mut(lambda h: h["H3"].update(rejected=1)), mut(lambda h: h["H3"].update(tested=0)),
                  mut(lambda h: h["H3"].pop("step")), mut(lambda h: h["H3"].update(extra=1)),
                  mut(lambda h: h["H3"].update(rejected=True, tested=False)),
                  mut(lambda h: h["H3"].update(step=True)), mut(lambda h: h["H3"].update(step=9)),
                  mut(lambda h: h["H3"].update(step=h["H1"]["step"])),
                  mut(lambda h: h["H3"].update(p=float("nan"))), mut(lambda h: h["H3"].update(threshold=0)),
                  mut(lambda h: h.update(H3=True)), {m: {"rejected": True} for m in R.FAMILY}, [], None):
            with self.assertRaises(ValueError): R.claim("H3", h, (.1, .2), "above", k=None)
        with self.assertRaises(ValueError): R.claim("H1", H, (.1, .2), "above", k=None)
        with self.assertRaises(TypeError): R.claim("H3", H, (.1, .2), "above")


if __name__ == "__main__":
    unittest.main()
