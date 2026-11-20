import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "train"))
import t7_samples as S  # noqa: E402

IDS = ["p%03d" % i for i in range(500)]


class Samples(unittest.TestCase):
    def test_sizes_disjoint_deterministic(self):
        m, s = S.main_ids(IDS), S.smoke_ids(IDS)
        self.assertEqual((len(m), len(s)), (100, 20))
        self.assertEqual((len(set(m)), len(set(s))), (100, 20))
        self.assertFalse(set(m) & set(s))
        self.assertEqual((m, s), (S.main_ids(list(reversed(IDS))), S.smoke_ids(list(reversed(IDS)))))

    def test_real_file_if_present(self):
        p = os.path.join(os.path.dirname(__file__), "..", "data", "math500", "test.jsonl")
        if not os.path.exists(p):
            self.skipTest("no data")
        ids = list(S.load_math500(p))
        self.assertEqual(len(ids), 500)
        self.assertFalse(set(S.main_ids(ids)) & set(S.smoke_ids(ids)))


if __name__ == "__main__":
    unittest.main()
