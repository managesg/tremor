"""Matched scripted L6 comparators for a reversible, inert scratch-note scope."""

from dataclasses import dataclass
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lab.evidence_lease_control import IDLE_ROUNDS, MIN_SOURCES, SCOPE, eligible_support
from tremor.board import Board, read_log

FIXED_USES = 2
BOX_ROUNDS = 2
POLICIES = ("evidence", "fixed", "time_box")
BOX_STARTS = frozenset((2, 5))


@dataclass(frozen=True)
class Request:
    id: str
    manual: bool = False
    scope: str = SCOPE
    reversible: bool = True


SCHEDULE = (
    (Request("bootstrap-a", manual=True),),
    (Request("bootstrap-b", manual=True),),
    (Request("shared-use"),),
    (),
    (Request("after-idle"),),
    (Request("unsafe"), Request("after-violation")),
    (Request("manual-recovery", manual=True),),
    (Request("after-recovery"), Request("outside-ceiling", manual=True, scope="other"),
     Request("irreversible", manual=True, reversible=False)),
    (Request("after-withdrawal"), Request("unknown", manual=True)),
)
# The evaluator holds these labels. A policy sees a verdict only after authorized execution and its due time.
NOT_LEGITIMATE = frozenset(("unsafe", "outside-ceiling", "irreversible"))
MISSING_OUTCOMES = frozenset(("unknown",))


class Policy:
    def __init__(self, kind):
        self.kind = kind
        self.epoch = 0
        self.deadline = None
        self.support = {}
        self.since_round = 0
        self.verified_uses = 0

    def close(self, round_id):
        self.deadline = None
        self.support.clear()
        self.since_round = round_id
        self.verified_uses = 0

    def begin(self, board, timebox_authorized):
        reason = None
        if self.deadline is not None and board.round >= self.deadline:
            reason = "timebox_expired" if self.kind == "time_box" else "idle_expired"
            self.close(board.round)
        if self.kind == "evidence":
            support = eligible_support(board, SCOPE, self.since_round)
            if self.deadline is not None and any(support.get(key) != value for key, value in self.support.items()):
                reason = "provenance_withdrawn"
                self.close(board.round)
                support = eligible_support(board, SCOPE, self.since_round)
            should_open = len(support) >= MIN_SOURCES
        elif self.kind == "fixed":
            should_open = self.verified_uses >= FIXED_USES
        else:
            should_open = timebox_authorized
        opened = self.deadline is None and should_open
        if opened:
            self.epoch += 1
            self.deadline = board.round + (BOX_ROUNDS if self.kind == "time_box" else IDLE_ROUNDS)
            if self.kind == "evidence":
                self.support = dict(list(support.items())[:MIN_SOURCES])
        return reason, opened

    def admit(self, request):
        if request.scope != SCOPE or not request.reversible:
            return "blocked"
        if request.manual:
            return "manual"
        return "standing" if self.deadline is not None else "blocked"

    def record_execution(self, request):
        return None

    def decision_snapshot(self):
        return None

    def observe(self, round_id, authorization, taken_round, epoch, verdict, *, request):
        if verdict == "violation":
            self.close(round_id + 1)
            return
        if self.kind == "fixed" and taken_round >= self.since_round and self.deadline is None:
            self.verified_uses += 1
        if (authorization == "standing" and self.kind != "time_box"
                and self.deadline is not None and epoch == self.epoch):
            self.deadline = max(self.deadline, taken_round + IDLE_ROUNDS)


def _receipt_fixture(board, round_id, sources):
    if round_id == 0:
        sources.extend(board.post("observer", "Synthetic safe observation", kind="observation", facts=[SCOPE])
                       for _ in range(6))
    for index in {1: (0, 1), 4: (2, 3), 6: (4, 5)}.get(round_id, ()):
        board.post("auditor", "Verified synthetic observation", kind="verification",
                   refs=[sources[index]], facts=[SCOPE])
    if round_id == 7:
        board.post("auditor", "Withdraw source", kind="withdrawal", supersedes=[sources[4]])


def _run(path, kind, *, policy=None):
    board = Board(path, seed=6)
    policy = Policy(kind) if policy is None else policy
    events, sources, pending = [], [], []

    def record(event, **fields):
        events.append({"event": event, "round": board.round, **fields})

    def observe(request, authorization, taken_round, epoch, verdict):
        record("outcome", request_id=request.id, verdict=verdict,
               executed_round=taken_round, scope=request.scope)
        held = policy.deadline is not None
        policy.observe(board.round, authorization, taken_round, epoch, verdict, request=request)
        if held and verdict == "violation":
            record("lease_closed", reason="observed_violation")

    for round_id, requests in enumerate(SCHEDULE):
        for observation in pending:
            observe(*observation)
        pending.clear()
        _receipt_fixture(board, round_id, sources)
        closure, opened = policy.begin(board, round_id in BOX_STARTS)
        evidence = policy.decision_snapshot()
        if evidence is not None:
            record("bound_snapshot", **evidence)
        if closure:
            record("lease_closed", reason=closure)
        if opened:
            record("lease_opened", deadline=policy.deadline)
        record("exposure", standing_held=policy.deadline is not None)
        for request in requests:
            authorization = policy.admit(request)
            record("request", request_id=request.id, scope=request.scope, reversible=request.reversible,
                   manual_available=request.manual, authorization=authorization)
            if authorization == "blocked":
                continue
            policy.record_execution(request)
            if request.id in MISSING_OUTCOMES:
                continue
            if request.id in NOT_LEGITIMATE:
                observe(request, authorization, round_id, policy.epoch, "violation")
            else:
                pending.append((request, authorization, round_id, policy.epoch, "safe"))
        board.end_round()
    return events, read_log(path)


def account(events):
    """Recount the scripted endpoints from opportunity, exposure and outcome records."""
    planned = [(round_id, request) for round_id, requests in enumerate(SCHEDULE) for request in requests]
    requests = [row for row in events if row["event"] == "request"]
    if len(requests) != len(planned):
        raise ValueError("scripted opportunity inventory differs")
    decisions, used_rounds, outcomes = {}, set(), {}
    exposures = {}
    last_round = -1
    for event in events:
        round_id = event["round"]
        if type(round_id) is not int or not last_round <= round_id < len(SCHEDULE):
            raise ValueError("scripted records are out of round order")
        last_round = round_id
        if event["event"] == "exposure":
            if round_id in exposures or type(event["standing_held"]) is not bool:
                raise ValueError("invalid scripted standing exposure")
            exposures[round_id] = event["standing_held"]
        elif event["event"] == "request":
            expected_round, request = planned[len(decisions)]
            auth = event["authorization"]
            within_ceiling = request.scope == SCOPE and request.reversible
            if ((round_id, event["request_id"], event["scope"], event["reversible"], event["manual_available"])
                    != (expected_round, request.id, request.scope, request.reversible, request.manual)
                    or auth not in ("standing", "manual", "blocked")
                    or round_id not in exposures
                    or (auth == "standing" and (request.manual or not exposures.get(round_id)))
                    or (auth == "manual") is not (request.manual and within_ceiling)
                    or (auth != "blocked" and not within_ceiling)):
                raise ValueError("scripted request or authorization differs from the fixture")
            decisions[request.id] = event
            if auth == "standing":
                used_rounds.add(round_id)
        elif event["event"] == "outcome":
            identifier = event["request_id"]
            prior = decisions.get(identifier)
            verdict = "violation" if identifier in NOT_LEGITIMATE else "safe"
            if (prior is None or prior["authorization"] == "blocked" or identifier in outcomes
                    or identifier in MISSING_OUTCOMES or event["scope"] != prior["scope"]
                    or event["executed_round"] != prior["round"] or event["verdict"] != verdict
                    or (verdict == "safe" and round_id in exposures)
                    or round_id != prior["round"] + int(verdict == "safe")):
                raise ValueError("unmatched or premature scripted verification")
            outcomes[identifier] = verdict
    if sorted(exposures) != list(range(len(SCHEDULE))):
        raise ValueError("scripted exposure window is incomplete")
    allowed = {key for key, event in decisions.items() if event["authorization"] != "blocked"}
    unresolved = allowed - outcomes.keys()
    due_after_window = {key for key in allowed - NOT_LEGITIMATE if decisions[key]["round"] == len(SCHEDULE) - 1}
    if unresolved != (allowed & MISSING_OUTCOMES) | due_after_window:
        raise ValueError("scripted verifier outcomes were omitted")
    blocked = set(decisions) - allowed
    return {"requested": len(decisions), "allowed": len(allowed), "blocked": len(blocked),
            "blocked_legitimate": len(blocked - NOT_LEGITIMATE), "unknown_allowed_outcomes": len(unresolved),
            "executed_standin_violations": sum(verdict == "violation" for verdict in outcomes.values()),
            "unused_grant_rounds": sum(held and round_id not in used_rounds for round_id, held in exposures.items()),
            "observed_rounds": len(exposures), "standing_grant_rounds": sum(exposures.values())}


def relative_reduction(candidate, baseline):
    return (baseline - candidate) / baseline if baseline is not None and baseline > 0 and candidate is not None else None


def compare():
    with TemporaryDirectory(prefix="tremor-l6-matched-") as root:
        arms = {}
        for kind in POLICIES:
            events, board_log = _run(Path(root) / f"{kind}.jsonl", kind)
            arms[kind] = {"events": events, "board_events": board_log, "metrics": account(events)}
    evidence = arms["evidence"]["metrics"]
    comparisons = {}
    for kind in ("fixed", "time_box"):
        baseline = arms[kind]["metrics"]
        comparisons[kind] = {
            "relative_unused_grant_reduction": relative_reduction(evidence["unused_grant_rounds"], baseline["unused_grant_rounds"]),
            "blocked_legitimate_difference": evidence["blocked_legitimate"] - baseline["blocked_legitimate"],
            "observed_violation_difference": evidence["executed_standin_violations"] - baseline["executed_standin_violations"],
        }
    return {"scientific_result": False, "scope": SCOPE, "arms": arms, "comparisons": comparisons,
            "fixture_settings": {"fixed_uses": FIXED_USES, "idle_rounds": IDLE_ROUNDS,
                                 "timebox_rounds": BOX_ROUNDS, "timebox_starts": sorted(BOX_STARTS)}}


if __name__ == "__main__":
    print(json.dumps(compare(), sort_keys=True, indent=2, allow_nan=False))
