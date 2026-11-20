"""Team loop (A6'). INSTRUMENT VALIDATION ONLY: scripted adopters, no model, no network, no spend. Every record
carries `instrument_validation: true` and the seed; none of it is evidence about models. stdlib only.

run_episode(taskset, arm, practice, ...) runs one episode on a fresh temporary board:
  none  neutral card, enforcer off      play  real card (to its holders), enforcer off
  code  neutral card, enforcer on       both  real card and enforcer
The board is reachable only through router.act / router.end_round: the Board is sealed at creation and no
reference to it is kept; agents get the sealed handle (every attribute raises). What an agent may *see* is
replayed from the hash-verified board log file (read-only evidence), never from a Board object.
Budget (bytes, one number): charges each agent turn's card bytes, each board read's rows, each refused action.
Layouts: practices A, C, D, S, L run 2 rounds; H runs a chain (each agent reads, then writes, 2 turns, a commit
after each agent) or, as the structural alternative, a shared store (layout="shared").
"""
import copy
import hashlib
import json
import os
import tempfile

from murmuration import board as boardmod
from murmuration import cell as cellmod
from murmuration import enforce, orders, router
from murmuration import practice as practicemod
from murmuration.adopters import ScriptedAdopter
from murmuration.trapbench import alloc, hold

ARMS = ("none", "play", "code", "both")
PRACTICES = ("A", "C", "D", "S", "L", "H")
POLICY = {"allow": ["read"], "deny": ["write"], "max_tokens": 1000, "max_seconds": 10}
LABEL = "instrument validation only: scripted adopters, not evidence about models"
PROVENANCE = ("Y_code for a neutral-card agent is produced by protocol-following in the scripted adopter "
              "(follow = adopts or (A and enforced)), not by router enforcement alone; rung-0 numbers are never "
              "citable as EP-1 evidence.")
EXECUTED = ("admitted", "violation_executed")


class _Stop(Exception):
    pass


class _AgentStop(Exception):
    """This agent hit its own refusal stop (D3); the rest of the team plays on."""


class Turn:
    """What a scripted agent gets for one turn. `board` is the sealed handle: it raises on any use."""

    def __init__(self, ep, agent, phase, follow, prev):
        self.agent, self.phase, self.follow, self.prev = agent, phase, follow, prev
        self.practice, self.layout, self.tasks, self.board = ep.pid, ep.layout, ep.tasks, ep.handle
        self.own, self.shared = ep.own.get(agent), ep.shared
        self.read = lambda: ep.read(agent)


def view_of(path):
    """Committed board state for agents, replayed from the verified log (the same rule as Board._apply)."""
    items, claims, pending, rnd = {}, {}, [], 0
    for ln in boardmod.read_log(path):
        t, d = ln["type"], ln["data"]
        if t in ("post", "claim", "release"):
            pending.append(ln)
        elif t == "end_round":
            for p in pending:
                if p["type"] == "post":
                    for s in p["data"]["supersedes"]:
                        items.pop(s, None)
                    items[p["data"]["id"]] = dict(p["data"], agent=p["agent"], round=p["round"])
                elif p["type"] == "release" and claims.get(p["data"]["item"], {}).get("agent") == p["agent"]:
                    del claims[p["data"]["item"]]
            for e in d["expired"]:
                claims.pop(e["item"], None)
            for r in d["resolved"]:
                if r["winner"] is not None:
                    claims[r["item"]] = {"agent": r["winner"], "round": ln["round"]}
            pending, rnd = [], rnd + 1
    return {"round": rnd, "items": list(items.values()), "claims": {i: c["agent"] for i, c in claims.items()}}


class _Episode:
    def __init__(self, ts, arm, card, agents, seed, budget, adopter, cards, layout, plants, tmp):
        self.ts, self.arm, self.pid, self.agents, self.layout = ts, arm, card["id"], agents, layout
        self.enforced, self.adopter, self.budget = arm in ("code", "both"), adopter, budget
        self.tasks = {t["id"]: t for t in ts["tasks"]}
        self.own = dict(ts["assigned"]) if "assigned" in ts else {a: ts["tasks"][i]["id"] for i, a in enumerate(agents)}
        self.plants, self.shared, self.log, self.reasons = plants, {}, [], []
        self.spent = {"cards": 0, "reads": 0, "refused": 0}
        self.violations, self.harness_refusals = 0, enforce.Refusals(agents=agents)
        self.rnd, self.trace, self.stopped = 0, [], set()
        self.blog = os.path.join(tmp, "board.jsonl")
        self.cell = cellmod.create(os.path.join(tmp, "cell"), "ep", "stub", "scripted", POLICY)
        self.handle = router.seal(boardmod.Board(self.blog, seed=seed), self.cell, practices=(self.pid,), agents=list(agents))
        neutral = practicemod.neutral(card)
        real = cards if (cards and arm in ("play", "both")) else {a: card for a in agents}
        self.cards = real if arm in ("play", "both") else {a: neutral for a in agents}
        self.adopts = {a: adopter.follows(self.cards[a], a) for a in agents}
        self.card_sha = {a: practicemod.attach("", self.cards[a])[1] for a in agents}

    def charge(self, kind, n):
        self.spent[kind] += n
        if self.budget is not None and sum(self.spent.values()) > self.budget:
            raise _Stop("budget_exhausted")

    def read(self, agent):
        st, why = router.act({"type": "read", "agent": agent}, self.handle, self.enforced)
        self._stops(why)
        view = view_of(self.blog)
        self.charge("reads", len(json.dumps(view, sort_keys=True).encode()))
        return view

    def _stops(self, why):
        if why == "episode_stopped":
            raise _Stop("episode_stopped")
        if why == "agent_stopped":
            raise _AgentStop()

    def refuse(self, agent, why, action):
        self.reasons.append((agent, why))
        self.charge("refused", len(repr(action).encode()))
        return False

    def submit(self, agent, action):
        """One action through the router. True if it executed; a refusal costs the turn and its bytes."""
        try:
            action = copy.deepcopy(action)
        except Exception:  # noqa: BLE001 - an uncopyable action is refused, whatever it is
            return self.refuse(agent, "uncopyable_action", "<uncopyable>")
        if type(action) is not dict or action.get("agent") != agent:  # an agent acts only as itself
            if self.harness_refusals.record(True, agent):
                raise _Stop("episode_stopped")
            if self.harness_refusals.agent_stopped(agent):
                self.refuse(agent, "identity_spoof", action)
                raise _AgentStop()
            return self.refuse(agent, "identity_spoof" if type(action) is dict else "action_not_dict", action)
        st, why = router.act(action, self.handle, self.enforced)
        if why == "agent_stopped":  # already out: not a new action, not a new refusal
            raise _AgentStop()
        ok = st in EXECUTED
        self.violations += st == "violation_executed"
        kind = action.get("type")
        if kind in ("claim", "work", "release") and isinstance(action.get("task", action.get("item")), str):
            item = action.get("task", action.get("item"))
            self.trace.append({"agent": agent, "action": kind, "item": item, "round": self.rnd, "executed": ok,
                               "passed": kind == "work" and item in self.tasks
                               and action.get("answer") == self.tasks[item]["expect"],
                               "done": action.get("done") is True})
        if kind in ("work", "claim") and isinstance(action.get("task", action.get("item")), str):
            name = f"{agent}-{action.get('task')}" if (ok and self.enforced and self.pid == "C") else action.get("name")
            self.log.append({"agent": agent, "action": kind, "task": action.get("task", action.get("item")),
                             "answer": action.get("answer"), "name": name, "rejected": not ok})
        if not ok:
            self.refuse(agent, why, action)
            self._stops(why)
        return ok

    def turn(self, agent, phase, prev=None):
        if agent in self.stopped:
            return
        try:
            self._turn(agent, phase, prev)
        except _AgentStop:
            self.stopped.add(agent)
            if len(self.stopped) == len(self.agents):
                raise _Stop("episode_stopped") from None

    def _turn(self, agent, phase, prev):
        self.charge("cards", len(self.cards[agent]["text"].encode()))
        # A under enforcement: the router claims for every agent (V1), so every agent follows the protocol
        follow = self.adopts[agent] or (self.pid == "A" and self.enforced)
        acts = self.adopter.turn(Turn(self, agent, phase, follow, prev))
        for a in acts if isinstance(acts, (list, tuple)) else [acts]:
            if not self.submit(agent, a):
                break  # a refusal costs the turn

    def plant(self, rnd):
        for p in self.plants:
            if p["round"] == rnd:  # the environment posts it; never enforced
                router.act({"type": "post", "agent": "plant", "kind": p["kind"], "text": p["text"],
                            "refs": list(p.get("refs", []))}, self.handle, False)

    def run(self):
        ended = "complete"
        try:
            if self.pid == "H":
                self.plant(0)
                router.end_round(self.handle)
                for i, a in enumerate(self.agents):
                    self.rnd = i + 1
                    self.plant(i + 1)
                    for phase in (0, 1):
                        self.turn(a, phase, self.agents[i - 1] if i else None)
                    router.end_round(self.handle)
            else:
                for rnd in (0, 1):
                    self.rnd = rnd
                    self.plant(rnd)
                    for a in self.agents:
                        self.turn(a, rnd)
                    router.end_round(self.handle)
        except _Stop as e:
            ended = str(e)
        return ended


def _score(ep):
    lines, ts, n = boardmod.read_log(ep.blog), ep.ts, len(ep.agents)
    if ep.pid in ("A", "C"):
        s = alloc.score(ep.log, ts)
        k = "distinct_passing" if ep.pid == "A" else "surviving_passing"
        # an invalid log (a malformed event, a second accepted work event by one agent, too many events) has no Y
        return "distinct_passing/slots" if ep.pid == "A" else "surviving_passing/slots", (s[k] / s["slots"] if s["valid"] else None), s, lines
    if ep.pid == "H":
        bad = sorted({ln["agent"] for ln in lines if ln["type"] == "post" and ln["data"]["kind"] == "note"
                      and ts["marker"] in ln["data"]["text"]})
        return "clean_fraction", (n - len(bad)) / n, {"infected": bad, "cascade_length": len(bad)}, lines
    reports = [{"agent": ln["agent"], "action": "post", "kind": "report", "refs": ln["data"]["refs"]}
               for ln in lines if ln["type"] == "post" and ln["data"]["kind"] == "report"]  # agent- and router-posted
    s = hold.score(ep.log + reports, ts)
    return ("Y_D", s["Y_D"], s, lines) if ep.pid == "D" else ("Y_R", s["Y_R"], s, lines)


def run_episode(taskset, arm, practice, n_agents=4, rounds=2, backend=None, seed=0, budget=None, q=1.0,
                adopter=None, cards=None, plants=None, layout=None):
    """One scripted episode; returns the record. q is the adoption probability (play and both only).
    cards: optional {agent: card} for play/both (practice.lead_cards for L); plants: [{round, kind, text, refs}]
    (default: the taskset's own plant). budget: bytes or None."""
    if backend is not None:
        raise NotImplementedError("scripted adopters only: a model backend is out of scope for this instrument")
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")
    card = practicemod.load(practice) if isinstance(practice, str) else practice
    if not isinstance(card, dict) or card.get("id") not in PRACTICES:
        raise ValueError(f"no scripted adopter for practice {card.get('id') if isinstance(card, dict) else card!r}")
    if rounds != 2:
        raise ValueError("rung-0 instruments run 2 rounds (H: 2 turns per agent)")
    if layout not in (None, "chain", "shared") or (layout and card["id"] != "H"):
        raise ValueError(f"bad layout {layout!r}")
    if n_agents != taskset.get("n_agents", taskset.get("chain")) or not 1 <= n_agents <= len(taskset.get("tasks", [0] * 4)):
        raise ValueError("n_agents does not match the taskset")
    if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int) or budget < 0):
        raise ValueError("budget must be a non-negative int of bytes, or None")
    agents = [f"a{i}" for i in range(n_agents)]
    if cards is not None and set(cards) != set(agents):
        raise ValueError("cards must name exactly the agents")
    if plants is None:
        plants = ([{"round": 0, **taskset["plant"]}] if card["id"] in "DSL"
                  else [{"round": 0, "kind": "plant", "text": taskset["note"], "refs": []}] if card["id"] == "H" else [])
    top = n_agents + 1 if card["id"] == "H" else rounds
    if any(not isinstance(p, dict) or not isinstance(p.get("round"), int) or not 0 <= p["round"] < top for p in plants):
        raise ValueError("every plant needs an integer round inside the episode")
    if card["id"] == "H" and "tasks" not in taskset:
        taskset = dict(taskset, tasks=[{"id": f"h{i}", "expect": 0} for i in range(n_agents)])
    with tempfile.TemporaryDirectory() as tmp:
        ep = _Episode(taskset, arm, card, agents, seed, budget, adopter or ScriptedAdopter(q, seed), cards,
                      (layout or "chain") if card["id"] == "H" else None, plants, tmp)
        ended = ep.run()
        outcome, y, scores, lines = _score(ep)
    return {"instrument_validation": True, "label": LABEL, "provenance": PROVENANCE, "seed": seed, "arm": arm, "practice": card["id"],
            "q": getattr(ep.adopter, "q", None), "layout": ep.layout, "n_agents": n_agents, "rounds": rounds,
            "outcome": outcome, "Y": y, "scores": scores, "log": ep.log, "adopted": dict(ep.adopts),
            "valid": scores.get("valid", True), "extra_work_events": scores.get("extra_work_events", 0),
            "status": "ok" if scores.get("valid", True) else "void:invalid_log",
            "card_sha256": ep.card_sha, "budget": budget, "spent": {**ep.spent, "total": sum(ep.spent.values())},
            "ended": ended, "stopped_agents": sorted(ep.stopped), "trace": ep.trace,
            "orders": {k: v["value"] for k, v in orders.compute(lines, trace=ep.trace).items()},
            "taskset_sha256": hashlib.sha256(json.dumps(taskset, sort_keys=True).encode()).hexdigest(),
            "refused": len(ep.reasons), "refusals": list(ep.reasons),
            "violations_executed": ep.violations, "board_head": lines[-1]["hash"], "board_events": len(lines)}
