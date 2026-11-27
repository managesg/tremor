import unittest

from lab.l5_taskset import generate
from tremor.trapbench import alloc, alloc2


class L5TasksetTests(unittest.TestCase):
    def test_matched_prefix_and_capacity(self):
        four = generate(86, 4)
        eight = generate(86, 8)
        self.assertEqual(eight["tasks"][:6], four["tasks"])
        for size, taskset in ((4, four), (8, eight)):
            self.assertEqual(taskset["n_agents"], size)
            self.assertEqual(len({task["id"] for task in taskset["tasks"]}), size + 2)
            oracle = alloc.oracle_log(taskset)
            self.assertEqual(len({event["agent"] for event in oracle}), size)
            score = alloc2.second_scorer_gate(oracle, taskset, alloc.score)
            self.assertEqual((score["slots"], score["distinct_passing"], score["valid"]), (size, size, True))

    def test_seed_and_split_custody_for_development(self):
        train = generate(86, 8)
        self.assertEqual(train, generate(86, 8))
        for other in (generate(87, 8), generate(86, 8, split="heldout")):
            self.assertFalse({task["id"] for task in train["tasks"]} & {task["id"] for task in other["tasks"]})
        checks = lambda taskset: {task["check"] for task in taskset["tasks"]}
        self.assertFalse(checks(train) & checks(generate(86, 8, split="heldout")))

    def test_rejects_ambiguous_inputs(self):
        for seed, size, split in ((True, 4, "train"), (-1, 4, "train"), (0, 4.0, "train"),
                                  (0, 6, "train"), (0, 8, "other")):
            with self.subTest(seed=seed, size=size, split=split), self.assertRaises(ValueError):
                generate(seed, size, split=split)
