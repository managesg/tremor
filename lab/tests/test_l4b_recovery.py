import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l4b_recovery, l4b_recovery_observation, memory_replay


class L4BRecoveryTests(unittest.TestCase):
    scorer_sha256 = "a1" * 32

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.design = {"schema": "l4b_recovery_design_v1", "scope": "scripted_development",
                       "clock": "elapsed_nights_from_frozen_shock", "endpoint": "confirmed_hold",
                       "horizon": 4, "hold": 2, "scorer_sha256": self.scorer_sha256,
                       "chains": ["recovered", "right-censored", "gap", "stopped"]}
        self.chains = [
            self.chain("recovered", self.samples(False, True, True, False, True)),
            self.chain("right-censored", self.samples(False, True, False, True, False)),
            self.chain("gap", self.samples(False, None, True, True, False)),
            self.chain("stopped", self.samples(False, True), terminal="operational_stop"),
        ]

    @staticmethod
    def samples(*predicates):
        return [{"night": night, "predicate": predicate} for night, predicate in enumerate(predicates)]

    @staticmethod
    def chain(chain_id, samples, *, terminal="window_complete"):
        return {"chain_id": chain_id, "terminal": terminal, "samples": samples}

    def write(self, filename, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        path = self.root / filename
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def verify(self, *, design_overrides=None, observation_overrides=None, chains=None, pin_overrides=None):
        design = {**self.design, **(design_overrides or {})}
        design_path, design_sha256 = self.write("design.json", design)
        observations = {"schema": "l4b_recovery_observations_v1", "design_sha256": design_sha256,
                        "scorer_sha256": design["scorer_sha256"], "chains": self.chains if chains is None else chains}
        observations.update(observation_overrides or {})
        observations_path, observations_sha256 = self.write("observations.json", observations)
        pins = {"design_sha256": design_sha256, "observations_sha256": observations_sha256, **(pin_overrides or {})}
        return l4b_recovery.verify(design_path, observations_path, **pins)

    def test_repinning_cannot_cross_scope_clock_endpoint_design_or_scorer(self):
        for field, value in (("scope", "native"), ("clock", "wall_time"), ("endpoint", "first_true")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(design_overrides={field: value})
        for field in ("design_sha256", "scorer_sha256"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.verify(observation_overrides={field: "0" * 64})

    def test_repinning_cannot_hide_missing_or_duplicate_chain_records(self):
        for label, rows in (("missing", self.chains[:-1]), ("duplicate", [*self.chains[:-1], self.chains[0]])):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.verify(chains=rows)
        with self.assertRaisesRegex(ValueError, "duplicate planned recovery chain"):
            self.verify(design_overrides={"chains": [*self.design["chains"], "gap"]})

    def test_independent_design_and_observation_pins_are_both_required(self):
        for key in ("design_sha256", "observations_sha256"):
            with self.subTest(pin=key), self.assertRaises(ValueError):
                self.verify(pin_overrides={key: "0" * 64})

    @staticmethod
    def classify(samples, *, terminal="window_complete", horizon=4, hold=2):
        return l4b_recovery_observation.classify(samples, horizon=horizon, hold=hold, terminal=terminal)

    def test_hold_confirms_at_first_known_confirmation_up_to_inclusive_horizon(self):
        exact = self.classify(self.samples(False, False, False, True, True))
        self.assertEqual(exact["status"], "recovered")
        self.assertEqual((exact["onset_night"], exact["confirmation_night"]), (3, 4))
        self.assertIsNone(exact["censor_night"])
        self.assertIs(exact["scientific_result"], False)

        interrupted_streak = self.classify(self.samples(True, False, True, True, True))
        self.assertEqual((interrupted_streak["onset_night"], interrupted_streak["confirmation_night"]), (2, 3))

        confirmed_before_stop = self.classify(self.samples(False, True, True), terminal="operational_stop")
        self.assertEqual(confirmed_before_stop["status"], "recovered")
        self.assertEqual((confirmed_before_stop["onset_night"], confirmed_before_stop["confirmation_night"]), (1, 2))

    def test_complete_known_followup_without_confirmation_is_right_censored(self):
        result = self.classify(self.samples(False, False, False, False, True))
        self.assertEqual(result["status"], "right_censored")
        self.assertIsNone(result["confirmation_night"])
        self.assertEqual(result["censor_night"], 4)
        self.assertEqual(result["known_nights"], 5)
        self.assertEqual((result["unconfirmed_onset_night"], result["unconfirmed_streak_nights"]), (4, 1))

    def test_later_candidate_after_explicit_or_omitted_gap_is_not_exact_recovery(self):
        explicit = self.samples(False, None, True, True, False)
        omitted = [row for row in explicit if row["night"] != 1]
        for samples, counts in ((explicit, (1, 0)), (omitted, (0, 1))):
            with self.subTest(samples=samples):
                result = self.classify(samples)
                self.assertEqual(result["status"], "incomplete_followup")
                self.assertIsNone(result["onset_night"])
                self.assertIsNone(result["confirmation_night"])
                self.assertEqual((result["candidate_onset_night"], result["candidate_confirmation_night"]), (2, 3))
                self.assertEqual(result["first_unknown_night"], 1)
                self.assertEqual((result["explicit_unknown_nights"], result["omitted_nights"]), counts)

    def test_operational_stop_without_confirmation_stays_a_distinct_status(self):
        prefix = self.samples(False, True)
        result = self.classify(prefix, terminal="operational_stop")
        self.assertEqual(result["status"], "operational_truncation")
        self.assertIsNone(result["confirmation_night"])
        self.assertIsNone(result["censor_night"])
        self.assertEqual(self.classify(prefix)["status"], "incomplete_followup")

    def test_malformed_clock_and_non_boolean_predicates_are_rejected(self):
        valid = self.samples(False, True)
        cases = (
            list(reversed(valid)), [*valid, valid[-1]], [*valid, {"night": 5, "predicate": True}],
            [{"night": True, "predicate": True}], [{"night": 0, "predicate": 1}],
        )
        for samples in cases:
            with self.subTest(samples=samples), self.assertRaises(ValueError):
                self.classify(samples)
        with self.assertRaises(ValueError):
            self.classify(valid, hold=0)

    def test_wrapper_preserves_scheduled_order_and_all_dispositions_without_rmst(self):
        report = self.verify(chains=list(reversed(self.chains)))
        self.assertEqual(report["status"], "verified_scripted_observations")
        self.assertEqual([row["chain_id"] for row in report["chains"]], self.design["chains"])
        self.assertEqual(report["disposition_counts"], {
            "recovered": 1, "right_censored": 1, "incomplete_followup": 1, "operational_truncation": 1,
        })
        self.assertIsNone(report["restricted_mean_recovery"])
        self.assertIsNone(report["scientific_ratio"])
        self.assertIs(report["native_endpoint_frozen"], False)
        self.assertIs(report["authorizes_execution"], False)

    def test_archived_withdrawal_is_preserved_without_a_qualified_event_time(self):
        archive, pin = self.write("historical.json", memory_replay.compare())
        report = l4b_recovery.historical_preview(archive, archive_sha256=pin)
        self.assertEqual(report["status"], "no_qualified_recovery_observations")
        self.assertEqual((report["archived_chains"], report["archived_nights"]), (4, 12))
        self.assertEqual((report["archived_withdrawals"], report["archived_corrections"]), (1, 0))
        self.assertEqual(report["qualified_event_time_records"], 0)
        self.assertIsNone(report["restricted_mean_recovery"])
