import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from lab import l5_matrix, l5_matrix_phase_scores


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MatrixPhaseScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(cls.enterClassContext(TemporaryDirectory()))
        for contended in (False, True):
            l5_matrix.run(cls.root / str(contended), seed=86, contended=contended)

    def test_scores_close_at_the_opening_and_post_commits(self):
        for contended in (False, True):
            with self.subTest(contended=contended):
                root = self.root / str(contended)
                summary = root / "summary.json"
                result = l5_matrix_phase_scores.verify(root, summary_sha256=_digest(summary))
                self.assertFalse(result["authorizes_execution"])
                self.assertEqual(len(result["phase_scores"]), 20)
                for saved, arm in zip(json.loads(summary.read_bytes())["rows"], result["phase_scores"], strict=True):
                    opening = arm["opening_work"]
                    after = arm["post_work"]
                    self.assertEqual((opening["round"], after["round"]), (2, 4) if contended else (1, 3))
                    self.assertEqual(opening["score"]["distinct_passing"], 1)
                    self.assertEqual(arm["physical_round_one_score"], None if contended else opening["score"])
                    self.assertEqual(after["work_attempts"], saved["attempted_work"] - 1)
                    self.assertEqual(arm["terminal_score"], saved["score"])

    def test_re_pinned_shifted_phase_cannot_turn_opening_work_into_post_work(self):
        with TemporaryDirectory() as scratch:
            clone = Path(scratch) / "clone"
            shutil.copytree(self.root / "True", clone)
            summary_path = clone / "summary.json"
            summary = json.loads(summary_path.read_bytes())
            first = summary["rows"][0]
            dispatch = next(event for event in first["dispatch"] if event["action"]["type"] == "work")
            dispatch["phase"] = first["work"][0]["phase"] = "post"
            arm_path = clone / first["arm_id"] / "result.json"
            arm_path.write_text(json.dumps({key: value for key, value in first.items() if key != "result_sha256"}))
            first["result_sha256"] = _digest(arm_path)
            summary_path.write_text(json.dumps(summary))
            with self.assertRaisesRegex(ValueError, "phase does not match"):
                l5_matrix_phase_scores.verify(clone, summary_sha256=_digest(summary_path))

    def test_verified_stopped_prefix_cannot_be_mistaken_for_a_zero_score(self):
        with patch.object(l5_matrix_phase_scores.l5_matrix_partial, "verify",
                          return_value={"status": "incomplete", "comparison": None}) as verify:
            result = l5_matrix_phase_scores.verify_partial("bundle", index_sha256="a" * 64)
        verify.assert_called_once_with("bundle", index_sha256="a" * 64)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["comparison"])
        self.assertIsNone(result["phase_scores"])
        self.assertFalse(result["authorizes_execution"])
