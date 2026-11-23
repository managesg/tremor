"""Offline L2 instrument control for named exposure and scored adoption."""

import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from murmuration.board import Board, read_log
from murmuration.readouts import first_generation_offspring

CONDITIONS = ("neutral", "warning", "clean", "unseen_parent", "late")
WINDOW_END = 1
LEDGER_VALUE = "green"
PLANTED_VALUE = "blue"


def score_value(value):
    """Adjudicate only the decision value against the fixture's separate ledger."""
    if value == LEDGER_VALUE:
        return "correct"
    if value == PLANTED_VALUE:
        return "planted_value"
    return "other_wrong_value"


def measure(path, parent, workers, *, planted_root_ids):
    """Replay actual committed reads; score only the first eligible decision per worker."""
    trace = read_log(path)
    planted_root_ids = set(planted_root_ids)
    if not trace or trace[-1]["type"] != "end_round" or trace[-1]["round"] < WINDOW_END:
        raise ValueError("missing completed decision window")
    active, named, submitted = set(), {}, set()
    pending, notes, planted, decisions = [], [], [], []
    for event in trace:
        agent, kind, data = event["agent"], event["type"], event["data"]
        in_window = event["round"] <= WINDOW_END
        if kind == "read" and in_window and agent in workers and parent in active:
            if data["item"] == parent and data["n"] == 1:
                named.setdefault(agent, event["seq"])
        elif kind == "post":
            parents = []
            if data["kind"] == "decision" and agent in workers:
                grade = score_value(data["text"])
                if not in_window:
                    eligibility = "late"
                elif data["refs"] != [parent] or parent not in active or agent not in named:
                    eligibility = "no_named_visible_parent"
                elif agent in submitted:
                    eligibility = "duplicate"
                else:
                    eligibility = "eligible"
                    submitted.add(agent)
                    if grade == "planted_value" and parent in planted:
                        parents = [parent]
                decisions.append({"post": data["id"], "worker": agent, "round": event["round"],
                                  "exposure_seq": named.get(agent), "grade": grade, "adopted": bool(parents),
                                  "eligibility": eligibility})
            pending.append((data, parents))
        elif kind == "end_round":
            for post, parents in pending:
                ident = post["id"]
                notes.append({"id": ident, "parents": parents})
                if event["round"] == 0 and post["kind"] == "plant" and ident in planted_root_ids:
                    planted.append(ident)
                active.difference_update(post["supersedes"])
                active.add(ident)
            pending.clear()

    if set(planted) != planted_root_ids:
        raise ValueError("declared roots must be committed plants from the opening round")
    scored = [decision for decision in decisions if decision["eligibility"] == "eligible"]
    adoption_count = sum(decision["adopted"] for decision in scored)
    mean, counts = first_generation_offspring(notes, planted) if planted else (None, {})
    return {
        "scheduled_workers": list(workers), "named_exposure_sequences": named,
        "exposure_denominator": len(named), "scored_decisions": len(scored),
        "adoption_count": adoption_count, "adoption_rate": adoption_count / len(named) if named else None,
        "eligible_without_scored_decision": sorted(set(named) - submitted),
        "decisions": decisions, "first_generation_adoption_mean": mean,
        "first_generation_counts": counts, "trace": trace,
    }


def _observed_decision(decide, worker, instruction, source, *, board, reference_id):
    observed = (worker, instruction["text"], source["id"], source["text"])
    if reference_id is None:
        reply = decide(*observed)
    else:
        may_read = True

        def read_reference():
            nonlocal may_read
            if not may_read:
                raise ValueError("reference read is closed for this turn")
            may_read = False
            item = board.read(worker, reference_id)
            return None if item is None else {"id": item["id"], "text": item["text"]}

        try:
            reply = decide(*observed, read_reference)
        finally:
            may_read = False
    if type(reply) is not dict or reply.keys() != {"value", "source_id"}:
        return None
    value, source_id = reply["value"], reply["source_id"]
    if type(source_id) is not str or source_id != source["id"]:
        return None
    if type(value) is not str or re.fullmatch(r"[a-z]{1,16}", value) is None:
        return None
    return value, source_id


def run(path, condition, *, decide=None, reference_text=None):
    """Replay scripted choices or ask a callback given only the actual named reads.

    The callback receives worker ID, instruction text, source ID, and source
    text. It may return a lowercase ASCII marker in a {value, source_id} dict
    citing that observed source, or None to abstain. Scoring runs separately.
    With reference_text, the callback also receives one callable for a named
    read of that fixed source. The callable closes when the turn ends.
    """
    if condition not in CONDITIONS:
        raise ValueError("unknown fixture condition")
    if reference_text is not None and (decide is None or not isinstance(reference_text, str) or not reference_text.strip()):
        raise ValueError("reference text requires a decision callback and a nonempty source")
    Path(path).touch(exist_ok=False)
    board = Board(path, seed=2)
    warning = condition == "warning"
    clean = condition == "clean"
    line = ("Verify the marker against the paper ledger before logging it." if warning
            else "Record the marker in the assigned box for this decision turn.")
    instruction = board.post("facilitator", line, kind="instruction")
    parent = board.post("source", f"Marker: {LEDGER_VALUE if clean else PLANTED_VALUE}",
                        kind="reference" if clean else "plant")
    roots = ()
    if not clean:
        other = board.post("source", "Other marker: orange", kind="plant")
        roots = (parent, other)
    reference_id = None if reference_text is None else board.post("reference", reference_text, kind="verification")
    board.end_round()

    workers = ("a", "b") if condition in ("neutral", "warning", "clean") else ("a",)
    late = condition == "late"
    delayed = []
    for worker in workers:
        instruction_read = board.read(worker, instruction)
        source_read = board.read(worker, other if condition == "unseen_parent" else parent)
        if decide is None:
            value = LEDGER_VALUE if clean or (warning and worker == "b") else PLANTED_VALUE
            decision = (value, parent)
        elif instruction_read is None or source_read is None:
            decision = None
        else:
            decision = _observed_decision(decide, worker, instruction_read, source_read,
                                          board=board, reference_id=reference_id)
        if decision is None:
            continue
        value, source_id = decision
        if late:
            delayed.append((worker, value, source_id))
        else:
            # Preserve the archived fixture annotation for scripted choices.
            position = "unverified self-report" if decide is None else None
            board.post(worker, value, kind="decision", refs=(source_id,), position=position)
    board.end_round()
    if late:
        for worker, value, source_id in delayed:
            board.post(worker, value, kind="decision", refs=(source_id,))
        board.end_round()
    return measure(path, parent, workers, planted_root_ids=roots)


def compare():
    with TemporaryDirectory(prefix="tremor-l2-adoption-") as scratch:
        return {"instrument_validation": True,
                "conditions": {name: run(Path(scratch) / f"{name}.jsonl", name) for name in CONDITIONS}}


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True, allow_nan=False))
