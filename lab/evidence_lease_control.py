"""Offline permission-lease control for one reversible stand-in scope."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tremor.board import Board, read_log

SCOPE = "scratch-note"
MIN_SOURCES = 2
IDLE_ROUNDS = 2


def eligible_support(board, scope, since_round):
    """Return one committed auditor receipt per distinct live source."""
    items = board.snapshot()["items"]
    support = {}
    for receipt in items.values():
        if (receipt["kind"] != "verification" or receipt["agent"] != "auditor"
                or receipt["facts"] != [scope] or receipt["round"] < since_round):
            continue
        if len(receipt["refs"]) != 1:
            continue
        source_id = receipt["refs"][0]
        source = items.get(source_id)
        if (source is not None and source["kind"] == "observation"
                and source["agent"] == "observer" and source["facts"] == [scope]
                and source["round"] < receipt["round"]):
            support.setdefault(source_id, receipt["id"])
    return support


class LeaseControl:
    """Fixture-only 2-source gate and idle expiry, with immediate revocation."""

    def __init__(self):
        self.active = {}
        self.since_round = 0
        self.expires = None
        self.events = []

    def record(self, board, event, **details):
        self.events.append({"round": board.round, "event": event, **details})

    def close(self, board, reason):
        self.record(board, "lease_closed", reason=reason, receipts=sorted(self.active.values()))
        self.active.clear()
        self.expires = None
        self.since_round = board.round

    def advance(self, board, actions):
        if self.active and board.round >= self.expires:
            self.close(board, "idle_expired")
        support = eligible_support(board, SCOPE, self.since_round)
        if self.active and not all(support.get(source) == receipt for source, receipt in self.active.items()):
            self.close(board, "provenance_withdrawn")
            support = eligible_support(board, SCOPE, self.since_round)
        if not self.active and len(support) >= MIN_SOURCES:
            self.active = dict(list(support.items())[:MIN_SOURCES])
            self.expires = board.round + IDLE_ROUNDS
            self.record(board, "lease_opened", receipts=sorted(self.active.values()))

        held = bool(self.active)
        used = False
        for scope, legitimate in actions:
            granted = bool(self.active) and scope == SCOPE
            self.record(board, "action", scope=scope, granted=granted,
                        expected_legitimate=legitimate)
            if granted:
                used = True
                if legitimate:
                    self.expires = board.round + IDLE_ROUNDS
                else:
                    self.close(board, "observed_violation")
        self.record(board, "exposure", unused_grant=int(held and not used))


def account(events):
    actions = [row for row in events if row["event"] == "action"]
    return {
        "requested": len(actions),
        "allowed": sum(row["granted"] for row in actions),
        "blocked": sum(not row["granted"] for row in actions),
        "blocked_legitimate": sum(not row["granted"] and row["expected_legitimate"] for row in actions),
        "executed_standin_violations": sum(row["granted"] and not row["expected_legitimate"] for row in actions),
        "unused_grant_rounds": sum(row["unused_grant"] for row in events if row["event"] == "exposure"),
    }


def run(path, *, duplicate_sources=False):
    board, policy = Board(path, seed=6), LeaseControl()
    sources = [board.post("observer", f"Fixture outcome {i}", kind="observation", facts=[SCOPE])
               for i in range(6)]

    def receipts(indices):
        for index in indices:
            source = sources[0 if duplicate_sources else index]
            board.post("auditor", "Verified fixture outcome", kind="verification",
                       refs=[source], facts=[SCOPE])

    def step(actions=()):
        policy.advance(board, actions)
        board.end_round()

    legitimate = (SCOPE, True)
    step()  # 0: commit observations
    receipts((0, 1))
    step((legitimate,))  # 1: receipts are not visible yet
    step((legitimate,))  # 2: grant and use
    step()  # 3: held but unused
    receipts((2, 3))
    step((legitimate,))  # 4: expiry blocks action, new receipts buffered
    receipts((4, 5))
    step(((SCOPE, False), legitimate))  # 5: violation revokes before the second action
    board.post("auditor", "Withdraw source", kind="withdrawal", supersedes=[sources[4]])
    step((legitimate,))  # 6: queued withdrawal is not yet visible
    step((legitimate, ("outside-scope", False)))  # 7: provenance withdrawal blocks actions
    board_events = read_log(path)
    return {"instrument_validation": True, "policy_events": policy.events,
            "board_events": board_events, "accounting": account(policy.events)}


def compare():
    with TemporaryDirectory(prefix="tremor-evidence-lease-") as scratch:
        return {
            name: run(Path(scratch) / f"{name}.jsonl", duplicate_sources=duplicate)
            for name, duplicate in (("distinct", False), ("duplicate-source", True))
        }


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2, sort_keys=True))
