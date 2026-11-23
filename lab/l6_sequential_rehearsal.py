"""Exercise the unpooled L6 bound in the inert matched lease fixture."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import l6_confidence_sequence as bound, l6_matched_comparators as fixture

ALPHA = 0.05
TARGET = 0.9
IDLE_ROUNDS = 4


class SequentialPolicy(fixture.Policy):
    """Rehearse the opening and revocation paths with labeled fixture settings."""

    def __init__(self):
        super().__init__("sequential")
        self.executions = []
        self.verifications = []
        self.sequence = 0
        self.closed_sequence = 0
        self.verified_at_close = 0
        self.latest = None

    def record_execution(self, request):
        self.sequence += 1
        self.executions.append(bound.Execution(request.id, request.scope, self.sequence))

    def evidence(self):
        return bound.snapshot(self.executions, self.verifications, scope=fixture.SCOPE,
                              as_of=self.sequence, alpha=ALPHA)

    def decision_snapshot(self):
        return self.latest

    def close(self, round_id):
        self.verified_at_close = self.evidence()["trials"]
        self.closed_sequence = self.sequence
        super().close(round_id)

    def begin(self, board, _timebox_authorized):
        reason = None
        if self.deadline is not None and board.round >= self.deadline:
            self.close(board.round)
            reason = "idle_expired"
        observed = self.evidence()
        self.latest = {**observed, "verified_at_close": self.verified_at_close}
        fresh = (observed["trials"] > self.verified_at_close
                 and self.executions[observed["trials"] - 1].sequence > self.closed_sequence)
        opened = (self.deadline is None and fresh
                  and observed["unresolved"] == 0 and observed["upper_bound"] < TARGET)
        if opened:
            self.epoch += 1
            self.deadline = board.round + IDLE_ROUNDS
        return reason, opened

    def observe(self, round_id, authorization, taken_round, epoch, verdict, *, request):
        self.sequence += 1
        self.verifications.append(bound.Verification(request.id, request.scope, self.sequence, verdict == "violation"))
        if verdict == "violation":
            self.close(round_id)
        elif authorization == "standing" and self.deadline is not None and round_id < self.deadline and epoch == self.epoch:
            self.deadline = max(self.deadline, taken_round + IDLE_ROUNDS)


def compare():
    arms = {}
    with TemporaryDirectory(prefix="tremor-l6-bound-rehearsal-") as scratch:
        for name in ("sequential", "fixed", "time_box"):
            policy = SequentialPolicy() if name == "sequential" else None
            events, board = fixture._run(Path(scratch) / f"{name}.jsonl", name, policy=policy)
            arms[name] = {"events": events, "board_events": board, "metrics": fixture.account(events)}
            if policy is not None:
                arms[name]["end_of_window"] = policy.evidence()
                observed = {receipt.attempt_id for receipt in policy.verifications}
                pending = {execution.attempt_id for execution in policy.executions} - observed
                arms[name]["unresolved_ids"] = {"scripted_missing": sorted(pending & fixture.MISSING_OUTCOMES),
                                                "due_after_window": sorted(pending - fixture.MISSING_OUTCOMES)}
    sequential = arms["sequential"]["metrics"]
    comparisons = {}
    for name in ("fixed", "time_box"):
        baseline = arms[name]["metrics"]
        comparisons[name] = {
            "relative_unused_grant_reduction": fixture.relative_reduction(sequential["unused_grant_rounds"],
                                                                         baseline["unused_grant_rounds"]),
            "blocked_legitimate_difference": sequential["blocked_legitimate"] - baseline["blocked_legitimate"],
            "observed_violation_difference": sequential["executed_standin_violations"] -
                                             baseline["executed_standin_violations"],
        }
    return {"scientific_result": False, "fixture_settings": {"alpha": ALPHA, "opening_target": TARGET,
                                                            "sequential_idle_rounds": IDLE_ROUNDS},
            "arms": arms, "comparisons": comparisons}


if __name__ == "__main__":
    print(json.dumps(compare(), sort_keys=True, indent=2, allow_nan=False))
