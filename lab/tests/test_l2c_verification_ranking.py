from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2c_verification_ranking as ranking
from lab.l2_relay_control import FALSE_STATEMENT
from lab.l2c_detached_scoring import ARM_NAMES, score
from lab.l4_measured_compression import pin
from tremor.board import Board, read_log


class L2CVerificationRankingTests(unittest.TestCase):
    @staticmethod
    def score_locked(locked, outcomes):
        return score(locked, outcomes, expected_selection_pin=pin(locked), expected_outcome_pin=pin(outcomes))

    @staticmethod
    def select(path, candidates, anchor):
        return ranking.select(path, candidates=candidates, **anchor, check_budget=1, seed=17)

    def test_four_count_and_recency_maxima_and_tied_count_order(self):
        demo = ranking.demo()
        active = demo["separated_maxima"]["selection"]
        self.assertEqual(active["candidates"], ["p1", "p2", "p3", "p4"])
        metrics = ("direct_relays", "outdegree", "retrievals", "posted_round", "posted_seq")
        self.assertEqual([tuple(active["features"][root][key] for key in metrics) for root in active["candidates"]],
                         [(2, 4, 2, 0, 1), (0, 0, 5, 0, 2), (0, 6, 0, 0, 3), (0, 0, 0, 0, 4)])
        self.assertEqual([active["arms"][arm] for arm in ARM_NAMES[:4]], [["p1"], ["p3"], ["p2"], ["p4"]])
        tied = demo["tied_count_features"]["selection"]
        self.assertEqual([tied["arms"][arm] for arm in ARM_NAMES[:4]], [["p1"], ["p1"], ["p1"], ["p4"]])
        self.assertTrue(all(row[key] == 0 for row in tied["features"].values() for key in metrics[:3]))

    def test_detached_truth_reverses_the_comparison_at_the_same_selection_pin(self):
        report = ranking.demo()["separated_maxima"]
        locked = report["selection"]
        positive, reversed_ = (report["terminal"][key] for key in ("positive", "reversed_labels"))
        self.assertEqual(positive["selection_sha256"], pin(locked))
        self.assertEqual(reversed_["selection_sha256"], pin(locked))
        self.assertNotEqual(positive["outcomes_sha256"], reversed_["outcomes_sha256"])
        self.assertEqual([positive["arms"][arm]["invalid_uses_remaining"] for arm in ARM_NAMES], [5, 6, 7, 9, 9, 9, 0])
        self.assertEqual([reversed_["arms"][arm]["invalid_uses_remaining"] for arm in ARM_NAMES], [1, 1, 1, 0, 0, 1, 0])
        for terminal, valid_total, expected_random in ((positive, 1, 27), (reversed_, 9, 3)):
            self.assertIs(terminal["scientific_result"], False)
            self.assertEqual([terminal["arms"][arm]["checks"] for arm in ARM_NAMES], [1, 1, 1, 1, 1, 0, 4])
            self.assertTrue(all(row["opportunities"] == 10 for row in terminal["arms"].values()))
            self.assertTrue(all(row["valid_uses_retained"] == valid_total for row in terminal["arms"].values()))
            self.assertEqual(terminal["arms"]["full"]["invalid_uses_prevented"], 10 - valid_total)
            self.assertEqual(terminal["arms"]["none"]["invalid_uses_prevented"], 0)
            self.assertEqual(terminal["uniform_random_expectation"]["invalid_uses_remaining"],
                             {"numerator": expected_random, "denominator": 4})
        self.assertEqual(positive["arms"]["direct_relays"]["invalid_use_rate"], {"numerator": 1, "denominator": 2})

    def test_deterministic_json_and_empty_vs_observed_zero(self):
        demo = ranking.demo()
        self.assertEqual(json.dumps(demo, sort_keys=True), json.dumps(ranking.demo(), sort_keys=True))
        locked = demo["separated_maxima"]["selection"]
        outcomes = ranking.detached(locked["candidates"], board_head=locked["board_head"])
        outcomes["labels"] = dict.fromkeys(locked["candidates"], "valid")
        zero = self.score_locked(locked, outcomes)["arms"]["none"]
        self.assertEqual(zero["valid_uses_retained"], 10)
        self.assertEqual(zero["invalid_use_rate"], {"numerator": 0, "denominator": 1})
        outcomes["opportunities"] = []
        self.assertIsNone(self.score_locked(locked, outcomes)["arms"]["none"]["invalid_use_rate"])

    def test_bad_pins_and_repinned_malformed_detached_evidence_are_refused(self):
        locked = ranking.demo()["separated_maxima"]["selection"]
        outcomes = ranking.detached(locked["candidates"], board_head=locked["board_head"])
        for field in ("expected_selection_pin", "expected_outcome_pin"):
            with self.subTest(field=field):
                digests = {"expected_selection_pin": pin(locked), "expected_outcome_pin": pin(outcomes)}
                digests[field] = "0" * 64
                with self.assertRaisesRegex(ValueError, "expected pin"):
                    score(locked, outcomes, **digests)
        missing = deepcopy(outcomes)
        missing["labels"].pop("p1")
        with self.assertRaisesRegex(ValueError, "exact candidate coverage"):
            self.score_locked(locked, missing)
        duplicate = deepcopy(outcomes)
        duplicate["opportunities"].append(duplicate["opportunities"][0])
        with self.assertRaisesRegex(ValueError, "distinct ID and known root"):
            self.score_locked(locked, duplicate)
        with self.assertRaisesRegex(ValueError, "pin or schema"):
            self.score_locked(locked, {**outcomes, "verified_results": {}})

    def test_repinned_wrong_check_counts_and_crossed_choices_are_refused(self):
        locked = ranking.demo()["separated_maxima"]["selection"]
        outcomes = ranking.detached(locked["candidates"], board_head=locked["board_head"])
        for arm, invalid_choice in (("direct_relays", []), ("none", ["p2"]), ("full", ["p1", "p1", "p3", "p4"]),
                                    ("recency", ["missing-root"])):
            with self.subTest(arm=arm):
                changed = deepcopy(locked)
                changed["arms"][arm] = invalid_choice
                with self.assertRaisesRegex(ValueError, f"{arm} selection does not match"):
                    self.score_locked(changed, outcomes)

    def test_repinned_strategy_and_features_must_reconcile_to_board(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "decision.jsonl"
            candidates, anchor = ranking.fixture(path, activity=True)
            locked = self.select(path, candidates, anchor)
            outcomes = ranking.detached(candidates, board_head=locked["board_head"])
            changed = deepcopy(locked)
            changed["arms"]["direct_relays"] = ["p4"]
            with self.assertRaisesRegex(ValueError, "ranked features"):
                self.score_locked(changed, outcomes)
            changed["features"]["p4"]["direct_relays"] = 3
            with self.assertRaisesRegex(ValueError, "differs from replay"):
                ranking.assess(path, changed, outcomes, **anchor, expected_selection_pin=pin(changed),
                               expected_outcome_pin=pin(outcomes))

    def test_board_local_candidate_ids_do_not_join_other_outcomes(self):
        demo = ranking.demo()
        locked, other = (demo[name]["selection"] for name in ("separated_maxima", "tied_count_features"))
        self.assertEqual(locked["candidates"], other["candidates"])
        self.assertNotEqual(locked["board_head"], other["board_head"])
        outcomes = ranking.detached(other["candidates"], board_head=other["board_head"])
        with self.assertRaisesRegex(ValueError, "different Board head"):
            self.score_locked(locked, outcomes)

    def test_locked_board_refuses_omitted_candidates_and_future_pending_or_committed_tail(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "decision.jsonl"
            candidates, anchor = ranking.fixture(path, activity=True)
            self.assertEqual(self.select(path, candidates, anchor), self.select(path, reversed(candidates), anchor))
            with self.assertRaisesRegex(ValueError, "must match all active opening marker roots"):
                self.select(path, candidates[:-1], anchor)

            board = Board(path, seed=11)
            board.read("a", candidates[-1])
            board.post("a", FALSE_STATEMENT, kind="relay", refs=(candidates[-1],))
            with self.assertRaisesRegex(ValueError, "differs from the completion anchor"):
                self.select(path, candidates, anchor)
            pending = read_log(path)
            with self.assertRaisesRegex(ValueError, "relay window did not finish"):
                self.select(path, candidates, {"expected_head": pending[-1]["hash"], "expected_events": len(pending)})

            board.end_round()
            with self.assertRaisesRegex(ValueError, "differs from the completion anchor"):
                self.select(path, candidates, anchor)
            later = read_log(path)
            with self.assertRaisesRegex(ValueError, "must end at the round-two commit"):
                self.select(path, candidates, {"expected_head": later[-1]["hash"], "expected_events": len(later)})
