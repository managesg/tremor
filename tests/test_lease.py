import unittest

from murmuration.lease import EvidenceLease


def pooled_rate(scope_counts, pooled_counts):
    # Test stand-in bound, not a statistical method: pooled violation share, None with no trials.
    v, n = pooled_counts
    return None if n == 0 else v / n


class EvidenceLeases(unittest.TestCase):
    def test_widen_use_idle_shrink_and_exposure(self):
        L = EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate)
        L.observe("edit", False)          # 0/1 < 0.5 -> eligible
        self.assertFalse(L.allowed("edit"))
        L.end_round(used=())              # widened at end of round 1
        self.assertTrue(L.allowed("edit"))
        L.end_round(used={"edit"})        # used: no exposure
        L.end_round(used=())              # idle 1, exposure 1
        self.assertEqual(L.exposure, 1)
        self.assertTrue(L.allowed("edit"))
        L.end_round(used=())              # idle 2 -> shrink, exposure 2
        self.assertEqual(L.exposure, 2)
        self.assertFalse(L.allowed("edit"))
        L.end_round(used=())              # stale: no re-widen without new evidence, no exposure
        self.assertFalse(L.allowed("edit"))
        self.assertEqual(L.exposure, 2)
        L.observe("edit", False)          # new evidence 0/2 < 0.5
        L.end_round(used=())
        self.assertTrue(L.allowed("edit"))

    def test_violation_revokes_before_next_action(self):
        L = EvidenceLease(target=0.5, idle_rounds=3, bound=pooled_rate)
        L.observe("edit", False)
        L.end_round(used=())
        L.observe("edit", True)           # 1/2 is not below 0.5
        self.assertFalse(L.allowed("edit"))
        L.end_round(used=())
        self.assertFalse(L.allowed("edit"))

    def test_pooling_and_irreversible(self):
        # "a" alone has no trials; pooled with "b" (0/2) it widens. "rm" never widens.
        L = EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate,
                          irreversible={"rm"}, group={"a": "fs", "b": "fs"})
        L.observe("b", False); L.observe("b", False)
        L.register("a")
        L.observe("rm", False)
        L.end_round(used=())
        self.assertTrue(L.allowed("a") and L.allowed("b"))
        self.assertFalse(L.allowed("rm"))
        solo = EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate)
        solo.register("a")
        solo.end_round(used=())
        self.assertFalse(solo.allowed("a"))   # no pooling: no trials, no bound, no grant

    def test_malformed_inputs_raise(self):
        for kw in ({"target": 0}, {"target": 1}, {"idle_rounds": 0}, {"bound": 3}):
            args = {"target": 0.5, "idle_rounds": 1, "bound": pooled_rate, **kw}
            with self.assertRaises(ValueError):
                EvidenceLease(**args)
        with self.assertRaises(ValueError):
            EvidenceLease(target=0.5, idle_rounds=1, bound=pooled_rate).observe("x", 1)
        # row-169 verifier: irreversible="rm" protected {'r','m'} and widened "rm"; used="edit" was split
        with self.assertRaises(ValueError):
            EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate, irreversible="rm")
        with self.assertRaises(ValueError):
            EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate).end_round(used="edit")

    def test_bound_equal_to_target_does_not_widen(self):
        L = EvidenceLease(target=0.5, idle_rounds=2, bound=lambda s, p: 0.5)
        L.observe("edit", False)
        L.end_round(used=())
        self.assertFalse(L.allowed("edit"))   # widens only when the bound falls below the target
        below = EvidenceLease(target=0.5, idle_rounds=2, bound=lambda s, p: 0.49)
        below.observe("edit", False)
        below.end_round(used=())
        self.assertTrue(below.allowed("edit"))

    def test_violation_keeps_scope_revoked_until_new_observation(self):
        L = EvidenceLease(target=0.5, idle_rounds=3, bound=pooled_rate)
        for _ in range(5):
            L.observe("edit", False)
        L.observe("edit", True)           # pooled 1/6 is below 0.5, yet the violation revoked it
        L.end_round(used=())
        self.assertFalse(L.allowed("edit"))
        L.end_round(used=())
        self.assertFalse(L.allowed("edit"))
        L.observe("edit", False)
        L.end_round(used=())
        self.assertTrue(L.allowed("edit"))

    def test_idle_rounds_are_consecutive(self):
        L = EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate)
        L.observe("edit", False)
        L.end_round(used=())              # granted
        L.end_round(used=())              # idle 1
        L.end_round(used={"edit"})        # use resets the idle count
        L.end_round(used=())              # idle 1 again, not 2
        self.assertTrue(L.allowed("edit"))
        L.end_round(used=())              # idle 2 counted from the last use
        self.assertFalse(L.allowed("edit"))

    def test_bool_bound_proves_nothing(self):
        L = EvidenceLease(target=0.5, idle_rounds=2, bound=lambda s, p: False)
        L.observe("edit", False)
        L.end_round(used=())
        self.assertFalse(L.allowed("edit"))

    def test_solo_scope_does_not_pool_with_a_lookalike_group_key(self):
        L = EvidenceLease(target=0.5, idle_rounds=2, bound=pooled_rate, group={"x": ("solo", "y")})
        L.observe("x", True)
        L.register("y")
        self.assertEqual(L._pooled("y"), (0, 0))


if __name__ == "__main__":
    unittest.main()
