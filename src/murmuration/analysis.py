"""EP-1 analysis entry point. Stdlib only. A MODEL table takes only real model records; scripted output is
stamped FAKE and never shares a table with model output (EP1 section on HDI, review-integration 8.4).

Record fields read (team_claude.run_episode): evidence, instrument_validation, label, episode_id, model,
arm, Y, ended, void, abort_reason, malformed_by_reason, refused, stopped_agents, turns, plus
`taskset_id` (else `taskset_sha256`) and optional `agent_answers`: [{agent, task, answer, pass}]; for the exploratory
read-offs, optional `scores` (alloc), `scorers.alloc2` and `orders`.
"""
from collections import defaultdict
from itertools import combinations

from . import stats

PRIOR_ART = ("Prior art: team-alignment papers are binding prior art; this is a narrow, token-matched test "
             "and claims no novelty over them.")
INCONCLUSIVE = "inconclusive is neither equivalence nor a null finding"
FAKE = "FAKE: scripted instrument validation; not evidence about any model"
CONTRASTS = (("play_none", "Y_play - Y_none"), ("code_none", "Y_code - Y_none"), ("code_play", "Y_code - Y_play"))
MIN_TASK_SETS = 12  # prereg/EP1.md section 10: fewer complete sets and every contrast reads NOT_SHOWN
NOT_SHOWN = "incomplete: not shown"
SOI = 0.20  # prereg section 9: the smallest effect of interest, 20 points
SMALLER = "smaller than the 20-point effect of interest"  # prereg section 11, ruling 3: cluster-bootstrap hi < 0.20
EXPLORATORY = "exploratory"  # prereg sections 8 and 11: every number other than the primary contrast
INCONCLUSIVE_LABEL = "not resolved: inconclusive"
# Intention to treat (orchestrator ruling on G1b-R R-5, 2026-11-20): an episode ended because every agent was stopped by
# the refusal rule is scored from its log and counted, never dropped; prereg section 12 "scored from its log and flagged".
SCORED_ENDS = ("complete", "episode_stopped")
RELEASE_NOTE = ("Only card A tells the agent to release, and the code arm has no release rule: a play difference in "
                "false-done is not a card-against-code result (prereg sections 6 and 8).")
KILL = ("Kill read-off: Y_play - Y_none has hi < 0.20 in both intervals; the card is dropped on this task and tier "
        "(prereg section 12).")


class AnalysisRefused(ValueError):
    pass


def _is_scripted(r):
    rid = str(r.get("episode_id") or r.get("run_id") or "")
    return (r.get("instrument_validation") is True or "FAKE" in str(r.get("label") or "")
            or r.get("evidence") == "fake" or rid.lower().startswith("scripted:"))


def _check(records, kind):
    if kind not in ("model", "scripted"):
        raise ValueError("kind must be 'model' or 'scripted'")
    for r in records:
        rid = r.get("episode_id") or r.get("run_id")
        if kind == "model":
            if _is_scripted(r):
                raise AnalysisRefused(f"refused: record {rid!r} is scripted/instrument validation/FAKE; "
                                      "it can never enter a model table or figure")
            if r.get("evidence") != "model":
                raise AnalysisRefused(f"refused: record {rid!r} has evidence {r.get('evidence')!r}, not 'model'")
            if not rid:
                raise AnalysisRefused("refused: a model record carries no run id")
            if not r.get("model"):
                raise AnalysisRefused(f"refused: model record {rid!r} has no returned model id")
        elif not _is_scripted(r):
            raise AnalysisRefused(f"refused: record {rid!r} is not scripted; scripted and model results never "
                                  "share a table")
        if r.get("instrument_validation") is True and not str(rid).lower().startswith("scripted:"):
            raise AnalysisRefused(f"refused: scripted run id {rid!r} must carry the 'scripted:' prefix")


def _set_id(r):
    s = r.get("taskset_id") or r.get("taskset_sha256")
    if not s:
        raise AnalysisRefused(f"refused: record {r.get('episode_id')!r} names no task set")
    return s


def error_correlation(errors):
    """Pairwise phi of 0/1 error vectors {agent: [..]} over the same items; None where a vector is constant."""
    out = {}
    for a, b in combinations(sorted(errors), 2):
        x, y = errors[a], errors[b]
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        sx, sy = sum((v - mx) ** 2 for v in x), sum((v - my) ** 2 for v in y)
        out[(a, b)] = (sum((u - mx) * (v - my) for u, v in zip(x, y)) / (sx * sy) ** 0.5) if sx and sy else None
    return out


def _agents(recs):
    """Per agent pair over shared (episode, task) items: phi of wrongness, identical-wrong and agreement counts."""
    items = defaultdict(dict)
    for r in recs:
        for a in r.get("agent_answers") or ():
            items[a["agent"]][(r.get("episode_id"), a["task"])] = (a["answer"], bool(a["pass"]))
    res = {}
    for a, b in combinations(sorted(items), 2):
        shared = sorted(set(items[a]) & set(items[b]), key=str)
        if not shared:
            continue
        ea = [int(not items[a][k][1]) for k in shared]
        eb = [int(not items[b][k][1]) for k in shared]
        same = [items[a][k][0] == items[b][k][0] for k in shared]
        res[(a, b)] = {"items": len(shared), "phi": error_correlation({a: ea, b: eb})[(a, b)],
                       "agree": sum(same), "identical_wrong": sum(s and e for s, e in zip(same, ea) if e)}
    return res


def summarise(records, kind="model", seed=0, n_boot=10000, margin=0.10):
    """Summary dict for a model (default) or scripted table; raises AnalysisRefused on a wrong-kind record.

    n counts TASK SETS, never agent-turns. Contrasts and HDI come from stats.hdi, clustered by task set,
    over the task sets present in all three arms (play, code, none), Y averaged within set.
    Contrast statistics are withheld below the preregistered complete-set floor.
    """
    records = list(records)
    _check(records, kind)
    arms = defaultdict(list)
    for r in records:
        arms[r["arm"]].append(r)
    per = {}
    for arm, rs in sorted(arms.items()):
        sets = {_set_id(r) for r in rs}
        cens = {_set_id(r) for r in rs if r.get("ended") not in SCORED_ENDS or r.get("void") or r.get("abort_reason")}
        turns = [t for r in rs for t in r.get("turns") or ()]
        per[arm] = {"task_sets": len(sets), "episodes": len(rs),
                    "completion": sum(r.get("ended") == "complete" for r in rs) / len(rs),
                    "all_agents_stopped": sum(r.get("ended") == "episode_stopped" and not r.get("void") for r in rs),
                    "truncations": sum((r.get("malformed_by_reason") or {}).get("truncated", 0) for r in rs),
                    "retries": sum(t.get("retries", 0) or 0 for t in turns) + sum(r.get("retries", 0) or 0 for r in rs),
                    "denials": sum(r.get("refused", 0) or 0 for r in rs), "censored_task_sets": len(cens),
                    "refusal_stopped_agents": sum(len(r.get("stopped_agents") or ()) for r in rs),
                    "refusal_rows": _refusal_rows(rs)}
    ys = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("Y") is not None and r.get("ended") in SCORED_ENDS and not r.get("void"):
            ys[_set_id(r)][r["arm"]].append(r["Y"])
    rows = [{"set": s, **{a: sum(v[a]) / len(v[a]) for a in ("none", "play", "code")}}
            for s, v in sorted(ys.items()) if all(v.get(a) for a in ("none", "play", "code"))]
    shown = len(rows) >= MIN_TASK_SETS
    h = stats.hdi(rows if shown else [], "set", n=n_boot, seed=seed, margin=margin)
    if not shown:
        h.update(reason=NOT_SHOWN, degenerate_resamples=None)
    # secondary pre-registered few-cluster guard: paired t on per-set differences, beside the bootstrap
    pt = {k: stats.paired_t([(r[a], r[b]) for r in rows]) if shown else None
          for k, (a, b) in {"play_none": ("play", "none"), "code_none": ("code", "none"),
                            "code_play": ("code", "play")}.items()}
    contrasts = {k: _contrast(name, h["contrasts"][k], pt.get(k), k != CONTRASTS[0][0], shown) for k, name in CONTRASTS}
    ok = h["status"] == "interpretable" and shown  # HDI is a ratio of the contrasts: hidden with them
    hb = {"interpretable": ok, "reason": None if ok else h["reason"] if shown else NOT_SHOWN, "label": EXPLORATORY,
          **({"point": h["point"], "lo": h["lo"], "hi": h["hi"], "recovered": h["recovered"]} if ok else {})}
    prim = contrasts[CONTRASTS[0][0]]
    kill = {"fires": prim["hi_below_soi_both"],
            "code_rule_stays": contrasts["code_none"]["resolved"] == "positive" if shown else None}
    return {"kind": kind, "label": FAKE if kind == "scripted" else "model episodes: evidence about the returned model ids only",
            "models": sorted({r["model"] for r in records if r.get("model")}), "arms": per,
            "n_task_sets_all_arms": len(rows), "min_task_sets": MIN_TASK_SETS, "shown": shown, "hdi": h,
            "contrasts": contrasts, "hdi_block": hb, "kill": kill,
            "exploratory": {"label": EXPLORATORY, "paired_t": pt, "release_note": RELEASE_NOTE,
                            "per_arm": {a: _readoffs(rs) for a, rs in sorted(arms.items())}}}


def _refusal_rows(rs):
    """Refusals of one arm in two rows, never one sum (prereg change 15): enforcer denials `A:*` and board errors
    `board_error:*`; any other reason is shown on its own so none drops silently."""
    out = {"A": 0, "board_error": 0, "other": 0}
    for r in rs:
        for x in r.get("refusals") or ():
            why = str(x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else x)
            out["A" if why.startswith("A:") else "board_error" if why.startswith("board_error:") else "other"] += 1
    return out


def _readoffs(rs):
    """Secondary read-offs of one arm (prereg section 8), all exploratory: false-done from alloc2's executed in-set
    releases, name and claim collisions, and the pairwise agent error read-off."""
    ok = [r for r in rs if r.get("ended") in SCORED_ENDS and not r.get("void")]
    a2 = [((r.get("scorers") or {}).get("alloc2") or {}) for r in ok]
    done, fd = sum(s.get("done_releases") or 0 for s in a2), sum(s.get("false_done") or 0 for s in a2)
    cc = [x for x in ((r.get("orders") or {}).get("claim_collision_rate") for r in ok) if x is not None]
    return {"done_releases": done, "false_done": fd, "false_done_rate": fd / done if done else None,
            "name_collisions": sum((r.get("scores") or {}).get("name_collisions") or 0 for r in ok),
            "claim_collision_rate": sum(cc) / len(cc) if cc else None, "agent_pairs": _agents(rs)}


def resolve(boot, t):
    """The one resolution rule: 'positive'/'negative' only when the bootstrap CI and the paired-t CI both exclude 0 on
    the same side (a missing paired t, one task set, defers to the bootstrap alone); else 'unresolved'."""
    side = "positive" if boot[0] > 0 else "negative" if boot[1] < 0 else None
    if side and t is not None and (t[0] > 0, t[1] < 0) != ((side == "positive"), (side == "negative")):
        return "unresolved"
    return side or "unresolved"


def _contrast(name, c, t, exploratory, shown):
    """One contrast record. `label` is one of the prereg section 11 labels; `smaller_than_effect_of_interest` is True
    when the cluster-bootstrap hi < SOI (ruling 3); `hi_below_soi_both` (hi < SOI in both intervals) drives the
    section 12 kill read-off. Both None when not computed; below MIN_TASK_SETS nothing is shown."""
    out = {"name": name, "point": None, "ci_boot": None, "ci_t": None, "resolved": "unresolved",
           "label": NOT_SHOWN if not shown else INCONCLUSIVE_LABEL, "smaller_than_effect_of_interest": None,
           "hi_below_soi_both": None, "exploratory": exploratory}
    if not shown or c["d"] is None:
        return out
    boot, tci = (c["lo"], c["hi"]), (t["ci95_lo"], t["ci95_hi"]) if t else None
    res = resolve(boot, tci)
    return dict(out, point=c["d"], ci_boot=boot, ci_t=tci, resolved=res,
                label=INCONCLUSIVE_LABEL if res == "unresolved" else f"resolved {res}",
                smaller_than_effect_of_interest=boot[1] < SOI,
                hi_below_soi_both=tci is not None and boot[1] < SOI and tci[1] < SOI)


def _f(x, fmt=".3f"):
    return "n/a" if x is None else format(x, fmt)


def render(summary):
    """Plain-text report built only from the structured summary fields (contrasts, hdi_block, kill, exploratory);
    no rule of its own."""
    L = [PRIOR_ART, "", summary["label"], "", f"n (task sets, all three arms): {summary['n_task_sets_all_arms']}", ""]
    L.append("arm  task_sets episodes completion all_stopped trunc retries censored stopped")
    for a, p in summary["arms"].items():
        L.append(f"{a:<4} {p['task_sets']:>9} {p['episodes']:>8} {p['completion']:>10.2f} {p['all_agents_stopped']:>11} "
                 f"{p['truncations']:>5} {p['retries']:>7} {p['censored_task_sets']:>8} {p['refusal_stopped_agents']:>7}")
    L += ["", "refusals per arm, two rows (labels differ by arm by construction; never summed)"]
    for a, p in summary["arms"].items():
        rr = p["refusal_rows"]
        L.append(f"{a:<4} A:*          {rr['A']:>5}")
        L.append(f"{a:<4} board_error:* {rr['board_error']:>4}" + (f"   other {rr['other']}" if rr["other"] else ""))
    L += ["", "contrast          d        lo       hi   t_lo      t_hi   (bootstrap | paired t)"]
    for c in summary["contrasts"].values():
        tag = f"  [{EXPLORATORY}]" if c["exploratory"] else ""
        if c["point"] is None:
            L.append(f"{c['name']:<16} n/a  {c['label']}{tag}")
            continue
        tt = f"{c['ci_t'][0]:+.3f} {c['ci_t'][1]:+.3f}" if c["ci_t"] else "n/a n/a"
        L.append(f"{c['name']:<16} {c['point']:+.3f} {c['ci_boot'][0]:+.3f} {c['ci_boot'][1]:+.3f}  {tt}  {c['label']}"
                 + (f"; {SMALLER}" if c["smaller_than_effect_of_interest"] else "") + tag)
    if any(c["resolved"] == "unresolved" for c in summary["contrasts"].values()):
        L.append(f"Note: {INCONCLUSIVE}.")
    if summary["kill"]["fires"]:
        L.append(KILL + (" Y_code - Y_none is resolved positive: the rule stays in code."
                         if summary["kill"]["code_rule_stays"] else ""))
    L.append("")
    h = summary["hdi_block"]
    if h["interpretable"]:
        L.append(f"HDI {h['point']:.3f} [{h['lo']:.3f}, {h['hi']:.3f}]; recovered fraction {h['recovered']:.3f}"
                 f"  [{EXPLORATORY}]")
    else:
        L.append(f"HDI not interpretable ({h['reason']}); no number reported. {INCONCLUSIVE}.  [{EXPLORATORY}]")
    x = summary["exploratory"]
    L += ["", f"Secondary read-offs [{EXPLORATORY}]: not confirmatory, n = task sets"]
    for k, name in CONTRASTS:
        t = x["paired_t"].get(k) if x["paired_t"] else None
        if t:
            L.append(f"paired t {name}: mean {t['mean_diff']:+.3f} [{t['ci95_lo']:+.3f}, {t['ci95_hi']:+.3f}] "
                     f"df {t['df']}  [{EXPLORATORY}]")
    for a, r in x["per_arm"].items():
        phis = [p["phi"] for p in r["agent_pairs"].values() if p["phi"] is not None]
        L.append(f"{a:<4} false-done {r['false_done']}/{r['done_releases']} = {_f(r['false_done_rate'])}; "
                 f"name collisions {r['name_collisions']}; claim-collision rate {_f(r['claim_collision_rate'])}; "
                 f"mean pairwise error phi {_f(sum(phis) / len(phis) if phis else None)}  [{EXPLORATORY}]")
    L.append(x["release_note"])
    return "\n".join(L) + "\n"
