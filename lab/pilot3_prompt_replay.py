"""Replay two second-round wording candidates against the immutable Pilot 3 archive."""

import argparse
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from murmuration import backend_claude, ep1, team_claude
from murmuration.trapbench import alloc

EPISODES_SHA256 = "04401ed5cf7d07e82e65bfa95d792234ac201cb591b12419434bbff6c2e4e0f6"
LEDGER_SHA256 = "142b7fef649bb0fe187ebf7fc5cb21e13a7bf4be17756cd9927c1eceae6117e1"
BASELINE = "Reply with one JSON array."
CANDIDATES = {
    "packet": "Return only the JSON action array. Start with [ and end with ]. Omit calculations and explanations.",
    "array_only": "Return exactly one JSON action array, starting with [ and ending with ]. Do not include any other text.",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read_archive(path, digest):
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == digest, "archive digest mismatch")
    return [json.loads(line) for line in data.splitlines()]


def _replace_instruction(user, wording):
    _require(user.endswith(BASELINE), "baseline instruction mismatch")
    return user[:-len(BASELINE)] + wording


def _serialize(payload):
    return json.dumps(payload, sort_keys=True).encode()


class _ArchiveClient:
    def __init__(self, row):
        self.turns = {turn["call_id"]: turn for turn in row["turns"]}
        self.requests = {}

    def call(self, episode, call_id, model, messages, max_tokens, temperature=0.0, system=None, **_kwargs):
        _require(call_id not in self.requests, "duplicate replay call")
        self.requests[call_id] = {
            "model": model, "max_tokens": max_tokens, "temperature": temperature,
            "messages": messages, "system": system, "thinking": dict(backend_claude.THINKING_OFF),
        }
        turn = self.turns[call_id]
        return dict(turn, id=call_id, text=turn["reply"])


def _replay_episode(row, wording):
    model_prompt = team_claude._ModelEpisode.prompt

    def candidate_prompt(episode, agent, round_index, view):
        system, user = model_prompt(episode, agent, round_index, view)
        if round_index == 1:
            user = _replace_instruction(user, wording)
        return system, user

    taskset = alloc.gen(row["set"], "train")
    card = "A" if row["cond"] in ep1.BASE_CONDS else ep1._pilot_card(row["cond"])
    client = _ArchiveClient(row)
    change = nullcontext() if wording is None else patch.object(team_claude._ModelEpisode, "prompt", candidate_prompt)
    with change:
        replay = team_claude.run_episode_model(
            taskset, row["arm"], card, client, seed=row["set"], batch="pilot3",
            caps={"id_tag": row["id_tag"], "task_order": row["task_order"]},
        )
    _require(all(replay[field] == row[field] for field in ("Y", "scores", "board_head", "ended")),
             "archived episode result mismatch")
    _require(list(client.requests) == list(client.turns), "archived call sequence mismatch")
    return client.requests


def _measure(bodies):
    return {
        "serialized_request_sequence_sha256": hashlib.sha256(
            b"".join(hashlib.sha256(body).digest() for body in bodies)
        ).hexdigest(),
        "max_request_bytes": max(map(len, bodies)),
    }


def audit(episodes_path, ledger_path):
    """Return only verification counts and hashes for the pinned historical archive."""
    rows = _read_archive(episodes_path, EPISODES_SHA256)
    ledger = _read_archive(ledger_path, LEDGER_SHA256)
    request_hashes = {row["id"]: row["request_sha256"] for row in ledger if row["kind"] == "charge"}
    bodies = {name: [] for name in ("baseline", *CANDIDATES)}
    counts = {name: {"first_round_unchanged": 0, "second_round_only_instruction_changed": 0}
              for name in CANDIDATES}
    for row in rows:
        requests = _replay_episode(row, None)
        variants = {name: _replay_episode(row, text) for name, text in CANDIDATES.items()}
        for turn in row["turns"]:
            call_id = turn["call_id"]
            baseline = requests[call_id]
            serialized = _serialize(baseline)
            _require(hashlib.sha256(serialized).hexdigest() == request_hashes[call_id],
                     "baseline request hash differs from ledger")
            message, = baseline["messages"]
            content = message["content"]
            prompt = (baseline["system"] + "\n" + content).encode()
            _require(hashlib.sha256(prompt).hexdigest() == turn["prompt_sha256"], "baseline prompt hash mismatch")
            bodies["baseline"].append(serialized)
            for name, wording in CANDIDATES.items():
                candidate = variants[name][call_id]
                if turn["round"] == 0:
                    _require(candidate == baseline, "first-round request changed")
                    counts[name]["first_round_unchanged"] += 1
                else:
                    expected = dict(baseline, messages=[dict(message, content=_replace_instruction(content, wording))])
                    _require(candidate == expected, "second-round request differs outside the candidate instruction")
                    counts[name]["second_round_only_instruction_changed"] += 1
                bodies[name].append(_serialize(candidate))
    return {
        "archive_sha256": {"episodes": EPISODES_SHA256, "ledger": LEDGER_SHA256},
        "episodes": len(rows), "baseline_request_hash_matches": len(bodies["baseline"]),
        "baseline_prompt_hash_matches": len(bodies["baseline"]),
        "episode_score_and_board_matches_per_variant": len(rows),
        "baseline": _measure(bodies["baseline"]),
        "candidates": {name: {**_measure(bodies[name]), **counts[name]} for name in CANDIDATES},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episodes", type=Path)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    try:
        results = audit(args.episodes, args.ledger)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(2, f"Pilot 3 prompt replay failed ({type(error).__name__}).\n")
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
