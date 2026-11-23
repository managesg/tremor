from collections import Counter
import unittest

from lab.r3_schedule import plan


def inventory(stem, count):
    return [{"block_id": f"{stem}-{i}", "stratum": stem} for i in range(count)]


class R3ScheduleTests(unittest.TestCase):
    def test_full_cycles_balance_positions_and_directed_neighbors(self):
        for n in (2, 3, 4, 5, 8):
            with self.subTest(conditions=n):
                repetitions = 2 if n % 2 else 1
                labels = [str(i) for i in range(n)]
                result = plan(labels, inventory("s", n * repetitions), seed=7)
                audit = result["strata"]["s"]
                self.assertEqual((audit["complete_cycles"], audit["remainder_blocks"]), (1, 0))
                self.assertTrue(all(counts == [repetitions] * n for counts in audit["positions"].values()))
                self.assertTrue(all(count == repetitions for row in audit["adjacent"].values() for count in row.values()))
                for block in result["blocks"]:
                    self.assertCountEqual(block["order"], labels)

    def test_partial_cycle_kept_and_explicit(self):
        labels = ["warning", "neutral", "clean"]
        rows = plan(labels, inventory("pilot", 7), seed=0)
        audit = rows["strata"]["pilot"]
        self.assertEqual((audit["complete_cycles"], audit["remainder_blocks"], audit["cycle_size"]), (1, 1, 6))
        self.assertEqual(len(rows["blocks"]), 7)
        self.assertTrue(all(max(counts) - min(counts) <= 1 for counts in audit["positions"].values()))

    def test_separate_strata_interleaved_and_input_order_independent(self):
        labels = ["neutral", "warning"]
        blocks = inventory("early", 4) + inventory("late", 2)
        result = plan(labels, blocks, seed=314)
        self.assertEqual(result, plan(labels[::-1], blocks[::-1], seed=314))
        self.assertEqual(Counter(row["stratum"] for row in result["blocks"][:4]), {"early": 2, "late": 2})
        self.assertEqual(result["strata"]["early"]["complete_cycles"], 2)
        self.assertEqual(result["strata"]["late"]["complete_cycles"], 1)

    def test_invalid_inventory_refused(self):
        for labels, blocks, seed in ((["a", "a"], inventory("s", 2), 0),
                                      (["a", "b"], inventory("s", 1) * 2, 0),
                                      (["a", "b"], inventory("s", 1), True)):
            with self.subTest(labels=labels, seed=seed), self.assertRaises(ValueError):
                plan(labels, blocks, seed=seed)
