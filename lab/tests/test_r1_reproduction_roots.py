import unittest

from tremor.readouts import reproduction_number


class ReproductionRootTests(unittest.TestCase):
    notes = [{"id": "root", "parents": []}, {"id": "child", "parents": ["root"]}]

    def test_one_shot_duplicate_roots_match_a_reusable_collection(self):
        self.assertEqual(reproduction_number(self.notes, iter(["root", "root"])), (0.5, 2))
        self.assertEqual(reproduction_number(self.notes, ["root"]), (0.5, 2))

    def test_empty_roots_preserve_legacy_no_adopter_sentinel(self):
        self.assertEqual(reproduction_number(self.notes, iter(())), (0.0, 0))
