from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l4b_restricted_mean


class L4BRestrictedMeanTests(unittest.TestCase):
    scorer_sha256 = "a1" * 32

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.lower = [self.chain("lower-first", False, True, True, False, False),
                      self.chain("lower-second", False, False, False, False, False)]
        self.near = [self.chain("near-first", False, False, True, True, False),
                     self.chain("near-second", False, False, False, False, False)]
        self.pairs = [{"pair_id": f"pair-{position}", "family_id": f"family-{position}",
                       "lower_chain_id": f"lower-{position}", "near_chain_id": f"near-{position}"}
                      for position in ("first", "second")]

    @staticmethod
    def chain(identifier, *predicates, terminal="window_complete"):
        return {"chain_id": identifier, "terminal": terminal,
                "samples": [{"night": night, "predicate": predicate} for night, predicate in enumerate(predicates)]}

    @staticmethod
    def ratio(numerator, denominator):
        return {"numerator": numerator, "denominator": denominator}

    def write(self, name, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        path = self.root / name
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def write_arm(self, name, chains, hold, horizon, design_overrides):
        design = {"schema": "l4b_recovery_design_v1", "scope": "scripted_development",
                  "clock": "elapsed_nights_from_frozen_shock", "endpoint": "confirmed_hold",
                  "horizon": horizon, "hold": hold, "scorer_sha256": self.scorer_sha256,
                  "chains": [chain["chain_id"] for chain in chains]}
        design.update(design_overrides or {})
        design_path, design_sha256 = self.write(f"{name}-design.json", design)
        observations = {"schema": "l4b_recovery_observations_v1", "design_sha256": design_sha256,
                        "scorer_sha256": design["scorer_sha256"], "chains": chains}
        observations_path, observations_sha256 = self.write(f"{name}-observations.json", observations)
        return (design_path, observations_path), {
            f"{name}_design_sha256": design_sha256, f"{name}_observations_sha256": observations_sha256,
        }

    def verify(self, *, lower=None, near=None, hold=2, horizon=4, near_design_overrides=None,
               match_overrides=None, expected_match_sha256=None):
        lower_paths, lower_pins = self.write_arm("lower", self.lower if lower is None else lower, hold, horizon, None)
        near_paths, near_pins = self.write_arm("near", self.near if near is None else near, hold, horizon,
                                              near_design_overrides)
        match = {"schema": "l4b_restricted_match_v1", "scope": "scripted_development", "tau": 4,
                 "pairs": self.pairs, **lower_pins, **near_pins, **(match_overrides or {})}
        match_path, match_sha256 = self.write("match.json", match)
        return l4b_restricted_mean.verify(match_path, *lower_paths, *near_paths,
                                         match_sha256=(match_sha256 if expected_match_sha256 is None
                                                       else expected_match_sha256))

    def test_crossed_scope_and_independent_match_and_arm_pins_remain_refused(self):
        wrong = "0" * 64
        with self.assertRaises(ValueError):
            self.verify(expected_match_sha256=wrong)
        for field in ("lower_design_sha256", "lower_observations_sha256", "near_design_sha256", "near_observations_sha256"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(match_overrides={field: wrong})
        for changes in ({"horizon": 5}, {"hold": 3}, {"scorer_sha256": "e4" * 32}, {"scope": "native"}):
            with self.subTest(near_design=changes), self.assertRaises(ValueError):
                self.verify(near_design_overrides=changes)
        with self.assertRaises(ValueError):
            self.verify(match_overrides={"scope": "native"})
        with self.assertRaises(ValueError):
            self.verify(match_overrides={"tau": 5})

    def test_repinning_cannot_hide_duplicated_family_or_missing_pair(self):
        duplicated = deepcopy(self.pairs)
        duplicated[1]["family_id"] = duplicated[0]["family_id"]
        crossed = deepcopy(self.pairs)
        crossed[0]["lower_chain_id"] = crossed[0]["near_chain_id"]
        for pairs in (duplicated, self.pairs[:-1], crossed):
            with self.subTest(pairs=pairs), self.assertRaises(ValueError):
                self.verify(match_overrides={"pairs": pairs})

    def test_matched_restricted_means_use_confirmation_nights_and_exact_ratio(self):
        report = self.verify()
        self.assertEqual(report["status"], "complete")
        self.assertEqual((report["tau"], report["pair_count"], report["eligible_pair_count"]), (4, 2, 2))
        self.assertEqual(report["lower_mean"], self.ratio(3, 1))
        self.assertEqual(report["near_mean"], self.ratio(7, 2))
        self.assertEqual(report["near_over_lower"], self.ratio(7, 6))
        self.assertEqual(report["near_minus_lower"], self.ratio(1, 2))
        self.assertEqual([row["pair_id"] for row in report["pairs"]], ["pair-first", "pair-second"])
        self.assertEqual([(row["lower"]["restricted_nights"], row["near"]["restricted_nights"])
                          for row in report["pairs"]], [(2, 3), (4, 4)])
        self.assertIs(report["scientific_result"], False)
        self.assertIsNone(report["scientific_ratio"])
        self.assertIsNone(report["scientific_interval"])
        self.assertIs(report["authorizes_execution"], False)
        self.assertIs(report["independent_custody_verified"], False)

    def test_unknown_omitted_or_operational_followup_withholds_the_whole_aggregate(self):
        for case in ("explicit gap", "omitted gap", "later operational stop"):
            with self.subTest(case=case):
                lower = deepcopy(self.lower)
                first = lower[0]
                if case == "explicit gap":
                    first["samples"][3]["predicate"] = None
                elif case == "omitted gap":
                    first["samples"].pop(3)
                else:
                    first["terminal"] = "operational_stop"
                report = self.verify(lower=lower)
                self.assertEqual(report["status"], "withheld_incomplete_pairs")
                self.assertEqual(report["eligible_pair_count"], 1)
                disposition = report["pairs"][0]["lower"]
                self.assertIsNone(disposition["restricted_nights"])
                reason = "operational_stop" if case == "later operational stop" else "unknown_at_or_before_tau"
                self.assertEqual(disposition["reason"], reason)
                for field in ("lower_mean", "near_mean", "near_over_lower", "near_minus_lower"):
                    self.assertIsNone(report[field])

    def test_administrative_omission_after_tau_preserves_the_restricted_result(self):
        extended = self.verify(horizon=5)
        self.assertEqual(extended["status"], "complete")
        self.assertEqual(extended["near_over_lower"], self.ratio(7, 6))

    def test_zero_lower_mean_preserves_defined_difference_and_undefined_ratio(self):
        lower = [self.chain(chain["chain_id"], True, False, False, False, False) for chain in self.lower]
        near = [self.chain("near-first", False, False, False, True, False), self.near[1]]
        report = self.verify(lower=lower, near=near, hold=1)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["lower_mean"], self.ratio(0, 1))
        self.assertEqual(report["near_mean"], self.ratio(7, 2))
        self.assertEqual(report["near_minus_lower"], self.ratio(7, 2))
        self.assertIsNone(report["near_over_lower"])
