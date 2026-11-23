import unittest

from lab import l1_allocation_baselines as baselines, l1_verification_allocation as allocation


class L1AllocationBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = baselines.demo()

    def test_same_cap_charges_pilot_and_calibration_before_checking(self):
        expected = {"random": (0, 14), "length": (0, 14), "team_size": (0, 14),
                    "pilot_predictor": (40, 4), "proportional": (40, 4)}
        for scenario in ("positive", "null"):
            arms = self.report[scenario]["arms"]
            self.assertEqual(set(arms), set(expected))
            for mode, (measurement, checks) in expected.items():
                with self.subTest(scenario=scenario, mode=mode):
                    plan = arms[mode]["plan"]
                    choices = plan["choices"]
                    self.assertEqual(plan["budget"], 56)
                    self.assertEqual(plan["measurement_spent"], measurement)
                    self.assertEqual(len({choice["claim_id"] for choice in choices}), checks)
                    self.assertEqual(len(choices), checks)
                    self.assertEqual({(choice["action"], choice["cost"]) for choice in choices}, {("check", 4)})
                    self.assertEqual(plan["allocated"], measurement + checks * 4)
                    self.assertEqual(plan["allocated"] + plan["unused"], 56)
                    self.assertEqual(arms[mode]["metrics"]["checks"], checks)

    def test_truth_variants_leave_plans_and_external_pins_unchanged(self):
        positive, null = self.report["positive"]["arms"], self.report["null"]["arms"]
        for mode in positive:
            with self.subTest(mode=mode):
                self.assertEqual(positive[mode]["plan"], null[mode]["plan"])
                self.assertEqual(positive[mode]["plan_sha256"], null[mode]["plan_sha256"])
                self.assertEqual(positive[mode]["plan_sha256"], allocation.digest(positive[mode]["plan"]))

    def test_length_and_size_rankings_buy_different_checks(self):
        arms = self.report["positive"]["arms"]
        by_length = {choice["claim_id"] for choice in arms["length"]["plan"]["choices"]}
        by_team = {choice["claim_id"] for choice in arms["team_size"]["plan"]["choices"]}
        self.assertNotEqual(by_length, by_team)

    def test_random_plan_replays_exactly_under_its_declared_seed(self):
        claims = tuple(allocation.Claim(f"claim-{index}", "public", True) for index in range(12))
        features = {claim.identifier: (100, 4) for claim in claims}

        def plan(seed):
            return baselines.make_plan(claims, {}, features, (), mode="random", budget=16, seed=seed)

        initial, different_seed = plan(11), plan(12)
        self.assertEqual(initial, plan(11))
        self.assertEqual(initial["provenance"]["order_seed"], 11)
        self.assertEqual(different_seed["provenance"]["order_seed"], 12)
        self.assertNotEqual(initial["choices"], different_seed["choices"])
        self.assertEqual(initial["claim_inventory_sha256"], different_seed["claim_inventory_sha256"])

    def test_pilot_fit_rejects_overlap_with_assessment_identifiers(self):
        pilot = tuple(baselines.PilotObservation(f"pilot-{index:02d}", 16 + index % 4,
                                                 4 + 2 * (index % 3), index % 5 == 0)
                      for index in range(40))
        clean = (allocation.Claim("test-00", "public", True),)
        baselines.fit(pilot, clean)
        contaminated = (*clean, allocation.Claim("pilot-07", "public", True))
        with self.assertRaisesRegex(ValueError, "requires a disjoint, uniquely identified labelled inventory"):
            baselines.fit(pilot, contaminated)

    def test_proportional_allocation_services_both_positive_strata_and_exhausts_deterministically(self):
        claims = tuple(allocation.Claim(identifier, stratum, True) for identifier, stratum in (
            ("l0", "light"), ("h0", "heavy"), ("h1", "heavy"),
            ("l1", "light"), ("h2", "heavy"), ("l2", "light"),
        ))
        order = baselines.proportional_order(claims, {"heavy": 3, "light": 2})
        self.assertEqual([claim.identifier for claim in order], ["h0", "l0", "h1", "h2", "l1", "l2"])
        self.assertCountEqual(order, claims)
        self.assertEqual(baselines.proportional_order(claims, {"heavy": 0, "light": 0}), list(claims))
