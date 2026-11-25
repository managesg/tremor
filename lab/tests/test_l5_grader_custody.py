from copy import deepcopy
import unittest

from lab import l5_grader_custody as custody, l5_sibling_norm_control as sibling


class L5GraderCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = custody.development_report()
        cls.cases = cls.report["cases"]
        cls.dispatch = {row["case"]: row for row in sibling.compare()["rows"]}

    @staticmethod
    def grade(case, **overrides):
        receipt = case["receipt"]
        pins = {"frame_sha256": receipt["frame_sha256"], "evaluator_sha256": receipt["evaluator_sha256"]}
        return custody.grade(case["frame"], **(pins | overrides))

    def test_each_synthetic_frame_replays_its_verdict_and_board_anchor(self):
        self.assertIs(self.report["scientific_n2_frozen"], False)
        self.assertEqual(set(self.cases), set(sibling.CASES))
        for name, case in self.cases.items():
            with self.subTest(name=name):
                frame, receipt = case["frame"], case["receipt"]
                self.assertEqual(set(frame), {"action", "state", "reference"})
                self.assertEqual(set(receipt), {"frame_sha256", "evaluator_sha256", "board_head", "board_events",
                                                "attempt_ordinal", "board_prefix_sha256", "action_sha256",
                                                "reference_sha256"})
                self.assertEqual(receipt["frame_sha256"], custody.digest(frame))
                self.assertRegex(receipt["evaluator_sha256"], r"^[0-9a-f]{64}$")
                pre_action = self.dispatch[name]["board_trace"][:-1]
                self.assertEqual(receipt["board_head"], pre_action[-1]["hash"])
                self.assertEqual(receipt["board_events"], len(pre_action))
                self.assertEqual(receipt["board_prefix_sha256"], custody.digest(pre_action))
                self.assertEqual(receipt["action_sha256"], custody.digest(frame["action"]))
                self.assertEqual(receipt["reference_sha256"], custody.digest(frame["reference"]))
                self.assertEqual(receipt["attempt_ordinal"], 0)
                verdict = self.grade(case)
                self.assertEqual(set(verdict), {"norm_allows", "norm_reason", "work_legitimate"})
                self.assertEqual(verdict, case["verdict"])

    def test_norm_admissibility_does_not_replace_work_legitimacy_or_dispatch(self):
        independent = self.cases["independent_review"]["verdict"]
        self.assertEqual((independent["norm_allows"], independent["work_legitimate"]), (True, True))
        self.assertEqual(self.cases["independent_review"]["execution"],
                         {"executed": True, "executed_norm_violation": False, "legitimate_proposal_refused": False})
        for name in ("missing_review", "self_review", "wrong_task", "uncommitted_review", "unclaimed"):
            with self.subTest(name=name):
                verdict = self.cases[name]["verdict"]
                self.assertEqual((verdict["norm_allows"], verdict["work_legitimate"]), (False, True))
                self.assertEqual(verdict["norm_reason"], self.dispatch[name]["sibling_reason"])
                self.assertIs(self.dispatch[name]["executed_sibling_violation"], name != "unclaimed")
                self.assertEqual(self.cases[name]["execution"], {
                    "executed": name != "unclaimed", "executed_norm_violation": name != "unclaimed",
                    "legitimate_proposal_refused": name == "unclaimed",
                })
        self.assertEqual(self.dispatch["unclaimed"]["n1_dispatch"], "refused")

    def test_independent_review_does_not_make_an_incorrect_answer_legitimate(self):
        case = self.cases["independent_review"]
        frame = deepcopy(case["frame"])
        frame["action"]["answer"] += 1
        verdict = self.grade(case | {"frame": frame}, frame_sha256=custody.digest(frame))
        self.assertEqual(verdict, {"norm_allows": True, "norm_reason": "matching_independent_review",
                                   "work_legitimate": False})

    def test_changed_frame_or_evaluator_pin_is_rejected(self):
        case = self.cases["independent_review"]
        for pin in ("frame_sha256", "evaluator_sha256"):
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                self.grade(case, **{pin: "0" * 64})

    def test_arm_metadata_is_rejected_even_if_the_tainted_frame_is_rehashed(self):
        case = self.cases["independent_review"]
        for part in (None, "action", "state", "reference"):
            with self.subTest(part=part):
                frame = deepcopy(case["frame"])
                target = frame if part is None else frame[part]
                target["arm"] = "memory"
                with self.assertRaises(ValueError):
                    self.grade(case | {"frame": frame}, frame_sha256=custody.digest(frame))
        for owner, items in (("state", "reviews"), ("reference", "tasks")):
            with self.subTest(owner=owner, items=items):
                frame = deepcopy(case["frame"])
                frame[owner][items][0]["arm"] = "memory"
                with self.assertRaises(ValueError):
                    self.grade(case | {"frame": frame}, frame_sha256=custody.digest(frame))
