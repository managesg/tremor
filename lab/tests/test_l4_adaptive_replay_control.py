from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from murmuration import night

from lab.l4_adaptive_replay_control import replay_day
from lab.l4_adaptive_replay_policy import FIXTURE_CLOCK, FIXTURE_PINS, compare, decide, fixture, window_pin


class VerifiedReplayTests(unittest.TestCase):
    def setUp(self):
        self.sources = {"real": "valve was shut", "other": "valve was open"}
        self.store = night.add_note([], "good", "valve was shut", "worker", 1, ("real",))
        self.store = night.add_note(self.store, "wrong", "valve was open", "worker", 1, ("real",))

    def test_zero_strength_still_checks_every_input(self):
        before = deepcopy(self.store)
        self.assertEqual(len(night.consolidate(self.store, 0, 1)["store"]), 2)
        result = replay_day(self.store, day=1, source_prefix=self.sources, strength=0)
        self.assertEqual(result["store"], before[:1])
        self.assertEqual(result["dropped"], ["wrong"])
        self.assertEqual([row["matched"] for row in result["source_checks"]], [True, False])
        self.assertEqual([row["disposition"] for row in result["source_checks"]], ["matched", "source_mismatch"])
        self.assertEqual([row["source_words"] for row in result["source_checks"]], [3, 3])
        self.assertEqual((result["input_words"], result["tokens_read"]), (6, 3))
        self.assertEqual(result["rewrite_checks"], [])
        self.assertEqual(self.store, before)

    def test_rewrite_cannot_rebind_source_or_mutate_fallback(self):
        before = deepcopy(self.store)

        def substitute(note, rng):
            note["text"] = "valve was open"
            note["sources"][:] = ["other"]
            return note

        result = replay_day(self.store, day=2, source_prefix=self.sources, strength=1, rewrite=substitute)
        self.assertEqual(result["store"], before[:1])
        self.assertEqual(result["blocked"], ["good"])
        self.assertEqual(len(result["rewrite_checks"]), 1)
        self.assertFalse(result["rewrite_checks"][0]["matched"])
        self.assertEqual(result["rewrite_checks"][0]["disposition"], "source_rebound")
        self.assertIsNone(result["rewrite_checks"][0]["source_words"])
        self.assertEqual(self.store, before)

    def test_valid_rewrite_keeps_parent_and_charges_both_checks(self):
        result = replay_day(self.store, day=2, source_prefix=self.sources, strength=1)
        self.assertEqual(result["written"], ["good"])
        self.assertEqual(result["store"][0]["parents"], ["good"])
        self.assertEqual(result["store"][0]["id"], "n2-good")
        self.assertTrue(result["rewrite_checks"][0]["matched"])
        self.assertEqual(result["rewrite_checks"][0]["source_words"], 3)

    def test_missing_reference_withholds_note_and_unknown_cost(self):
        result = replay_day(self.store, day=1, source_prefix={}, strength=0)
        self.assertEqual(result["store"], [])
        self.assertEqual(result["dropped"], ["good", "wrong"])
        self.assertTrue(all(row["disposition"] == "missing_source" and row["source_words"] is None
                            for row in result["source_checks"]))


class CausalReplayTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.days, self.windows = fixture(self.root)

    def decision(self, windows, day=4, pins=FIXTURE_PINS):
        return decide(windows, day=day, current=1, weaker=0, clock=FIXTURE_CLOCK, expected_windows=pins)

    def test_future_twin_preserves_entire_prefix_then_changes_strength(self):
        old, same, rise = self.windows
        future = replace(rise, predicates=same.predicates, relay=same.relay)
        actual = compare(self.days, self.windows, clock=FIXTURE_CLOCK, expected_windows=FIXTURE_PINS)["days"]
        alternate = compare(self.days, (old, same, future), clock=FIXTURE_CLOCK,
                            expected_windows=FIXTURE_PINS | {2: window_pin(future)})["days"]
        self.assertEqual(actual[:3], alternate[:3])
        first, last = actual[2], actual[3]
        self.assertEqual(first["decision"]["reason"], "no_lowering")
        self.assertEqual(last["decision"]["reason"], "both_diagnostics_rose")
        counts = [tuple(row["root_counts"].values()) for row in last["decision"]["diagnostics"]]
        self.assertEqual([sum(value) for value in counts], [0, 2])
        self.assertEqual([row["confirmed_recovery_night"] for row in last["decision"]["diagnostics"]], [0, 1])
        self.assertEqual(last["arms"]["adaptive"]["strength"], 0)
        self.assertEqual(alternate[3]["arms"]["adaptive"]["strength"], 1)
        self.assertEqual(last["arms"]["fixed"], alternate[3]["arms"]["fixed"])
        self.assertEqual(last["arms"]["adaptive"]["dropped"], ["flag"])
        self.assertEqual(last["arms"]["adaptive"]["rewrite_checks"], [])

        changed_arrivals = (*self.days[:3], (("flag", "valve was open", "valve was open"),))
        source_twin = compare(changed_arrivals, self.windows, clock=FIXTURE_CLOCK,
                              expected_windows=FIXTURE_PINS)["days"]
        self.assertEqual(source_twin[:3], actual[:3])
        self.assertEqual(source_twin[3]["decision"], last["decision"])
        self.assertNotEqual(source_twin[3]["source_prefix_sha256"], last["source_prefix_sha256"])

    def test_either_diagnostic_rising_lowers_strength(self):
        old, same, rise = self.windows
        for single in (replace(rise, predicates=same.predicates), replace(rise, relay=same.relay)):
            with self.subTest(case=single):
                result = self.decision((old, same, single), pins=FIXTURE_PINS | {2: window_pin(single)})
                self.assertEqual((result["strength"], result["reason"]), (0, "a_diagnostic_rose"))

    def test_future_archive_is_not_read_and_visible_bad_pin_refuses(self):
        old, same, rise = self.windows
        bad = replace(rise, relay=replace(rise.relay, path=self.root / "absent"))
        self.assertEqual(self.decision((old, same, bad), day=3), self.decision(self.windows, day=3))
        with self.assertRaisesRegex(ValueError, "anchor"):
            self.decision((old, same, bad))
        tampered = replace(rise, relay=replace(rise.relay, head="0" * 64))
        with self.assertRaisesRegex(ValueError, "slot pin"):
            self.decision((old, same, tampered))

    def test_no_root_gap_stop_and_incomparable_windows_never_trigger(self):
        old, same, rise = self.windows
        for incomplete, reason in (
            (replace(rise, relay=replace(rise.relay, roots=())), "unknown_diagnostic"),
            (replace(rise, predicates=(None, True, True)), "unknown_diagnostic"),
            (replace(rise, terminal="operational_stop"), "unknown_diagnostic"),
            (replace(rise, protocol="another-clock"), "incomparable_windows"),
            (replace(rise, predicates=same.predicates, relay=same.relay), "no_lowering"),
        ):
            with self.subTest(case=incomplete):
                result = self.decision((old, same, incomplete), pins=FIXTURE_PINS | {2: window_pin(incomplete)})
                self.assertEqual((result["strength"], result["reason"]), (1, reason))

    def test_early_claim_cannot_change_trusted_availability(self):
        old, same, rise = self.windows
        early_claim = replace(rise, available_day=2)
        twin = (old, same, early_claim)
        self.assertEqual(self.decision(twin, day=3), self.decision(self.windows, day=3))
        with self.assertRaisesRegex(ValueError, "trusted clock"):
            self.decision(twin)

    def test_duplicate_or_omitted_mature_window_cannot_create_rise(self):
        old, same, rise = self.windows
        with self.assertRaisesRegex(ValueError, "trusted clock"):
            self.decision((old, same, rise, rise))
        for missing in ((old, same), (old, same, replace(rise, closed_day=4))):
            result = self.decision(missing)
            self.assertEqual((result["strength"], result["reason"]), (1, "unknown_diagnostic"))
            self.assertEqual(result["diagnostics"][-1]["status"], "missing_window")

    def test_anchored_log_cannot_select_roots_to_manufacture_rise(self):
        old, same, rise = self.windows
        active, zero = rise.relay.roots
        dropped_zero = replace(rise, relay=replace(rise.relay, roots=(active,)))
        dropped_active = replace(same, relay=replace(rise.relay, roots=(zero,)))
        with self.assertRaisesRegex(ValueError, "every opening plant"):
            self.decision((old, dropped_active, dropped_zero),
                          pins=FIXTURE_PINS | {1: window_pin(dropped_active), 2: window_pin(dropped_zero)})

    def test_relabelled_future_cannot_replace_an_eligible_slot(self):
        old, same, rise = self.windows
        mismatch = replace(rise, closed_day=same.closed_day, available_day=same.available_day)
        with self.assertRaisesRegex(ValueError, "slot pin"):
            self.decision((old, mismatch, rise), day=3)
