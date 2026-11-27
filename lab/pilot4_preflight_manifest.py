"""Build a review-only Pilot 4 manifest from pinned Pilot 3 evidence."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path

from lab import pilot3_prompt_replay as replay
from tremor import ep1, spend, team_claude


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "runs" / "ep1-live" / "pilot3"
LEDGER = ROOT / "runs" / "spend" / "pilot3.jsonl"
PRICE_SHEET = ROOT / "docs" / "reports" / "price-sheet.json"
SCHEDULE_SHA256 = "2a0188449dff2b411c67b603473349325ad8148afbaa74ef2d109d84a55ce003"
PRICE_SHEET_SHA256 = "16b204c23aa5ce3b169e44a3b2608ee39e3aa8da14b6b1838d8cb15a3356984f"
BATCH = "pilot4"
PREFIX = "p4"
CANDIDATE_REQUEST_SHA256 = {
    "packet": "7a2efdee1ba195ed5674e305e73c0b20e94894d0197587c8235056f00cc07499",
    "array_only": "8d8c681b424b5772f9c6513ad368e58e36c0a2441bfd766f1b7a9e96fe0eb192",
}


def _require(condition, detail):
    if not condition:
        raise ValueError(detail)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pinned_json(path, expected):
    data = path.read_bytes()
    _require(_sha(data) == expected, "historical input digest mismatch")
    return json.loads(data, parse_float=Decimal)


def _candidate_schedule(archive, rows, model):
    historical = _pinned_json(archive / "schedule.json", SCHEDULE_SHA256)
    blocks = ep1.plan("pilot3", 0)
    _require(historical["kind"] == "pilot3" and historical["model"] == model
             and historical["schedule_seed"] == 0 and historical["plan"] == blocks,
             "historical schedule does not match seed-zero Pilot 3 plan")
    _require(BATCH in ep1.KINDS and spend.BATCH_SPECS[BATCH] == spend.BATCH_SPECS["pilot3"]
             and ep1.ID_PREFIX[BATCH] == PREFIX and ep1.plan(BATCH, 0) == blocks,
             "registered pilot4 spec, prefix or plan differs from the expected ones")
    cells = [(block, condition) for block in blocks for condition in block["order"]]
    _require(len(rows) == len(cells) == 30, "expected thirty historical episodes")
    schedule = []
    old_ids, new_ids = set(), set()
    historical_prefix = ep1.ID_PREFIX["pilot3"]
    for row, (block, condition) in zip(rows, cells, strict=True):
        task_order = block["task_order"]
        tag_suffix = ep1.ORDER_TAG.get(task_order, "") + ep1.COND_TAG.get(condition, "")
        expected_tag = historical_prefix + tag_suffix
        arm = condition if condition in ep1.BASE_CONDS else "play"
        _require(row["batch"] == row["kind"] == "pilot3" and row["attempt"] == 0
                 and row["set"] == row["seed"] == block["set"] and row["schedule_seed"] == 0
                 and row["cond"] == condition and row["arm"] == arm and row["task_order"] == task_order
                 and row["block_order"] == block["order"] and row["id_tag"] == expected_tag
                 and block["split"] == "train" and row["ended"] == "complete",
                 "historical episode does not match the planned cell")
        suffix = f"-{arm}-t{row['set']}-s{row['seed']}"
        historical_id = f"ep1{expected_tag}{suffix}"
        prospective_id = f"ep1{PREFIX}{tag_suffix}{suffix}"
        _require(row["episode_id"] == historical_id and row["calls"] == len(row["turns"]) == 8,
                 "historical episode ID or call count mismatch")
        calls = []
        turn_order = []
        for turn in row["turns"]:
            turn_order.append((turn["round"], turn["agent"]))
            call_suffix = f":r{turn['round']}:{turn['agent']}"
            _require(turn["call_id"] == historical_id + call_suffix, "historical call ID mismatch")
            old_ids.add(turn["call_id"])
            calls.append(prospective_id + call_suffix)
        _require(turn_order == [(round_id, f"a{agent}") for round_id in range(2) for agent in range(4)],
                 "historical call order mismatch")
        old_ids.add(historical_id)
        new_ids.update((prospective_id, *calls))
        schedule.append({"set": row["set"], "condition": condition, "task_order": task_order,
                         "episode_id": prospective_id, "call_ids": calls})
    _require(len(old_ids) == len(new_ids) == 270 and old_ids.isdisjoint(new_ids),
             "planned episode or call ID collision")
    return schedule


def _budget(price_sheet, model, planned_calls):
    historical_policy = spend.BATCH_SPECS["pilot3"]
    _require((historical_policy["calls"], historical_policy["tokens"], historical_policy["usd"]) ==
             (260, 598_000, 0.25), "historical pilot budget differs from the review envelope")
    inputs, outputs = spend.PER_CALL_INPUT_TOKENS, spend.PER_CALL_OUTPUT_TOKENS
    _require((inputs, outputs) == (2000, 300) and ep1.CALLS_PER_EPISODE == 8
             and (team_claude.CAPS["input_tokens"], team_claude.CAPS["output_tokens"]) == (inputs, outputs),
             "instrument caps differ from the review envelope")
    prices = _pinned_json(price_sheet, PRICE_SHEET_SHA256)["models"][model]
    input_rate = max(prices["input"], prices["cache_write_5m"], prices["cache_write_1h"])
    output_rate = prices["output"]
    ceiling = Decimal("0.25")
    attempt_cost = (inputs * input_rate + outputs * output_rate) / 1_000_000
    total_cost = 260 * attempt_cost
    _require(inputs < prices["long_context"]["threshold_input_tokens"]
             and 260 * (inputs + outputs) == 598_000 and 260 - planned_calls == 20
             and total_cost == Decimal("0.143") and total_cost <= ceiling,
             "historical price-sheet reservation arithmetic mismatch")
    return {
        "planned_calls": planned_calls, "max_attempts": 260, "extra_attempt_allowance": 20,
        "max_reserved_tokens": 598_000, "request_byte_cap": inputs,
        "assumed_input_token_upper_bound": inputs, "output_token_cap": outputs,
        "ceiling_usd": str(ceiling), "historical_price_sheet_sha256": PRICE_SHEET_SHA256,
        "historical_input_usd_per_million": str(input_rate),
        "historical_output_usd_per_million": str(output_rate),
        "modeled_max_reservation_usd": str(total_cost),
        "modeled_per_attempt_reservation_usd": str(attempt_cost),
        "pricing_assumption": "Serialized text request bytes bound input tokens under the recorded client model.",
        "pricing_review_status": "pending",
    }


def build_manifest(archive=ARCHIVE, ledger=LEDGER, price_sheet=PRICE_SHEET):
    """Replay pinned inputs offline and leave both proposed instructions unselected."""
    episodes = archive / "episodes.jsonl"
    rows = replay._read_archive(episodes, replay.EPISODES_SHA256)
    model = ep1.MODEL
    _require(model == "claude-haiku-5-5", "model differs from the review envelope")
    schedule = _candidate_schedule(archive, rows, model)
    planned_calls = sum(len(row["call_ids"]) for row in schedule)
    budget = _budget(price_sheet, model, planned_calls)
    evidence = replay.audit(episodes, ledger)
    _require(evidence["episodes"] == evidence["episode_score_and_board_matches_per_variant"] == len(schedule)
             and evidence["baseline_request_hash_matches"] == evidence["baseline_prompt_hash_matches"] == planned_calls,
             "archived replay count mismatch")
    _require(evidence["candidates"].keys() == CANDIDATE_REQUEST_SHA256.keys(),
             "wording candidate inventory changed")
    candidates = {}
    for name, result in evidence["candidates"].items():
        _require(result["serialized_request_sequence_sha256"] == CANDIDATE_REQUEST_SHA256[name],
                 "wording candidate request digest changed")
        _require(result["first_round_unchanged"] == result["second_round_only_instruction_changed"] == 120
                 and result["max_request_bytes"] <= budget["request_byte_cap"],
                 "candidate request replay exceeds the review envelope")
        candidates[name] = {**result, "wording_sha256": _sha(replay.CANDIDATES[name].encode())}
    return {
        "status": "awaiting_review", "author_review_status": "pending",
        "selected_candidate": None, "execution_authorized_by_manifest": False,
        "batch": BATCH, "ledger_id": "runs/spend/pilot4.jsonl", "output_id": "runs/ep1-live/pilot4",
        "model": model, "schedule_seed": 0, "episode_count": len(schedule), "schedule": schedule,
        "prospective_schedule_sha256": _sha(json.dumps(schedule, sort_keys=True, separators=(",", ":")).encode()),
        "pilot3_archive_sha256": {**evidence["archive_sha256"], "schedule": SCHEDULE_SHA256},
        "baseline_request_replay": evidence["baseline"], "wording_candidate_replays": candidates,
        "reservation": budget,
    }


if __name__ == "__main__":
    print(json.dumps(build_manifest(), sort_keys=True, indent=2))
