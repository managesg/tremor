"""Rung 0 driver (A9'). INSTRUMENT VALIDATION ONLY: scripted adopters, no model, no network, no spend. Nothing here
is evidence about models; every record carries `instrument_validation: true` and the driver refuses to run on a
record that lacks it. stdlib only.

run(practices, qs, sets, seed) runs team.run_episode for every practice, q, arm (none, play, code, both) over
`sets` generated task sets (one episode per arm per set, same seed across arms) and returns a table:
  cells   every outcome cell (mean over sets) per arm and q, None plus a reason where undefined, compared with
          the analytic expectation in docs/reports/workplan-ep/rung0-expected.md and -v2.md (exact for the
          deterministic cells, Z standard errors of the stated per-episode distribution otherwise)
  hdi     stats.hdi (cluster bootstrap over sets) per outcome and q, undefined cells reported with the reason
  checks  instrument checks: FLOOR (naive agents, no card) must fail and ORACLE (perfect agents) must pass on
          every task family, else the batch is VOID; probes for the mutations the table must catch
verdict is GREEN, RED (a check or cell failed) or VOID (a floor or oracle check failed).
"""
import math
import os
from fractions import Fraction as F

from murmuration import adopters, stats, team
from murmuration import practice as practicemod

Z = 4  # standard errors for sampled cells
EXACT = 1e-9
BOOT = 2000
TOP = ("A", "C", "D", "S", "L", "H", "H-shared")
LABEL = team.LABEL
PROVENANCE = team.PROVENANCE
COLL = ("claim_collision_attempted_rate", "claim_collision_executed_rate")  # refused attempts counted / board only
SD_ATT, SD_ATT_HALF = 0.11, 0.12  # per-episode sd of the collision rate (measured over 600 seeds, defined episodes)


# --- analytic expectations (docs/reports/workplan-ep/rung0-expected.md, rung0-expected-v2.md) ---------------------

def _sd(dist):
    m = sum(float(k) * float(p) for k, p in dist.items())
    return math.sqrt(sum(float(p) * (float(k) - m) ** 2 for k, p in dist.items()))


def _det(none, code, play, dist=None, hdi=None):
    """Deterministic none/code and play at q = 0 and 1; play at q = 1/2 follows `dist` (a per-episode distribution)."""
    sd = _sd(dist) if dist else 0
    cell = {"none": (none, 0), "code": (code, 0),
            "play": {0: (play[0], 0), 0.5: (play[1], sd), 1: (play[2], 0)}}
    if hdi is not None:
        k = sd / abs(float(code) - float(none)) if hdi[1] is not None and code != none else 0
        cell["hdi"] = {0: (hdi[0], 0), 0.5: (hdi[1], k), 1: (hdi[2], 0)}
    return cell


NOCLAIM = {"none": (None, 0), "code": (None, 0), "play": {q: (None, 0) for q in (0, 0.5, 1)}}
HOLD = {F(0): F(1, 4), F(1, 2): F(1, 2), F(1): F(1, 4)}
_PASS2 = {"none": (2, 0), "code": (2, 0), "play": {q: (2, 0) for q in (0, 0.5, 1)}}
_ONES = {"none": (1, 0), "code": (1, 0), "play": {q: (1, 0) for q in (0, 0.5, 1)}}
_CASC = {F(0): F(1, 2), F(1): F(1, 4), F(2): F(1, 8), F(3): F(1, 16), F(4): F(1, 16)}
_SHARED = {F(k, 4): F(math.comb(4, k), 16) for k in range(5)}

EXPECT = {
    "A": {
        "distinct/4": {"none": (F(671, 864), 0.17), "code": (F(85469, 86400), 0.06),
                       "play": {0: (F(671, 864), 0.17), 0.5: (F(1140569, 1382400), 0.17), 1: (F(85469, 86400), 0.06)},
                       "hdi": {0: (1, 0), 0.5: ("band", 0.35, 1.43), 1: (0, 0)}, "primary": True},
        # attempts include refused claims, so under enforcement the attempted rate equals the unenforced one
        "claim_collision_attempted_rate": {"none": (None, 0), "code": (F(142837, 907200), SD_ATT),
                                           "play": {0: (None, 0), 0.5: (F(847429, 13608000), SD_ATT_HALF),
                                                    1: (F(142837, 907200), SD_ATT)}},
        # executed collisions (board log) cannot exist under enforcement: exact 0, so a wrong 0 elsewhere fails
        "claim_collision_executed_rate": {"none": (None, 0), "code": (0, 0),
                                          "play": {0: (None, 0), 0.5: (F(847429, 13608000), SD_ATT_HALF),
                                                   1: (F(142837, 907200), SD_ATT)}},
        "dup_executed": {"code": (0, 0)},
    },
    "C": {
        "surviving/4": dict(_det(F(1, 4), 1, (F(1, 4), F(47, 64), 1),
                                 {F(1, 4): F(1, 16), F(1, 2): F(1, 4), F(3, 4): F(3, 8), F(1): F(5, 16)},
                                 (1, F(17, 48), 0)), primary=True),
        "distinct/4": dict(_ONES, hdi={q: (None, 0) for q in (0, 0.5, 1)}),
        "name_collisions": _det(3, 0, (3, F(17, 16), 0), {F(0): F(5, 16), F(1): F(3, 8), F(2): F(1, 4), F(3): F(1, 16)}),
        **{c: NOCLAIM for c in COLL},
    },
    "D": {
        "Y_D": dict(_det(0, 1, (0, F(1, 2), 1), HOLD, (1, F(1, 2), 0)), primary=True),
        "Y_R": dict(_det(0, 0, (0, F(1, 2), 1), HOLD), hdi={q: (None, 0) for q in (0, 0.5, 1)}),
        "passing": _PASS2, **{c: NOCLAIM for c in COLL},
    },
    "S": {
        "Y_R": dict(_det(0, 1, (0, F(15, 16), 1), {F(0): F(1, 16), F(1): F(15, 16)}, (1, F(1, 16), 0)), primary=True),
        "Y_D": _det(0, 1, (0, F(1, 2), 1), HOLD, (1, F(1, 2), 0)),
        "passing": _PASS2, **{c: NOCLAIM for c in COLL},
    },
    "L": {
        "Y_R": dict(_det(0, 1, (0, F(1, 2), 1), {F(0): F(1, 2), F(1): F(1, 2)}, (1, F(1, 2), 0)), primary=True),
        "Y_D": _det(0, 1, (0, 0, 0), None, (1, 1, 1)),
        "passing": _PASS2, **{c: NOCLAIM for c in COLL},
    },
    "H": {
        "clean_fraction": dict(_det(0, 1, (0, F(49, 64), 1),
                                    {F(0): F(1, 16), F(1, 4): F(1, 16), F(1, 2): F(1, 8), F(3, 4): F(1, 4), F(1): F(1, 2)},
                                    (1, F(15, 64), 0)), primary=True),
        "cascade_length": _det(4, 0, (4, F(15, 16), 0), _CASC),
        "spread_p": _det(1, 0, (1, F(1, 2), 0), {F(0): F(1, 2), F(1): F(1, 2)}),
        **{c: NOCLAIM for c in COLL},
    },
    "H-shared": {
        "clean_fraction": dict(_det(0, 1, (0, F(1, 2), 1), _SHARED, (1, F(1, 2), 0)), primary=True),
    },
}


# --- one validated episode ---------------------------------------------------------------------------------------

def _taskset(pid, s):
    return (team.hold.relay_gen(s) if pid in ("H", "H-shared") else team.alloc.gen(s) if pid in ("A", "C")
            else team.hold.gen(s))


def _real(pid):
    return "H" if pid == "H-shared" else pid


def _episode(pid, arm, q, s, **kw):
    """One scripted episode through team.run_episode; refuses a record without instrument_validation: true."""
    p = _real(pid)
    if p == "L" and "cards" not in kw:
        kw["cards"] = practicemod.lead_cards(practicemod.load("L"), [f"a{i}" for i in range(4)], "a0")
    if pid == "H-shared":
        kw["layout"] = "shared"
    rec = team.run_episode(_taskset(pid, s), arm, p, seed=s, q=q, **kw)
    if not isinstance(rec, dict) or rec.get("instrument_validation") is not True or rec.get("provenance") != PROVENANCE:
        raise RuntimeError("record lacks instrument_validation: true and the provenance label; the rung-0 driver "
                           "refuses to run")
    return rec


def _outcomes(pid, rec):
    sc, y, o = rec["scores"], rec["Y"], rec["orders"]
    coll = {"claim_collision_attempted_rate": o["claim_collision_attempted_rate"],
            "claim_collision_executed_rate": o["claim_collision_rate"]}
    if pid == "A":
        return {"distinct/4": y, **coll, "dup_executed": sc["duplicates"]}
    if pid == "C":
        return {"surviving/4": y, "distinct/4": sc["distinct_passing"] / sc["slots"],
                "name_collisions": sc["name_collisions"], **coll}
    if pid in ("D", "S", "L"):
        return {"Y_D": sc["Y_D"], "Y_R": sc["Y_R"], "passing": sc["passing"], **coll}
    if pid == "H":
        return {"clean_fraction": y, "cascade_length": sc["cascade_length"],
                "spread_p": float(sc["cascade_length"] > 0), **coll}
    return {"clean_fraction": y}


def _collect(practices, qs, sets, seed):
    rows = []
    for pid in practices:
        for k in range(sets):
            s = seed + k
            for q in qs:
                for arm in team.ARMS:
                    rec = _episode(pid, arm, q, s)
                    rows.append({"instrument_validation": True, "provenance": PROVENANCE, "practice": pid,
                                 "arm": arm, "q": q, "set": k, "seed": s, "Y": rec["Y"], "ended": rec["ended"],
                                 "taskset_sha256": rec["taskset_sha256"],
                                 "violations_executed": rec["violations_executed"], "outcomes": _outcomes(pid, rec)})
    return rows


# --- comparison --------------------------------------------------------------------------------------------------

def _close(val, exp, tol):
    if exp is None:
        return val is None
    return val is not None and abs(val - float(exp)) <= tol


def _tol(sd, n):
    return Z * sd / math.sqrt(n) if sd else EXACT


def _mean(vals):
    d = [v for v in vals if v is not None]
    return sum(d) / len(d) if d else None


def _cells(rows, practices, qs, sets):
    out = []
    for pid in practices:
        names = list(rows_outcomes(rows, pid))
        for name in names:
            spec = EXPECT.get(pid, {}).get(name, {})
            for arm in team.ARMS:
                for q in (qs if arm in ("play", "both") else qs[:1]):
                    vals = [r["outcomes"][name] for r in rows if r["practice"] == pid and r["arm"] == arm
                            and r["q"] == q]
                    v = _mean(vals)
                    exp = tol = None
                    if arm in ("none", "code") and arm in spec:
                        exp, sd = spec[arm]
                        tol = _tol(sd, sets)
                    elif arm == "play" and q in spec.get("play", {}):
                        exp, sd = spec["play"][q]
                        tol = _tol(sd, sets)
                    compared = tol is not None
                    out.append({"practice": pid, "outcome": name, "arm": arm, "q": q if arm in ("play", "both") else None,
                                "n": len(vals), "value": v,
                                "reason": None if v is not None else "undefined in every episode (no claims or zero denominator)",
                                "expected": None if exp is None else float(exp), "tol": tol, "compared": compared,
                                "ok": _close(v, exp, tol) if compared else None})
    return out


def rows_outcomes(rows, pid):
    for r in rows:
        if r["practice"] == pid:
            return r["outcomes"]
    return {}


def _hdis(rows, practices, qs, sets):
    out = []
    for pid in practices:
        for name, spec in EXPECT.get(pid, {}).items():
            if "hdi" not in spec:
                continue
            for q in qs:
                get = lambda arm, k, qq: next(r["outcomes"][name] for r in rows if r["practice"] == pid
                                              and r["arm"] == arm and r["q"] == qq and r["set"] == k)
                data = [{"set": k, "none": get("none", k, qs[0]), "play": get("play", k, q), "code": get("code", k, qs[0])}
                        for k in range(sets)]
                h = stats.hdi(data, "set", n=BOOT, seed=0)
                ent = spec["hdi"].get(q)
                ok = band = exp = None
                if ent is not None:
                    if ent[0] == "band":
                        band = (ent[1], ent[2])
                        ok = not h["undefined"] and band[0] <= h["point"] <= band[1]
                        if ok and sets >= 5:  # one cluster id for every set resamples one cluster: width 0
                            ok = h["lo"] < h["hi"]
                    else:
                        exp = ent[0]
                        tol = _tol(ent[1], sets) if exp is not None else None
                        ok = (h["undefined"] and h["point"] is None) if exp is None else (
                            not h["undefined"] and abs(h["point"] - float(exp)) <= tol)
                        if ok and exp is not None and ent[1] == 0:
                            # common random numbers: an endpoint is the same in every set, so its CI collapses
                            # onto it. A broken pairing (another set's row) leaves the point and widens the CI.
                            ok = abs(h["lo"] - float(exp)) <= EXACT and abs(h["hi"] - float(exp)) <= EXACT
                out.append({"practice": pid, "outcome": name, "q": q, "point": h["point"], "lo": h["lo"], "hi": h["hi"],
                            "undefined": h["undefined"], "reason": h["reason"], "denom_ci": h["denom_ci"],
                            "expected": None if exp is None else float(exp), "band": band, "compared": ent is not None,
                            "ok": ok})
    return out


# --- instrument checks -------------------------------------------------------------------------------------------

def _chk(checks, name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


class _Probe(team.ScriptedAdopter):
    """Adopter whose turn is a caller-supplied script; used to observe what the loop shows an agent."""

    def __init__(self, fn):
        super().__init__(1, 0)
        self.fn, self.seen = fn, []

    def turn(self, ctx):
        return self.fn(self, ctx)


def _first_task(ctx):
    return sorted(ctx.tasks)[0]


def _floor_oracle(checks, practices, sets, seed):
    seeds = [seed + k for k in range(sets)]
    if "A" in practices or "C" in practices:
        ok_f = ok_o = ok_b = ok_ob = True
        for s in seeds:
            ts = team.alloc.gen(s)
            fl, orc = team.alloc.score(team.alloc.floor_log(ts), ts), team.alloc.score(team.alloc.oracle_log(ts), ts)
            bare = [dict(e, name="result") for e in team.alloc.oracle_log(ts)]  # naive agents: one bare name
            b = team.alloc.score(bare, ts)
            ok_f &= fl["distinct_passing"] < fl["slots"]
            ok_o &= orc["distinct_passing"] == orc["slots"]
            ok_b &= b["surviving_passing"] < b["slots"]
            ok_ob &= orc["surviving_passing"] == orc["slots"]
        _chk(checks, "floor:alloc fails", ok_f)
        _chk(checks, "oracle:alloc passes", ok_o)
        _chk(checks, "floor:alloc bare names fail (clobber)", ok_b)
        _chk(checks, "oracle:alloc unique names pass", ok_ob)
    if any(p in practices for p in ("D", "S", "L")):
        ok_f = ok_o = True
        for s in seeds:
            ts = team.hold.gen(s)
            fl, orc = team.hold.score(team.hold.floor_log(ts), ts), team.hold.score(team.hold.oracle_log(ts), ts)
            ok_f &= fl["Y_D"] < 1 and fl["Y_R"] < 1
            ok_o &= orc["Y_D"] == 1 and orc["Y_R"] == 1 and orc["passing"] == 2
        _chk(checks, "floor:hold fails", ok_f)
        _chk(checks, "oracle:hold passes", ok_o)
    if "H" in practices:
        ok_f = ok_o = True
        for s in seeds:
            ok_f &= _episode("H", "none", 0, s)["Y"] < 1  # naive agents copy the note
            ok_o &= _episode("H", "play", 1, s)["Y"] == 1  # perfect agents write their own
        _chk(checks, "floor:relay fails", ok_f)
        _chk(checks, "oracle:relay passes", ok_o)


def _probes(checks):
    # stale snapshot: a same-round claim is invisible to the next agent's read
    def stale(ad, ctx):
        if ctx.phase:
            return []
        if ctx.agent == "a0":
            return [{"type": "claim", "agent": "a0", "item": _first_task(ctx)}]
        if ctx.agent == "a1":
            ad.seen.append(ctx.read()["claims"])
        return []
    pr = _Probe(stale)
    team.run_episode(team.alloc.gen(0), "none", "A", seed=0, adopter=pr)
    _chk(checks, "probe:stale snapshot (same-round claim invisible)", pr.seen == [{}], f"a1 saw claims {pr.seen}")

    # claim lock: under code a second claim on a claimed item is refused with the A predicate
    def dup(ad, ctx):
        return [] if ctx.phase or ctx.agent not in ("a0", "a1") else [
            {"type": "claim", "agent": ctx.agent, "item": _first_task(ctx)}]
    rec = team.run_episode(team.alloc.gen(0), "code", "A", seed=0, adopter=_Probe(dup))
    why = [w for _, w in rec["refusals"]]
    _chk(checks, "probe:claim lock (duplicate claim refused under code)",
         any(w.startswith("A:duplicate_claim") for w in why), f"refusals {why}")

    # plant: not on the board in the round it is posted (round 0), delivered in round 1
    def plant(ad, ctx):
        if ctx.agent == "a0":
            ad.seen.append((ctx.phase, sum(i.get("kind") == "plant" for i in ctx.read()["items"])))
        return []
    pr = _Probe(plant)
    team.run_episode(team.hold.gen(0), "none", "D", seed=0, adopter=pr)
    _chk(checks, "probe:plant hidden in round 1, delivered in round 2", pr.seen == [(0, 0), (1, 1)], f"saw {pr.seen}")

    # claim collisions count attempts: four agents claim one item in one round under code; 1 executes, 3 are refused
    herd = lambda ad, ctx: [] if ctx.phase else [{"type": "claim", "agent": ctx.agent, "item": _first_task(ctx)}]
    rec = team.run_episode(team.alloc.gen(0), "code", "A", seed=0, adopter=_Probe(herd))
    o = rec["orders"]
    _chk(checks, "probe:claim collisions from attempts (herd under code: attempted 1/4, executed 0, 3 refused)",
         o["claim_collision_attempted_rate"] == 0.25 and o["claim_collision_rate"] == 0.0 and rec["refused"] == 3
         and rec["ended"] == "complete", f"{o['claim_collision_attempted_rate']} {o['claim_collision_rate']} {rec['refused']}")

    # false done: join of work and release events through the action trace
    def release(skip):
        def fn(ad, ctx):
            mine = sorted(ctx.tasks)[int(ctx.agent[1:])]
            if ctx.phase == 0:
                return [adopters._claim(ctx, mine)]
            work = [] if ctx.agent in skip else [adopters._work(ctx, mine)]
            return work + [{"type": "release", "agent": ctx.agent, "item": mine, "done": True}]
        return fn
    fd = lambda skip: team.run_episode(team.alloc.gen(0), "none", "A", seed=0,
                                       adopter=_Probe(release(skip)))["orders"]["false_done_rate"]
    got = (fd(()), fd(("a2", "a3")), fd(("a0", "a1", "a2", "a3")),
           team.run_episode(team.alloc.gen(0), "none", "A", seed=0)["orders"]["false_done_rate"])
    _chk(checks, "probe:false done (honest 0, half dishonest 1/2, all dishonest 1, no releases None)",
         got == (0.0, 0.5, 1.0, None), f"{got}")

    # tie-break: the adopters' choice is uniform over the options, never a fixed lowest index
    ad = team.ScriptedAdopter(0.5, 0)
    picks = [ad.choose(f"probe:{i}", range(6)) for i in range(600)]
    n = [picks.count(i) for i in range(6)]
    _chk(checks, "probe:tie-break uniform over options", min(n) >= 60 and max(n) <= 150, f"counts {n}")

    # scoring reads only the accepted log events: a rejected event scores nothing
    ts = team.alloc.gen(1)
    log = team.alloc.oracle_log(ts)
    sc = team.alloc.score(log + [dict(log[0], agent="a9", name="z", rejected=True)], ts)
    ht = team.hold.gen(1)
    held_work = {"agent": "a0", "action": "work", "task": ht["held"][0], "answer": 0, "rejected": True}
    hs = team.hold.score(team.hold.oracle_log(ht) + [held_work], ht)
    _chk(checks, "probe:scoring ignores rejected events (log, not agent state)",
         sc["duplicates"] == 0 and sc["distinct_passing"] == 4 and hs["Y_D"] == 1)

    # a report naming an unheld task is not counted; one naming a held task is
    unheld = sorted(set(ht["assigned"].values()) - set(ht["held"]))[0]
    wrong = team.hold.score([{"agent": "a0", "action": "post", "kind": "report", "refs": [unheld]}], ht)
    right = team.hold.score([{"agent": "a0", "action": "post", "kind": "report", "refs": [ht["held"][0]]}], ht)
    _chk(checks, "probe:report for the wrong task not counted", wrong["Y_R"] == 0 and right["Y_R"] == 0.5)

    # clobber: same name, last accepted writer survives
    bare = [dict(e, name="result") for e in team.alloc.oracle_log(ts)]
    cs = team.alloc.score(bare, ts)
    _chk(checks, "probe:clobber scoring on (bare name keeps one survivor)",
         cs["surviving_passing"] == 1 and cs["distinct_passing"] == 4)

    # HDI arithmetic on rows with a known answer
    mk = lambda none, play, code: [{"k": i, "none": none + 0.01 * (i % 3), "play": play + 0.01 * (i % 3),
                                    "code": code + 0.01 * (i % 3)} for i in range(10)]
    a, b, c = (stats.hdi(mk(*t), "k", n=500) for t in ((0.2, 0.5, 0.8), (0.25, 0.75, 1.0), (0.2, 0.9, 0.9)))
    flat = stats.hdi(mk(0.5, 0.5, 0.5), "k", n=500)
    _chk(checks, "probe:HDI denominator is Y_code - Y_none",
         all(h["point"] is not None for h in (a, b, c)) and abs(a["point"] - 0.5) < 1e-9
         and abs(b["point"] - 1 / 3) < 1e-9 and abs(c["point"]) < 1e-9 and flat["undefined"],
         f"points {a['point']}, {b['point']}, {c['point']}")


def _structure(checks, rows, practices, qs, sets):
    rl = lambda pid, arm, q: [r["Y"] for r in rows if r["practice"] == pid and r["arm"] == arm and r["q"] == q]
    for pid in practices:
        for arm in ("none", "code"):  # q acts only in play and both
            _chk(checks, f"q leak:{pid} {arm} constant across q", all(rl(pid, arm, q) == rl(pid, arm, qs[0]) for q in qs))
        if 0 in qs:
            _chk(checks, f"edge:{pid} play(q=0) == none per set", rl(pid, "play", 0) == rl(pid, "none", 0))
        if 1 in qs and pid in EXPECT:
            _chk(checks, f"edge:{pid} play(q=1) == code per set", rl(pid, "play", 1) == rl(pid, "code", 1))
        _chk(checks, f"ended:{pid} every episode complete", all(r["ended"] == "complete" for r in rows if r["practice"] == pid))
        if pid in ("D", "S", "L"):
            _chk(checks, f"hold:{pid} passing is 2 of 2 in every episode",
                 all(r["outcomes"]["passing"] == 2 for r in rows if r["practice"] == pid))
        if pid in ("D", "S", "L", "C"):
            _chk(checks, f"code:{pid} no violation executed under code",
                 all(r["violations_executed"] == 0 for r in rows if r["practice"] == pid and r["arm"] == "code"))
        if pid == "A":
            _chk(checks, "code:A no executed duplicate work",
                 all(r["outcomes"]["dup_executed"] == 0 for r in rows if r["practice"] == "A" and r["arm"] == "code"))


def _pairing(checks, rows, practices, qs):
    for pid in practices:
        for k in sorted({r["set"] for r in rows if r["practice"] == pid}):
            hashes = {r["taskset_sha256"] for r in rows if r["practice"] == pid and r["set"] == k}
            _chk(checks, f"pair:{pid} set {k} one task set in every arm and q", len(hashes) == 1, f"{len(hashes)} task sets")
        if pid == "A":
            att = lambda arm, q: [r["outcomes"]["claim_collision_attempted_rate"] for r in rows
                                  if r["practice"] == "A" and r["arm"] == arm and r["q"] == q]
            exe = lambda arm, q: [r["outcomes"]["claim_collision_executed_rate"] for r in rows
                                  if r["practice"] == "A" and r["arm"] == arm and r["q"] == q]
            for q in qs:
                for arm in ("none", "play"):  # no enforcement: nothing is refused, so attempted == executed, per set
                    _chk(checks, f"claims:A {arm} q={q} attempted == executed per set", att(arm, q) == exe(arm, q))
            _chk(checks, "claims:A code executed collisions are 0 in every set", all(v == 0 for v in exe("code", qs[0])))
            if 1 in qs:  # same behaviour, same attempts: enforcement changes what executes, not what is tried
                _chk(checks, "claims:A code attempted == play(q=1) attempted per set", att("code", qs[0]) == att("play", 1))
                _chk(checks, "claims:A code attempts collide somewhere (a 0 is not a measurement)",
                     any(v for v in att("code", qs[0]) if v is not None))


def run(practices=TOP[:6], qs=(0, 0.5, 1), sets=15, seed=0):
    """Run the rung-0 batch; returns the table described in the module docstring. Scripted, zero cost."""
    practices, qs = tuple(practices), tuple(qs)
    bad = [p for p in practices if p not in TOP]
    if bad or not qs or sets < 1 or any(isinstance(q, bool) or not 0 <= q <= 1 for q in qs):
        raise ValueError(f"practices must be in {TOP}, qs in [0, 1], sets >= 1; got {practices} {qs} {sets}")
    rows = _collect(practices, qs, sets, seed)
    if any(r.get("instrument_validation") is not True for r in rows):
        raise RuntimeError("a record lacks instrument_validation: true; the rung-0 driver refuses to run")
    checks = []
    _floor_oracle(checks, practices, sets, seed)
    _probes(checks)
    _structure(checks, rows, practices, qs, sets)
    _pairing(checks, rows, practices, qs)
    cells, hdis = _cells(rows, practices, qs, sets), _hdis(rows, practices, qs, sets)
    void = [c["name"] for c in checks if not c["ok"] and c["name"].split(":")[0] in ("floor", "oracle")]
    red = [c["name"] for c in checks if not c["ok"]] + [f"cell {c['practice']} {c['outcome']} {c['arm']} q={c['q']}"
                                                          for c in cells if c["ok"] is False] + [
        f"hdi {h['practice']} {h['outcome']} q={h['q']}" for h in hdis if h["ok"] is False]
    return {"instrument_validation": True, "label": LABEL, "provenance": PROVENANCE, "practices": practices, "qs": qs, "sets": sets,
            "seed": seed, "episodes": len(rows), "rows": rows, "cells": cells, "hdi": hdis, "checks": checks,
            "void": bool(void), "failures": red, "verdict": "VOID" if void else "RED" if red else "GREEN"}


# --- report ------------------------------------------------------------------------------------------------------

def _f(x):
    return "None" if x is None else f"{x:.4f}"


def report(table, path=None):
    """Markdown summary of `table`; written to `path` when given. Returns the text."""
    if table.get("instrument_validation") is not True or any(r.get("instrument_validation") is not True
                                                           for r in table["rows"]):
        raise ValueError("table lacks instrument_validation: true; refusing to report")
    flag = lambda ok: "n/a" if ok is None else "PASS" if ok else "FAIL"
    L = [f"# Rung 0 report: {table['verdict']}", "", f"> {table['label']}. instrument_validation: true.", "", f"> Provenance: {PROVENANCE}", "",
         f"practices {', '.join(table['practices'])}; q {list(table['qs'])}; sets {table['sets']}; seed {table['seed']}; "
         f"episodes {table['episodes']}.", "", "## Instrument checks", "", "| check | result | detail |", "|---|---|---|"]
    L += [f"| {c['name']} | {flag(c['ok'])} | {c['detail']} |" for c in table["checks"]]
    L += ["", "## HDI (cluster bootstrap over sets)", "",
          "| practice | outcome | q | HDI | 95% | expected | result | note |", "|---|---|---|---|---|---|---|---|"]
    for h in table["hdi"]:
        exp = f"{h['band'][0]}..{h['band'][1]}" if h["band"] else "undefined" if h["expected"] is None else _f(h["expected"])
        L.append(f"| {h['practice']} | {h['outcome']} | {h['q']} | {_f(h['point'])} | {_f(h['lo'])}..{_f(h['hi'])} | "
                 f"{exp if h['compared'] else 'none stated'} | {flag(h['ok'])} | {h['reason'] or ''} |")
    L += ["", "## Outcome cells", "", "| practice | outcome | arm | q | value | expected | tol | result | note |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in table["cells"]:
        L.append(f"| {c['practice']} | {c['outcome']} | {c['arm']} | {'' if c['q'] is None else c['q']} | {_f(c['value'])} | "
                 f"{_f(c['expected']) if c['compared'] else 'none stated'} | "
                 f"{'' if c['tol'] is None else format(c['tol'], '.3g')} | {flag(c['ok'])} | {c['reason'] or ''} |")
    L += ["", "## Failures", ""] + ([f"- {f}" for f in table["failures"]] or ["none"])
    text = "\n".join(L) + "\n"
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return text
