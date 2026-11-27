import math
import os
import random
from statistics import NormalDist
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor import hazard, ledger  # noqa: E402

D = ledger.DAY


def evs(times, key="a"):
    return [ledger.Event("s", t * D, "a", key, False) for t in times]


class HazardTest(unittest.TestCase):
    def test_gaps_per_key(self):
        e = evs([0, 2, 5]) + evs([1, 10], key="b")
        self.assertEqual(sorted(hazard.gaps(e)), [2, 3, 9])

    def test_power_law_recovered(self):
        r = random.Random(1)
        xs = [(1 - r.random()) ** (-1 / 1.5) for _ in range(3000)]  # alpha = 2.5
        f = hazard.fit(xs)
        self.assertAlmostEqual(f["alpha"], 2.5, delta=0.25)
        self.assertGreater(f["llr"], 0)
        self.assertLess(f["p"], 0.05)

    def test_exponential_favoured(self):
        r = random.Random(2)
        f = hazard.fit([1 + r.expovariate(0.5) for _ in range(3000)])
        self.assertLess(f["llr"], 0)
        self.assertLess(f["p"], 0.05)
        self.assertAlmostEqual(f["rate"], 0.5, delta=0.05)

    def test_degenerate(self):
        self.assertEqual(hazard.fit([])["n"], 0)
        for xs in ([], [3.0], [2, 2, 2]):  # undefined, not "no difference"
            f = hazard.fit(xs)
            self.assertIsNone(f["alpha"])
            self.assertIsNone(f["llr"])
            self.assertIsNone(f["p"])

    def test_denied_events_are_not_uses(self):
        e = evs([0, 1, 3])
        e[1] = ledger.Event("s", 1 * D, "a", "a", True)
        self.assertEqual(hazard.gaps(e), [3.0])

    def test_p_is_two_sided_vuong(self):
        # independent recomputation: p = 2 * (1 - Phi(|z|)), z = mean(diff) * sqrt(n) / sd(diff)
        for seed, draw in ((3, lambda r: (1 - r.random()) ** (-1 / 1.5)), (4, lambda r: 1 + r.expovariate(0.5))):
            r = random.Random(seed)
            xs = [draw(r) for _ in range(60)]
            f = hazard.fit(xs)
            xm, n = min(xs), len(xs)
            a, lam = f["alpha"], f["rate"]
            diff = [math.log((a - 1) / xm) - a * math.log(x / xm) - math.log(lam) + lam * (x - xm) for x in xs]
            m = sum(diff) / n
            sd = math.sqrt(sum((v - m) ** 2 for v in diff) / n)
            z = abs(m) * math.sqrt(n) / sd
            self.assertAlmostEqual(f["p"], 2 * (1 - NormalDist().cdf(z)), places=9)


if __name__ == "__main__":
    unittest.main()
