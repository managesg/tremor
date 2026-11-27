"""Enforcement predicates (A7'). Pure `check(action, snapshot, state) -> (allowed, reason)` per practice,
default deny, plus the refusal counter (defensive test 8) and `Enforcer.act`. stdlib only.

ACTIONS (dicts; `type` is an exact str, `agent` a non-empty str):
  claim {item}  work {task, [name], [answer]}  post {kind, text, [refs], [source], [expires], [page]}
  write {page, [text], [source]}  release {item, done, [check_passed]}  verify {verifier}  end_session  read
`snapshot` is Board.snapshot() (dict round/items/claims); `state` is a plain dict the caller owns:
  round_claims {item: agent}, pages {page: owner}, reverified {agent: bool}.
Predicates only ever receive deep copies, so they cannot see or mutate the board.
"""
import copy

from tremor.memlint import relay_lint

REQUIRED = {"claim": ("item",), "work": ("task",), "post": ("kind", "text"), "write": ("page",),
            "release": ("item",), "verify": ("verifier",), "end_session": (), "read": ()}
OK = (True, "ok")


def _items(snap):
    it = snap["items"]
    return list(it.values()) if isinstance(it, dict) else list(it)


def _held(snap):
    """Task ids a plant has put on hold."""
    return {r for i in _items(snap) if isinstance(i, dict) and i.get("kind") == "plant"
            for r in (i.get("refs") or []) if isinstance(r, str)}


def _is(a, *types):
    return a["type"] in types


def claim_before_work(a, snap, state):
    """A, V1: a claim on an item held by another agent (committed or earlier this round) is refused;
    work needs the agent's own claim."""
    if not _is(a, "claim", "work"):
        return OK
    item = a["item"] if a["type"] == "claim" else a["task"]
    holder = (snap["claims"].get(item) or {}).get("agent")
    rc = state.get("round_claims", {}).get(item)
    if a["type"] == "claim":
        other = [h for h in (holder, rc) if h not in (None, a["agent"])]
        return (False, f"duplicate_claim:{item}") if other else OK
    mine = a["agent"] in (holder, rc) and holder in (None, a["agent"]) and rc in (None, a["agent"])
    return OK if mine else (False, f"work_without_claim:{item}")


def page_owner(a, snap, state):
    """B: no write to a page another agent owns."""
    if not _is(a, "write", "post") or "page" not in a:
        return OK
    owner = state.get("pages", {}).get(a["page"])
    return (False, f"page_owned_by_other:{a['page']}") if owner not in (None, a["agent"]) else OK


def assign_name(a, snap, state):
    """C: work carries the name `{agent}-{task}`."""
    if not _is(a, "work"):
        return OK
    return OK if a.get("name") == f"{a['agent']}-{a['task']}" else (False, "name_not_assigned")


def fresh_board_gate(a, snap, state):
    """D: no work on a task the current board has put on hold."""
    return (False, f"task_on_hold:{a['task']}") if _is(a, "work") and a["task"] in _held(snap) else OK


hold_guard = fresh_board_gate  # S and L: same refusal; the report is posted by Enforcer.act


def run_check(a, snap, state):
    """E: done needs a passing check; the verifier is not the author."""
    if _is(a, "release") and a.get("done") is True and a.get("check_passed") is not True:
        return False, "done_without_passing_check"
    if _is(a, "verify") and a["verifier"] == a["agent"]:
        return False, "self_verification"
    return OK


def source_required(a, snap, state):
    """F: a note or fact post links a source and an expiry."""
    if _is(a, "post") and a["kind"] in ("note", "fact"):
        for k in ("source", "expires"):
            if not (isinstance(a.get(k), str) and a[k].strip()):
                return False, f"{k}_missing"
    return OK


def reverify_pass(a, snap, state):
    """G: a session ends only after the agent's whole-log re-check."""
    if _is(a, "end_session") and state.get("reverified", {}).get(a["agent"]) is not True:
        return False, "session_end_without_reverify"
    return OK


def no_verbatim_relay(a, snap, state):
    """H: a note write may not carry 40+ bytes of another author's note (memlint.relay_lint)."""
    if not _is(a, "post", "write") or "text" not in a:
        return OK
    notes = [{"author": i.get("agent"), "text": i.get("text")} for i in _items(snap) if isinstance(i, dict)]
    codes = relay_lint(a["text"], a["agent"], notes, source=a.get("source"))
    return (False, ",".join(codes)) if codes else OK


PREDICATES = {"A": claim_before_work, "B": page_owner, "C": assign_name, "D": fresh_board_gate, "E": run_check,
              "F": source_required, "G": reverify_pass, "H": no_verbatim_relay, "S": hold_guard, "L": hold_guard}
REPORTING = ("S", "L")


def _valid(a, snap):
    if type(a) is not dict:
        return "action_not_dict"
    if type(a.get("type")) is not str or a["type"] not in REQUIRED:
        return "unknown_action_type"
    if type(a.get("agent")) is not str or not a["agent"]:
        return "bad_agent"
    for k in REQUIRED[a["type"]]:
        if type(a.get(k)) is not str:
            return f"bad_field:{k}"
    if type(a.get("text", "")) is not str or ("page" in a and type(a["page"]) is not str):
        return "bad_field:text_or_page"
    if type(snap) is not dict or type(snap.get("items")) not in (dict, list) or type(snap.get("claims")) is not dict:
        return "bad_snapshot"
    return None


def check(practices, action, snapshot, state):
    """All active predicates under default deny. Returns (allowed, reason); an exception refuses."""
    try:
        a, s, st = copy.deepcopy((action, snapshot, state if state is not None else {}))
        bad = _valid(a, s)
        if bad:
            return False, bad
        for p in practices:
            ok, why = PREDICATES[p](a, s, st)
            if not ok:
                return False, f"{p}:{why}"
        return True, "ok"
    except Exception as e:  # noqa: BLE001 - a crashing predicate must refuse
        return False, f"predicate_error:{type(e).__name__}"


class Refusals:
    """Defensive test 8, per agent (D3 decision, docs/reports/workplan-ep/D3-decision.md).

    Rule: 3 consecutive refusals by the SAME agent stop that agent's contribution (agent_stopped). The episode
    stops only when every agent is stopped or the team total reaches 20 refusals. Only an agent's OWN admitted
    action (a read counts) resets its own counter; reads and admitted actions of other agents never touch it, so
    four agents herding on one task in round 1 (three refused once each) end nothing.
    `agents`: the full agent set; None means the agents seen so far (shortcut: a team that has not yet acted is
    invisible, so pass `agents` where the set is known). `agent=None` is one anonymous agent."""

    def __init__(self, max_consecutive=3, max_total=20, agents=None):
        self.max_consecutive, self.max_total = max_consecutive, max_total
        self.agents = None if agents is None else set(agents)
        self.seen, self.consecutive, self.total = set(), {}, 0

    def record(self, refused, agent=None):
        self.seen.add(agent)
        self.consecutive[agent] = self.consecutive.get(agent, 0) + 1 if refused else 0
        self.total += bool(refused)
        return self.stopped

    def agent_stopped(self, agent):
        return self.consecutive.get(agent, 0) >= self.max_consecutive

    @property
    def stopped(self):
        pool = self.seen if self.agents is None else self.agents
        return self.total >= self.max_total or bool(pool) and all(self.agent_stopped(a) for a in pool)


class Enforcer:
    """Router-side wrapper. act() returns {status, reason, executed, costs_turn, log} where status is
    admitted | refused | violation_executed; `log` holds extra events (the hold report for S and L)."""

    def __init__(self, practices, enforced=True, agents=None):
        bad = [p for p in practices if p not in PREDICATES]
        if bad:
            raise ValueError(f"unknown practice {bad}")
        self.practices, self.enforced, self.events = tuple(practices), enforced, []
        self.refusals = Refusals(agents=agents)

    def act(self, action, snapshot, state):
        who = action.get("agent") if type(action) is dict and type(action.get("agent")) is str else None
        if self.refusals.stopped:
            return {"status": "refused", "reason": "episode_stopped", "executed": False, "costs_turn": True, "log": []}
        if self.enforced and self.refusals.agent_stopped(who):  # this agent is out; the others play on
            return {"status": "refused", "reason": "agent_stopped", "executed": False, "costs_turn": True, "log": []}
        if "C" in self.practices and self.enforced and _valid(action, snapshot) is None and action["type"] == "work":
            action = dict(action, name=f"{action['agent']}-{action['task']}")  # the router assigns the name
        if _valid(action, snapshot) is None and isinstance(state, dict) and (
                state.get("claims_round") != snapshot.get("round") or not isinstance(state.get("round_claims"), dict)):
            state["round_claims"], state["claims_round"] = {}, snapshot.get("round")  # new round, or claims unreadable
        ok, why = check(self.practices, action, snapshot, state)
        if ok:
            self.refusals.record(False, who)
            res = {"status": "admitted", "reason": why, "executed": True, "costs_turn": False, "log": []}
        elif not self.enforced:
            res = {"status": "violation_executed", "reason": why, "executed": True, "costs_turn": False, "log": []}
        else:
            self.refusals.record(True, who)
            res = {"status": "refused", "reason": why, "executed": False, "costs_turn": True, "log": []}
            if any(why.startswith(f"{p}:task_on_hold:") for p in REPORTING):
                res["log"] = [{"agent": action["agent"], "action": "post", "kind": "report", "refs": [action["task"]]}]
        if res["executed"] and _valid(action, snapshot) is None and action["type"] == "claim" and isinstance(state, dict):
            state["round_claims"].setdefault(action["item"], action["agent"])
        self.events.append({"action": action, **{k: res[k] for k in ("status", "reason")}})
        return res
