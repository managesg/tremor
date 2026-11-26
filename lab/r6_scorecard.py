"""R6 Evaluation Scorecard: schema validator and scorer (prereg/R6-pvsnp-research-line-plan.md).

Pure and deterministic. No default for any open parameter: the sealed keyword and pattern
lists and the reviewer flag are required keyword arguments of `score`.
Gate failures zero the rubric total only; `performance_row.pass` is never read or changed.
Author reading: criterion scores are integers 0..5 (the rubric tables give whole anchors).
The frozen weights come from the protocol's freeze record and are a required argument.
"""
import math
import re
import unicodedata

# claim status None or "" is not a schema error: it is the G2 no-status failure
SCHEMA_VERSION = "r6-scorecard-2"
ROLES = ("proposer", "red_team", "control_solver", "definition_auditor", "solver")
LENSES = ("circuit", "algebraic", "meta_complexity", "proof_complexity", "fine_grained", "descriptive")
CLAIM_TYPES = ("lower_bound", "upper_bound", "reduction", "finite_lemma", "formal_statement")
MODELS = ("multitape_tm", "ram", "uniform_circuit", "nonuniform_circuit", "arithmetic_circuit", "proof_system")
PARAMS = ("bit_length_N", "variables_n", "clauses_m", "truth_table_2^n", "matrix_dim_n")
SMALL_N = ("refuted", "not_refuted", "not_testable_at_small_n", "na")
CLAIM_STATUS = ("checked_by_oracle", "proved_in_artifact", "cited_classical", "citation_to_be_verified",
                "recalled_unverified", "from_briefing_unverified", "conjecture")
BARRIER = ("evades", "hits", "not_applicable", "open")
FAMILIES = ("F1", "F2", "F3", "F4", "F5", "F6")
VERDICTS = ("advance", "revise", "prune")
CRITERIA = ("barrier_compliance", "formal_precision", "falsifiability", "verifiability", "incremental_value")
GATES = ("G1_barrier", "G2_unverified_as_fact", "G3_overclaim", "G4_model_parameter", "G5_separation",
         "G6_definition_audit")
GATE_VALUES = {"G1_barrier": ("pass", "fail", "na"), "G2_unverified_as_fact": ("pass", "fail"),
               "G3_overclaim": ("pass", "fail"), "G4_model_parameter": ("pass", "fail"),
               "G5_separation": ("pass", "fail", "na"), "G6_definition_audit": ("pass", "fail", "na")}
N0_MAX = 20  # plan M3: a refutation needs a threshold n0 <= 20


_DASHES = {ord(c): "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"}


def _nfkc(s):
    return unicodedata.normalize("NFKC", s).translate(_DASHES)


def _fold(s):
    """Match form for keywords and scanned text: compatibility-normalised, dashes unified, case-folded."""
    return _nfkc(s).casefold()


def _isint(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _text(v):
    return isinstance(v, str) and v.strip() != ""


def _str(p, v, e):
    if not isinstance(v, str):
        e.append(f"{p}: not a string")


def _bool(p, v, e):
    if not isinstance(v, bool):
        e.append(f"{p}: not a bool")


def _int(lo, hi=None):
    def f(p, v, e):
        if not _isint(v) or v < lo or (hi is not None and v > hi):
            e.append(f"{p}: not an integer >= {lo}" + (f" and <= {hi}" if hi is not None else ""))
    return f


def _num(lo, hi=None):
    def f(p, v, e):
        if not _isnum(v) or v < lo or (hi is not None and v > hi):
            e.append(f"{p}: not a finite number in [{lo}, {hi if hi is not None else 'inf'}]")
    return f


def _enum(*vals):
    def f(p, v, e):
        if not isinstance(v, str) or v not in vals:
            e.append(f"{p}: not one of {vals}")
    return f


def _opt(inner):
    def f(p, v, e):
        if v is not None:
            _walk(p, v, inner, e)
    return f


def _list(inner):
    def f(p, v, e):
        if not isinstance(v, list):
            e.append(f"{p}: not a list")
            return
        for i, x in enumerate(v):
            _walk(f"{p}[{i}]", x, inner, e)
    return f


def _const(want):
    def f(p, v, e):
        if not isinstance(v, str) or v != want:
            e.append(f"{p}: must be {want!r}")
    return f


def _span(p, v, e):
    if isinstance(v, str) or (isinstance(v, list) and len(v) == 2 and all(_isint(x) and x >= 0 for x in v)
                              and v[0] <= v[1]):
        return
    e.append(f"{p}: span must be a string or [start, end] integers, start <= end")


def _sha(p, v, e):
    if not isinstance(v, str) or not re.fullmatch(r"([0-9a-f]{64})?", v):
        e.append(f"{p}: not empty or 64 lowercase hex")


def _walk(p, v, spec, e):
    if callable(spec):
        spec(p, v, e)
        return
    if not isinstance(v, dict):
        e.append(f"{p or '<root>'}: not an object")
        return
    for k in sorted(v, key=str):
        if k not in spec:
            e.append(f"{p}.{k}: unknown key" if p else f"{k}: unknown key")
    for k, s in spec.items():
        q = f"{p}.{k}" if p else k
        if k not in v:
            e.append(f"{q}: missing")
        else:
            _walk(q, v[k], s, e)


def _barrier(extra=None):
    d = {"status": _enum(*BARRIER), "argument": _str}
    if extra:
        d.update(extra)
    return d


_METER = {"k": _opt(_num(0)), "c": _opt(_num(0)), "s": _opt(_num(0)), "cost_ops": _opt(_num(0)),
          "density": _opt(_num(0, 1)), "useful": _opt(_bool)}

_SPEC = {
    "schema_version": _const(SCHEMA_VERSION),
    "line": _const("R6"),
    "candidate_id": _str,
    "iteration": _int(0),
    "commit": _str,
    "agent": {"role": _enum(*ROLES), "model": _str, "team_size": _int(1), "arm": _str},
    "lens": _enum(*LENSES),
    "claim_type": _enum(*CLAIM_TYPES),
    "model_of_computation": _str,  # vocabulary is gate G4, not a schema error
    "input_parameter": _str,
    "statement": _str,
    "predicate": {"path": _str, "sha256": _sha, "domain": _str, "step_limit": _int(0)},
    "small_n_claim": {"explicit_constants": _bool, "threshold_n0": _opt(_int(0)), "result": _enum(*SMALL_N)},
    "claims": _list({"id": _str, "text": _str, "status": _opt(_enum("", *CLAIM_STATUS)), "evidence": _str}),
    "barrier_audit": {"relativization": _barrier(), "natural_proofs": _barrier({"meter": _METER}),
                      "algebrization": _barrier()},
    "hard_gates": {g: _enum(*GATE_VALUES[g]) for g in GATES},
    "criteria": {c: {"score": _int(0, 5), "weight": _num(0, 1), "evidence": _str} for c in CRITERIA},
    "weighted_total": _num(0, 100),
    "disqualified": _bool,
    "disqualification_reasons": _list(_str),
    "oracle_checks": {"claims_checkable": _int(0), "claims_checked": _int(0), "claims_passed": _int(0),
                      "max_n": _int(0), "wall_seconds": _num(0), "checker": _str},
    "red_team": {"attempted": _bool, "verdict": _enum("refuted", "not_refuted", "na"), "counterexample": _str,
                 "counterexample_verified": _opt(_bool), "label_overridden": _bool},
    "definition_audit": {"done": _bool, "auditor": _str, "reference_statement": _str, "faithful": _opt(_bool),
                         "defect_spans": _list(_span)},
    "lean": {"kernel_checked": _bool, "toolchain": _str, "axioms": _list(_str), "sorry_count": _opt(_int(0))},
    "separations": {"asymptotic_vs_practical": _str, "worst_vs_average_case": _str},
    "performance_row": {"task": _str, "family": _enum(*FAMILIES), "n": _int(0), "rerun": _int(0),
                        "agent": _int(0), "pass": lambda p, v, e: None if _isint(v) and v in (0, 1)
                        else e.append(f"{p}: not integer 0 or 1"), "conf": _opt(_num(0, 1))},
    "resources": {"calls": _int(0), "input_tokens": _int(0), "output_tokens": _int(0),
                  "wall_seconds": _num(0), "hosted_usd": _num(0)},
    "verdict": _enum(*VERDICTS),
    "reviewer": {"id": _str, "independent": _bool, "notes": _str, "overclaim_flag": _bool},
    "evidence_paths": _list(_str),
}


def _check_weights(weights):
    if not isinstance(weights, dict) or set(weights) != set(CRITERIA) or not all(_isnum(w) and w >= 0
                                                                               for w in weights.values()):
        raise ValueError("weights: must map each of the five criteria to a finite number >= 0")
    if not math.isclose(math.fsum(weights.values()), 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError("weights: frozen weights must sum to 1.0")


def validate(card, *, weights):
    """Return a list of error strings; empty means the schema holds.

    `weights` are the weights frozen in the protocol; a card whose weights differ is refused.
    """
    _check_weights(weights)
    e = []
    _walk("", card, _SPEC, e)
    if e:
        return e
    for k in CRITERIA:
        if not math.isclose(card["criteria"][k]["weight"], weights[k], rel_tol=0, abs_tol=1e-9):
            e.append(f"criteria.{k}.weight: differs from the frozen weight")
    ids = [c["id"] for c in card["claims"]]
    if len(set(ids)) != len(ids):
        e.append("claims: duplicate id")
    s = card["small_n_claim"]
    if s["result"] == "refuted" and not (s["explicit_constants"] and _isint(s["threshold_n0"])
                                         and s["threshold_n0"] <= N0_MAX):
        e.append(f"small_n_claim: refuted needs explicit constants and threshold_n0 <= {N0_MAX}")
    o = card["oracle_checks"]
    if not o["claims_passed"] <= o["claims_checked"] <= o["claims_checkable"]:
        e.append("oracle_checks: need claims_passed <= claims_checked <= claims_checkable")
    r = card["red_team"]
    if r["label_overridden"] and r["counterexample_verified"] is not True:
        e.append("red_team: label_overridden needs a verified counterexample")
    return e


def _barrier_ok(b):
    return b["status"] in ("evades", "not_applicable") and _text(b["argument"])


def _check_lists(briefing_keywords, overclaim_patterns):
    for name, v in (("briefing_keywords", briefing_keywords), ("overclaim_patterns", overclaim_patterns)):
        if not isinstance(v, (list, tuple)) or not v or not all(_text(x) for x in v):
            raise ValueError(f"{name}: must be a non-empty list of non-empty strings")
    return [re.compile(_nfkc(p), re.IGNORECASE) for p in overclaim_patterns]  # no casefold: it would turn \S into \s


def gates(card, *, briefing_keywords, overclaim_patterns):
    """Compute (gates, reasons) for a schema-valid card."""
    pats = _check_lists(briefing_keywords, overclaim_patterns)
    g, why = {}, []
    ct, b = card["claim_type"], card["barrier_audit"]
    if ct == "lower_bound":
        bad = [k for k in ("relativization", "natural_proofs", "algebrization") if not _barrier_ok(b[k])]
    elif ct == "upper_bound":
        bad = [k for k in ("relativization",) if not _barrier_ok(b[k])]
    else:
        bad = None
    g["G1_barrier"] = "na" if bad is None else ("fail" if bad else "pass")
    if bad:
        why.append("G1: barrier entries not evades/not_applicable with a written argument: " + ", ".join(bad))

    cl, o = card["claims"], card["oracle_checks"]
    n_oracle = sum(c["status"] == "checked_by_oracle" for c in cl)
    p2 = [f"claim {c['id']!r} has no status" for c in cl if not c["status"]]
    if n_oracle and (o["claims_checked"] < n_oracle or o["claims_passed"] < o["claims_checked"]):
        p2.append("checked_by_oracle claims not all re-run and passed")
    kws = [_fold(k) for k in briefing_keywords]
    for c in cl:
        low = _fold(c["text"] + "\n" + c["evidence"])
        if c["status"] != "from_briefing_unverified" and any(k in low for k in kws):
            p2.append(f"claim {c['id']!r} carries a briefing keyword without from_briefing_unverified")
    cover = "\n".join(_fold(c["text"] + "\n" + c["evidence"]) for c in cl
                       if c["status"] == "from_briefing_unverified")
    p2 += [f"statement carries briefing keyword {k!r} not covered by a from_briefing_unverified claim"
           for k in kws if k in _fold(card["statement"]) and k not in cover]
    g["G2_unverified_as_fact"] = "fail" if p2 else "pass"
    why += [f"G2: {x}" for x in p2]

    texts = [card["statement"]] + [t for c in cl for t in (c["text"], c["evidence"])] + [v["evidence"] for v in card["criteria"].values()]
    hit = any(p.search(_nfkc(t)) for p in pats for t in texts)
    flag = card["reviewer"]["overclaim_flag"]
    g["G3_overclaim"] = "fail" if hit or flag else "pass"
    if hit:
        why.append("G3: sealed overclaim pattern matched")
    if flag:
        why.append("G3: reviewer flagged overclaim")

    ok4 = card["model_of_computation"] in MODELS and card["input_parameter"] in PARAMS
    g["G4_model_parameter"] = "pass" if ok4 else "fail"
    if not ok4:
        why.append("G4: model_of_computation or input_parameter empty or outside the vocabulary")

    sep = card["separations"]
    if ct == "finite_lemma":
        g["G5_separation"] = "na"
    elif _text(sep["asymptotic_vs_practical"]) and _text(sep["worst_vs_average_case"]):
        g["G5_separation"] = "pass"
    else:
        g["G5_separation"] = "fail"
        why.append("G5: a separations field is empty")

    d = card["definition_audit"]
    if ct != "formal_statement":
        g["G6_definition_audit"] = "na"
    elif d["done"] is True and d["faithful"] is True:
        g["G6_definition_audit"] = "pass"
    else:
        g["G6_definition_audit"] = "fail"
        why.append("G6: formal_statement without a done and faithful definition audit")
    return g, why


def score(card, *, weights, briefing_keywords, overclaim_patterns):
    """Validate, recompute gates and total. Never reads or changes performance_row.pass.

    Invalid card: valid False, gates and weighted_total None, disqualified True, reasons = errors.
    A disqualified card with verdict advance is invalid (errors) but keeps its gates and zero total.
    `declared_mismatch` lists declared fields that differ from the recomputation (not a disqualifier).
    """
    errs = validate(card, weights=weights)
    if errs:
        return {"valid": False, "errors": errs, "gates": None, "weighted_total": None, "disqualified": True,
                "reasons": errs, "declared_mismatch": []}
    g, why = gates(card, briefing_keywords=briefing_keywords, overclaim_patterns=overclaim_patterns)
    # validate() proved the card weights equal the frozen ones; the total uses the frozen ones
    raw = 100 * math.fsum(weights[k] * card["criteria"][k]["score"] for k in CRITERIA) / 5
    dq = "fail" in g.values()
    total = 0.0 if dq else raw
    mism = [k for k in GATES if card["hard_gates"][k] != g[k]]
    if not math.isclose(card["weighted_total"], total, rel_tol=0, abs_tol=1e-9):
        mism.append("weighted_total")
    if card["disqualified"] != dq:
        mism.append("disqualified")
    errs = ["verdict: advance is not allowed on a disqualified card"] if dq and card["verdict"] == "advance" else []
    return {"valid": not errs, "errors": errs, "gates": g, "weighted_total": total, "disqualified": dq, "reasons": why,
            "declared_mismatch": mism}
