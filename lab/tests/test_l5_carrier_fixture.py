import unittest

from lab.l5_carrier_fixture import compare


class L5CarrierFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compare()
        cls.rows = {(r["carrier"], r["disrupted"]): r for r in cls.result["rows"]}

    def test_all_conditions_match_task_and_work_budget(self):
        self.assertEqual(len(self.rows), 6)
        baseline = self.rows["neutral", False]
        for row in self.rows.values():
            self.assertEqual(row["taskset"], baseline["taskset"])
            self.assertEqual(row["pre_replacement"], baseline["pre_replacement"])
            self.assertEqual(row["post_replacement"]["opportunities"], 2)
            self.assertEqual(row["carrier_reads"], 4)
            self.assertEqual(row["carrier_bytes_read"], 68)
            self.assertEqual(row["board_ops"]["post"], 4)
            self.assertEqual(row["board_ops"]["end_round"], 4)

    def test_exposure_is_committed_named_read_and_environment_is_sharded(self):
        for (carrier, _), row in self.rows.items():
            trace = row["board_trace"]
            posts = {e["data"]["id"]: e for e in trace if e["type"] == "post"}
            reads = [e for e in trace if e["type"] == "read"]
            self.assertEqual(row["board_head"], trace[-1]["hash"])
            for observed, read in zip(row["exposure"], reads, strict=True):
                posted = posts[observed["item"]]
                self.assertEqual(observed["agent"], read["agent"])
                self.assertEqual(observed["item"], read["data"]["item"])
                self.assertEqual(read["data"]["n"], 1)
                self.assertEqual(observed["text"], posted["data"]["text"])
                self.assertEqual(read["round"], posted["round"] + 1)
            for round_id in (1, 2):
                pair = [e for e in row["exposure"] if e["round"] == round_id]
                self.assertEqual(len({e["item"] for e in pair}), 2 if carrier == "environment" else 1)

    def test_neutral_sham_and_matched_disruption_have_known_outcomes(self):
        for (carrier, disrupted), row in self.rows.items():
            present = carrier != "neutral" and not disrupted
            self.assertEqual(row["score"]["distinct_passing"], 3 if present else 2)
            self.assertEqual(row["post_replacement"]["executed_norm_violations"], 0 if present else 1)
            self.assertEqual(row["post_replacement"]["blocked_norm_allowed_work"], 0 if present else 1)
            self.assertEqual(row["guide_reads"], 0 if carrier == "neutral" else (2 if disrupted else 4))
            self.assertEqual(row["board_ops"]["claim"], 3 if present else 2)
        self.assertEqual(self.rows["neutral", False]["board_sha256"], self.rows["neutral", True]["board_sha256"])

    def test_repeated_replay_is_identical(self):
        self.assertEqual(self.result, compare())


if __name__ == "__main__":
    unittest.main()
