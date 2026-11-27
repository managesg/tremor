import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab import pilot3_prompt_replay as replay
from tremor import team_claude


ROOT = Path(__file__).resolve().parents[2]
EPISODES = ROOT / "runs" / "ep1-live" / "pilot3" / "episodes.jsonl"
LEDGER = ROOT / "runs" / "spend" / "pilot3.jsonl"


class ArchiveIdentityTests(unittest.TestCase):
    def test_changed_archive_is_rejected_before_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / "changed.jsonl"
            changed.write_text('{"note":"synthetic substitute"}\n')
            with patch.object(replay, "_replay_episode") as run:
                with self.assertRaisesRegex(ValueError, "archive digest mismatch"):
                    replay.audit(changed, changed)
            run.assert_not_called()


@unittest.skipUnless(EPISODES.is_file() and LEDGER.is_file(), "requires the private Pilot 3 archive")
class ArchiveReplayTests(unittest.TestCase):
    def test_both_candidates_preserve_the_archived_instrument_except_for_the_final_instruction(self):
        result = replay.audit(EPISODES, LEDGER)
        self.assertEqual(result["episodes"], 30)
        self.assertEqual(result["baseline_request_hash_matches"], 240)
        self.assertEqual(result["baseline_prompt_hash_matches"], 240)
        self.assertEqual(result["episode_score_and_board_matches_per_variant"], 30)
        self.assertEqual(result["baseline"]["max_request_bytes"], 1509)
        self.assertEqual({name: value["max_request_bytes"] for name, value in result["candidates"].items()},
                         {"packet": 1582, "array_only": 1586})
        for candidate in result["candidates"].values():
            self.assertEqual(candidate["first_round_unchanged"], 120)
            self.assertEqual(candidate["second_round_only_instruction_changed"], 120)
        self.assertEqual(len({row["serialized_request_sequence_sha256"] for row in (
            result["baseline"], *result["candidates"].values(),
        )}), 3)

    def test_unrelated_prompt_edit_breaks_historical_request_identity(self):
        original = team_claude._ModelEpisode.prompt

        def drift(*args):
            system, user = original(*args)
            return system + " ", user

        with patch.object(team_claude._ModelEpisode, "prompt", drift):
            with self.assertRaisesRegex(ValueError, "baseline request hash differs from ledger"):
                replay.audit(EPISODES, LEDGER)
