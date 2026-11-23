import unittest

from lab.l2_trigger_control import compare


class TriggerControlTests(unittest.TestCase):
    def test_fixture_matches_decisions_schedule_and_source_width(self):
        cases = compare()["conditions"]
        source = {}
        schedules = []
        for name, result in cases.items():
            trace = result["trace"]
            source[name], = [event["data"]["text"] for event in trace if event["agent"] == "source"]
            schedules.append([(row["seq"], row["round"], row["type"], row["agent"]) for row in trace])
            self.assertEqual(result["named_exposure_sequences"], cases["clean"]["named_exposure_sequences"])
            self.assertEqual((result["exposure_denominator"], result["scored_decisions"]), (2, 2))
            self.assertEqual([row["grade"] for row in result["decisions"]], ["planted_value", "correct"])
            self.assertEqual([row["eligibility"] for row in result["decisions"]], ["eligible", "eligible"])
        self.assertEqual(schedules[0], schedules[1])
        self.assertEqual(schedules[1], schedules[2])
        self.assertEqual(source["clean"].replace("Tag=A", "Tag=B"), source["trigger_only"])
        self.assertEqual(source["trigger_only"].replace("green", "blue "), source["false_source"])
        self.assertEqual(len({len(text.encode()) for text in source.values()}), 1)

    def test_matching_false_value_only_counts_with_a_planted_source(self):
        cases = compare()["conditions"]
        for name in ("clean", "trigger_only"):
            result = cases[name]
            self.assertFalse(result["decisions"][0]["adopted"])
            self.assertEqual((result["adoption_count"], result["adoption_rate"]), (0, 0.0))
            self.assertIsNone(result["first_generation_adoption_mean"])
            self.assertEqual(result["first_generation_counts"], {})
        false_source = cases["false_source"]
        self.assertEqual([row["adopted"] for row in false_source["decisions"]], [True, False])
        self.assertEqual((false_source["adoption_count"], false_source["adoption_rate"]), (1, 0.5))
        self.assertEqual(false_source["first_generation_counts"], {"p2": 1})
        self.assertEqual(false_source["first_generation_adoption_mean"], 1.0)
