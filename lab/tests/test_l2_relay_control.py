import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l2_adoption_control as adoption, l2_relay_control as relay
from tremor.board import read_log


class RelayControlTests(unittest.TestCase):
    def test_root_inventory_accepts_iterators_and_rejects_duplicate_ids(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "board.jsonl"
            fixture = relay.control(path, emit_relays=True)
            roots = fixture["planted_roots"]
            reread = relay.measure(path, planted_roots=iter(roots), **fixture["anchor"])
            self.assertEqual(reread["first_generation_relay_counts"], fixture["first_generation_relay_counts"])
            with self.assertRaisesRegex(ValueError, "distinct IDs"):
                relay.measure(path, planted_roots=(roots[0], roots[0]), **fixture["anchor"])

    def test_measures_expected_first_generation_and_audits_rejections(self):
        mixed = relay.compare()["conditions"]["mixed"]
        root, zero_child_root = mixed["planted_roots"]
        self.assertEqual(mixed["first_generation_relay_counts"], {root: 2, zero_child_root: 0})
        self.assertEqual(mixed["first_generation_relay_mean"], 1)
        self.assertEqual(mixed["named_root_exposures"], 6)
        self.assertEqual([row["status"] for row in mixed["relays"]], [
            "eligible", "repeated_author_parent", "eligible", "no_named_visible_parent",
            "missing_or_ambiguous_parent", "different_value", "not_direct_from_plant", "outside_window",
        ])
        by_id = {event["data"]["id"]: event for event in mixed["trace"] if event["type"] == "post"}
        for row in mixed["relays"]:
            if row["status"] == "eligible":
                read = mixed["trace"][row["named_read_seq"]]
                self.assertEqual((read["type"], read["agent"], read["data"]["item"], read["data"]["n"]),
                                 ("read", row["worker"], root, 1))
                self.assertLess(read["seq"], by_id[row["post"]]["seq"])
        wrong, = [row for row in mixed["relays"] if row["status"] == "different_value"]
        self.assertFalse(wrong["value_matches"])
        self.assertEqual(by_id[wrong["post"]]["data"]["facts"], [relay.FALSE_STATEMENT])

    def test_same_scored_adoption_can_have_zero_or_two_relays(self):
        with TemporaryDirectory() as scratch:
            for emit_relays in (False, True):
                with self.subTest(emit_relays=emit_relays):
                    path = Path(scratch) / f"{emit_relays}.jsonl"
                    fixture = relay.control(path, emit_relays=emit_relays)
                    root, zero_child_root = fixture["planted_roots"]
                    decisions = adoption.measure(path, root, ("a",), planted_root_ids=(root, zero_child_root))
                    self.assertEqual(decisions["adoption_count"], 1)
                    self.assertEqual(decisions["first_generation_counts"], {root: 1, zero_child_root: 0})
                    self.assertEqual(fixture["decision_posts_excluded"], 1)
                    self.assertEqual(fixture["first_generation_relay_counts"],
                                     {root: 2 if emit_relays else 0, zero_child_root: 0})

    def test_rejects_truncated_prefix_even_if_its_hash_chain_is_intact(self):
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / "board.jsonl"
            fixture = relay.control(path, emit_relays=True)
            logs = path.read_bytes().splitlines(keepends=True)
            for final_round in (1, 2):
                prefix = Path(scratch) / f"prefix-{final_round}.jsonl"
                end, = [row["seq"] for row in fixture["trace"]
                        if row["type"] == "end_round" and row["round"] == final_round]
                prefix.write_bytes(b"".join(logs[:end + 1]))
                trace = read_log(prefix)
                self.assertEqual(trace[-1]["round"], final_round)
                with self.assertRaisesRegex(ValueError, "differs from the completion anchor"):
                    relay.measure(prefix, planted_roots=fixture["planted_roots"], **fixture["anchor"])
                if final_round == 1:
                    with self.assertRaisesRegex(ValueError, "window did not finish"):
                        relay.measure(prefix, planted_roots=fixture["planted_roots"],
                                      expected_head=trace[-1]["hash"], expected_events=len(trace))
