import unittest

from murmuration import blocks as B


class BlockAndSummarise(unittest.TestCase):
    def test_groups_by_coupling_threshold(self):
        # a-b and b-c strongly coupled, c-d weak, e alone. Threshold 0.5 -> {a,b,c}, {d}, {e}.
        coupling = {("a", "b"): 0.9, ("b", "c"): 0.6, ("c", "d"): 0.1}
        self.assertEqual(B.groups(list("abcde"), coupling, 0.5), [["a", "b", "c"], ["d"], ["e"]])
        self.assertEqual(B.groups(list("abcde"), coupling, 0.05), [["a", "b", "c", "d"], ["e"]])

    def test_assign_sizes_blocks_by_task_count(self):
        # 6 agents over 3, 1, 1 tasks: exact shares 3.6, 1.2, 1.2 -> floors 3, 1, 1, one left goes to the
        # largest fraction (0.6, group 0) -> 4, 1, 1.
        blocks = B.assign(range(6), [["a", "b", "c"], ["d"], ["e"]])
        self.assertEqual([len(b) for b in blocks], [4, 1, 1])
        self.assertEqual(sum(blocks, []), list(range(6)))
        # 10 agents over 9 and 1 tasks: exactly proportional, 9 and 1.
        self.assertEqual([len(b) for b in B.assign(range(10), [list("abcdefghi"), ["j"]])], [9, 1])
        # 3 agents over 8, 1, 1 tasks: shares 2.4, 0.3, 0.3; the minimum of one forces 1, 1, 1.
        self.assertEqual([len(b) for b in B.assign(range(3), [list("abcdefgh"), ["i"], ["j"]])], [1, 1, 1])
        # row-169 verifier: 10 agents over 15, 5, 15, 11, 5 tasks: shares 2.94, 0.98, 2.94, 2.16, 0.98.
        # Floors 2, 0, 2, 2, 0 leave 4 seats; largest fractions .98, .98, .94, .94 -> 3, 1, 3, 2, 1.
        # (The clamped version gave 2, 2, 2, 2, 2.)
        sizes = [len(b) for b in B.assign(range(10), [[f"g{j}t{i}" for i in range(k)] for j, k in enumerate((15, 5, 15, 11, 5))])]
        self.assertEqual(sizes, [3, 1, 3, 2, 1])

    def test_upward_one_line_per_block(self):
        out = B.upward([["x ok", "y ok"], ["z failed"]], lambda ls: "; ".join(ls))
        self.assertEqual(out, [{"agent": "block-0", "summary": "x ok; y ok"},
                               {"agent": "block-1", "summary": "z failed"}])

    def test_malformed_inputs_raise(self):
        with self.assertRaises(ValueError):
            B.groups(["a", "b"], {("a", "q"): 1.0}, 0.5)
        with self.assertRaises(ValueError):
            B.assign(range(1), [["a"], ["b"]])
        with self.assertRaises(ValueError):
            B.assign(range(3), [[], []])  # was ZeroDivisionError
        for call in (lambda: B.groups(["a", "b"], {("a", "b"): 1.0}, float("nan")),
                     lambda: B.groups(["a", "b"], {("a", "b"): float("nan")}, 0.5),
                     lambda: B.groups(["a", "b"], {("a", "b"): None}, 0.5),
                     lambda: B.upward([["a"]], lambda ls: "one\rtwo"),
                     lambda: B.upward([["a"]], lambda ls: "one two"),
                     # re-verifier at 08659a3: strings split into tasks, string keys, duplicates
                     lambda: B.groups("ab", {}, 0.5),
                     lambda: B.assign(range(3), "abc"),
                     lambda: B.groups(["a", "b"], {"ab": 1.0}, 0.5),
                     lambda: B.assign(range(4), [["a", "a", "a"], ["b"]]),
                     lambda: B.groups(["a"], [("a", "a")], 0.5),
                     lambda: B.upward([["a"]], lambda ls: "a "),
                     lambda: B.upward([["a"]], lambda ls: "a\x1c")):
            with self.assertRaises(ValueError):
                call()
        with self.assertRaises(ValueError):
            B.upward([["a"]], lambda ls: "two\nlines")
        self.assertEqual(B.assign(range(3), []), [])


if __name__ == "__main__":
    unittest.main()
