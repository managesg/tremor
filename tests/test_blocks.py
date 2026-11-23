import unittest

from murmuration import blocks as B


class BlockAndSummarise(unittest.TestCase):
    def test_groups_by_coupling_threshold(self):
        # a-b and b-c strongly coupled, c-d weak, e alone. Threshold 0.5 -> {a,b,c}, {d}, {e}.
        coupling = {("a", "b"): 0.9, ("b", "c"): 0.6, ("c", "d"): 0.1}
        self.assertEqual(B.groups("abcde", coupling, 0.5), [["a", "b", "c"], ["d"], ["e"]])
        self.assertEqual(B.groups("abcde", coupling, 0.05), [["a", "b", "c", "d"], ["e"]])

    def test_assign_sizes_blocks_by_task_count(self):
        # 6 agents, groups of 3, 1, 1 tasks: one each, then 3 spare split 3*3/5=1.8, 0.6, 0.6
        # -> floors 1,0,0 (+1 each = 2,1,1), 2 left by largest remainder: 0.8 (g0), then 0.6 (g1).
        blocks = B.assign(range(6), [["a", "b", "c"], ["d"], ["e"]])
        self.assertEqual([len(b) for b in blocks], [3, 2, 1])
        self.assertEqual(sum(blocks, []), list(range(6)))

    def test_upward_one_line_per_block(self):
        out = B.upward([["x ok", "y ok"], ["z failed"]], lambda ls: "; ".join(ls))
        self.assertEqual(out, [{"agent": "block-0", "summary": "x ok; y ok"},
                               {"agent": "block-1", "summary": "z failed"}])

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            B.groups("ab", {("a", "q"): 1.0}, 0.5)
        with self.assertRaises(ValueError):
            B.assign(range(1), [["a"], ["b"]])
        with self.assertRaises(ValueError):
            B.upward([["a"]], lambda ls: "two\nlines")
        self.assertEqual(B.assign(range(3), []), [])


if __name__ == "__main__":
    unittest.main()
