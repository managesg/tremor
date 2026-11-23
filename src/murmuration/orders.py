"""Order parameters computed from the board log (schema: board.py docstring) and, for the two read-offs the
board log cannot hold, an optional ordered action `trace` (see trace_false_done).

compute(log, f, trace=None) returns {name: {"value": number|None, "unit": str}}.
None means undefined (no data or a zero denominator); never 0 or inf.
`log` is a path (hash chain verified) or a list of event dicts.
claim_collision_rate is EXECUTED collisions (board log); claim_collision_attempted_rate counts refused attempts
too; report them side by side. false_done_rate is None unless a trace (or board work events) can back it.
"""
import math
import os
import re
from collections import Counter

from murmuration.board import read_log


def _entropy(counts):
    n = sum(counts)
    return -sum(c / n * math.log(c / n) for c in counts if c)


def _false_done(ev, done):
    """Board-log-only path: done releases with no earlier passing work event by the same agent on the same item,
    or None when the log holds no work event at all (the router never logs work, so the rate is not measurable
    from a router board log: pass `trace` to compute instead).
    Work event: {"type": "work", "agent", "data": {"item", "passed": bool}}."""
    if not any(e["type"] == "work" for e in ev):
        return None
    backed, bad, ids = set(), 0, {id(x) for x in done}
    for e in ev:
        d = e.get("data") or {}
        if e["type"] == "work" and d.get("passed"):
            backed.add((e.get("agent"), d.get("item")))
        elif id(e) in ids and (e.get("agent"), d.get("item")) not in backed:
            bad += 1
    return bad / len(done) if done else None


def trace_false_done(trace):
    """done releases with no passing work event by the same agent for the same item / done releases. Walks the
    ordered action trace once: an EXECUTED work event with passed true backs every later executed done release
    by that agent for that item (same round included, as long as the work was logged first). None if no done
    release. Trace entry: {"action": "claim"|"work"|"release", "agent", "item", "round", "executed": bool,
    "passed": bool (work), "done": bool (release)}."""
    backed, bad, n = set(), 0, 0
    for t in trace:
        if not t.get("executed"):
            continue
        if t["action"] == "work" and t.get("passed") is True:
            backed.add((t["agent"], t["item"]))
        elif t["action"] == "release" and t.get("done") is True:
            n += 1
            bad += (t["agent"], t["item"]) not in backed
    return bad / n if n else None


def trace_claim_collisions(trace):
    """(colliding items, claim attempts) over ALL claim attempts, executed or refused. An item collides in a
    round when two or more distinct agents attempted it in that round (the board's own definition, applied to
    attempts). Under enforcement the refused duplicates never reach the board log, so the board-log rate is 0
    by construction; this is the arm-comparable one."""
    by, n = {}, 0
    for t in trace:
        if t["action"] == "claim":
            n += 1
            by.setdefault((t["round"], t["item"]), set()).add(t["agent"])
    return sum(len(a) >= 2 for a in by.values()), n


def _marker_spread(ev, agents):
    """Share of the other agents with a post holding the marker of the first kind "marker" post."""
    m = next((e for e in ev if e["type"] == "post" and e["data"].get("kind") == "marker"), None)
    tok = re.search(r"MARK-[A-Za-z0-9_-]+", m["data"].get("text", "")) if m else None
    others = [a for a in agents if m and a != m["agent"]]
    if not tok or not others:
        return None
    hit = {e["agent"] for e in ev if e["type"] == "post" and e is not m and tok.group() in e["data"].get("text", "")}
    return len(hit & set(others)) / len(others)


def compute(log, f=0.75, trace=None):
    if isinstance(log, (str, os.PathLike)):
        if not os.path.exists(log):  # read_log loads a missing file as empty; a missing log is an error here
            raise FileNotFoundError(log)
        ev = read_log(os.fspath(log))
    else:
        ev = list(log)
    agents = sorted({e["agent"] for e in ev if e.get("agent") is not None})
    n_agents = len(agents)

    done = [e for e in ev if e["type"] == "release" and e["data"].get("done")]
    per_agent = Counter(e["agent"] for e in done)
    entropy = _entropy([per_agent[a] for a in agents]) / math.log(n_agents) if done and n_agents > 1 else None

    types = {e["data"]["task_type"] for e in done if e["data"].get("task_type") is not None}
    spec = None
    if len(types) > 1:
        by = {}
        for e in done:
            if e["data"].get("task_type") is not None:
                by.setdefault(e["agent"], Counter())[e["data"]["task_type"]] += 1
        spec = sum(1 - _entropy(list(c.values())) / math.log(len(types)) for c in by.values()) / len(by)

    reads = sum(e["type"] == "read" for e in ev)
    writes = sum(e["type"] == "post" for e in ev)
    claims = sum(e["type"] == "claim" for e in ev)
    ends = [e for e in ev if e["type"] == "end_round"]
    collisions = sum(r["collision"] for e in ends for r in e["data"]["resolved"])

    # replay committed posts at each end_round: positions, live items, facts
    pending, live, planted, depth, pos, converged, cascade = [], {}, set(), {}, {}, None, None
    for e in ev:
        if e["type"] == "post":
            pending.append(e)
        elif e["type"] == "end_round":
            for p in pending:
                d = p["data"]
                for s in d.get("supersedes", ()):
                    live.pop(s, None)
                live[d["id"]] = d
                if d.get("kind") == "plant":
                    planted.update(d.get("facts", ()))
                for fact in d.get("facts", ()):
                    up = [depth[(r, fact)] for r in d.get("refs", ()) if (r, fact) in depth]
                    depth[(d["id"], fact)] = max(up) + 1 if up else 0
                    cascade = max(cascade or 0, depth[(d["id"], fact)])
                if d.get("position") is not None:
                    pos[p["agent"]] = d["position"]
            pending = []
            if converged is None and pos and n_agents and max(Counter(pos.values()).values()) / n_agents >= f:
                converged = e["round"] + 1

    kept = {fact for d in live.values() for fact in d.get("facts", ())} & planted
    reporters = {e["agent"] for e in ev if e["type"] == "post" and e["data"].get("kind") == "report"}
    if trace is None:
        att, fd = None, _false_done(ev, done)
    else:
        (hits, tried), fd = trace_claim_collisions(trace), trace_false_done(trace)
        att = hits / tried if tried else None
    return {
        "work_distribution_entropy": {"value": entropy, "unit": "fraction of log N (0 monopoly, 1 equal)"},
        "read_write_ratio": {"value": reads / writes if writes else None, "unit": "reads per post"},
        "claim_collision_rate": {"value": collisions / claims if claims else None,
                                 "unit": "EXECUTED colliding items per executed claim (board log; 0 under enforcement)"},
        "claim_collision_attempted_rate": {"value": att, "unit": "colliding items per claim attempt, refused included (needs trace)"},
        "convergence_time": {"value": converged, "unit": "rounds until fraction f agree"},
        "specialisation_index": {"value": spec, "unit": "0 to 1"},
        "cascade_length": {"value": cascade, "unit": "hops of the longest relay chain of one fact"},
        "fact_retention_rate": {"value": len(kept) / len(planted) if planted else None, "unit": "kept / planted facts"},
        "memory_sprawl": {"value": sum(len(d["text"]) for d in live.values()) if live else None,
                          "unit": "characters in live items", "items": len(live)},
        "false_done_rate": {"value": fd, "unit": "done releases with no passing work event / done releases"},
        "report_reach": {"value": len(reporters) / n_agents if n_agents else None, "unit": "agents who posted a report / agents"},
        "marker_spread": {"value": _marker_spread(ev, agents), "unit": "other agents whose notes hold the marker / other agents"},
    }
