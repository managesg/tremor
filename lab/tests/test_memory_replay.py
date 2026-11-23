import unittest

from lab import memory_replay


class MemoryReplayTests(unittest.TestCase):
    def test_clean_and_planted_controls(self):
        for trial in memory_replay.compare()["runs"]:
            with self.subTest(planted=trial["planted"], verified=trial["verified_replay"]):
                discrepancy = ["flag"] if trial["planted"] and not trial["verified_replay"] else []
                self.assertEqual([r["unverified_notes"] for r in trial["nights"]], [discrepancy] * 3)
                if trial["planted"] and trial["verified_replay"]:
                    first = trial["nights"][0]
                    self.assertEqual(first["dropped"], ["flag"])
                    self.assertEqual([n["id"] for n in first["input"]], ["pH", "flag"])
                    self.assertEqual([n["id"] for n in first["output"]], ["n1-pH"])

    def test_lineage_resolves_to_input_and_source_across_nights(self):
        trial = memory_replay.run(planted=True, verify=True)
        for record in trial["nights"]:
            inputs = {note["id"]: note for note in record["input"]}
            for note in record["output"]:
                parent, = note["parents"]
                self.assertEqual(inputs[parent]["sources"], note["sources"])
                self.assertEqual(trial["source_log"][note["sources"][0]], note["text"])
            self.assertEqual(record["tokens_read"], sum(len(n["text"].split()) for n in inputs.values()))
        chain = trial["nights"][-1]["output"][0]
        self.assertEqual(chain["id"], "n3-n2-n1-pH")
        self.assertEqual(chain["sources"], ["day-1:pH"])

    def test_first_night_has_equal_note_read_volume(self):
        for planted in (False, True):
            placebo = memory_replay.run(planted=planted, verify=False)
            verified = memory_replay.run(planted=planted, verify=True)
            self.assertEqual(placebo["nights"][0]["input"], verified["nights"][0]["input"])
            self.assertEqual(placebo["nights"][0]["tokens_read"], verified["nights"][0]["tokens_read"])
            self.assertEqual(placebo["nights"][0]["verification"], [])
            self.assertGreater(len(verified["nights"][0]["verification"]), 0)
