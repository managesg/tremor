"""R6 Stage A (R3 of prereg/R6-pvsnp-research-line-plan.md): the pinned R5 estimators on R6-type tasks, with
scripted agents that carry PLANTED values. Offline: no network, model call, GPU or key. Standard library plus the
pinned harness (lab/r5_perf_harness.py at d0c67d7, imported, never edited), M1 (lab/r6_pvsnp_tasks.py), the
lemma checker (lab/r6_predicates.py) and the scorecard (lab/r6_scorecard.py).

Instrument validation only: nothing here is evidence about models or about P vs NP.

Pass is the family oracle's verdict alone (`oracle_f2`, `oracle_f3`, `oracle_f5`), computed from the agent's
CLAIM; the planted draws only choose which claim the scripted agent makes. Gate failures never touch pass.
No default for any open parameter: every config key is required and unknown keys are refused.

Planted models (names as in the harness):
- H2: per episode, with probability c every agent fails, else each fails with q = 1 - pass_p[difficulty]. One
  difficulty per family run, so one pooled (q, c) is the target. Recovered iff the planted (q, c) lies in the
  likelihood-ratio region of the fit: 2 (ll_hat - ll_planted) <= chi2_2(1 - alpha), which is -2 ln(alpha) in closed form.
- H3: agent pass probability p_arm; stated confidence = p_arm + bias_arm + uniform(-0.1, 0.1); planted dG =
  bias_team - bias_solo (exact, no clipping allowed). Behaviour check: planted pass-rate difference = ask_effect.
- H5: hidden state per episode, failure rate f (1 +- spread) with probability 1/2; a failing candidate is flagged
  with probability 1 - a (a = false-clean rate). Planted S has the closed form `h5_planted_S`; a is checked with an
  exact Clopper-Pearson interval on the calibration split's failing candidates.
- RT (plan section 3): proposer a0 and responder a1 per lemma and arm. The proposer's label is the same in both arms
  (keyed by lemma): a false lemma is accepted with probability A. The responder supplies a verified counterexample
  with probability f_arm (treatment = Red Team role, control = solver); the label stands unless a counterexample
  verifies. Planted difference in the share of false lemmas still accepted = A (f_control - f_treatment). Exact
  within-lemma permutation null = exact McNemar (binomial on the discordant lemmas). Also reported: verified-refutation
  recall and the unverified-counterexample rate on true lemmas, with Clopper-Pearson intervals.
- F6 Definition Audit (plan section 4): auditors flag a defective pair with probability `detect` and a faithful pair with
  probability `false_alarm`; a flag carries the exact span with probability `locate`, else a uniformly random span (the
  null of exact-span scoring: chance 1 / (L (L + 1) / 2) for a text of length L). Rates with exact intervals, no test.
Deferred, with the reason: H1 (plan Part II section 2 leaves it with R5; plan section R3 does not name it), F1 (SAT
checker, not in the R3 row of plan section 7) and F4 (resolution checker "not built", protocol draft), so Stage A has
no scripted agent for them. Not done: the Holm family over H3, H5, RT (a separate module in the protocol draft).
"""
import hashlib
import math
import random
from functools import lru_cache

from tremor import team
from tremor.adopters import ScriptedAdopter

from lab import r5_perf_harness as h
from lab import r6_predicates as pr
from lab import r6_pvsnp_tasks as m1
from lab import r6_scorecard as sc
from lab.l3c_harness import task_seed

FAMILIES = ("F2", "F3", "F5")
GRID = h.PLAN_GRID
OPS = tuple(range(16))


# ------------------------------------------------------------------------------------------ validation ----

def _need(cfg, keys, name):
    if not isinstance(cfg, dict) or set(cfg) != set(keys):
        raise ValueError(f"{name} must be a dict with exactly the keys {sorted(keys)}")
    return cfg


def _int(x, name, lo, hi=10**9):
    if isinstance(x, bool) or not isinstance(x, int) or not lo <= x <= hi:
        raise ValueError(f"{name} must be an integer in [{lo}, {hi}]")
    return x


def _p(x, name, open_lo=False, open_hi=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0 <= x <= 1 \
            or (open_lo and x == 0) or (open_hi and x == 1):
        raise ValueError(f"{name} must be a probability" + (" strictly inside (0, 1)" if open_lo or open_hi else ""))
    return x


# ------------------------------------------------------------------------------------- circuits and M1 ----

@lru_cache(maxsize=None)
def _m1_sizes(n):
    return m1.min_circuit_size(n)


def circuit_table(n, circ):
    """Truth table of circ = {"gates": [[op, i, j], ...], "out": k, "neg": bool}; op is a 4-bit two-input function
    (bit 2u+v is the value at inputs u, v); i, j index the inputs then the earlier gates. ValueError if malformed."""
    if not isinstance(circ, dict) or set(circ) != {"gates", "out", "neg"} or not isinstance(circ["gates"], list):
        raise ValueError("circuit must be {gates, out, neg}")
    full = (1 << (1 << n)) - 1
    sig = [m1.var_table(n, j) for j in range(n)]
    for g in circ["gates"]:
        if not isinstance(g, (list, tuple)) or len(g) != 3 or any(type(v) is not int for v in g):
            raise ValueError("gate must be [op, i, j]")
        op, i, j = g
        if not 0 <= op < 16 or not (0 <= i < len(sig) and 0 <= j < len(sig)):
            raise ValueError("gate out of range")
        a, b, t = sig[i], sig[j], 0
        for k in range(4):
            if (op >> k) & 1:
                t |= (a if k >> 1 else full ^ a) & (b if k & 1 else full ^ b)
        sig.append(t)
    if type(circ["out"]) is not int or not 0 <= circ["out"] < len(sig) or type(circ["neg"]) is not bool:
        raise ValueError("bad output")
    return sig[circ["out"]] ^ (full if circ["neg"] else 0)


@lru_cache(maxsize=None)
def _synth_table(n):
    """normalised table -> shortest gate list over AND (any input polarity) / XOR, by exhaustive DFS.
    shortcut: exhaustive, so n <= 3 only (4 gates); n = 4 needs 7 gates, too slow, use a stronger synthesizer then."""
    if n > 3:
        raise ValueError("the scripted agents' circuit synthesizer supports n <= 3")
    full = (1 << (1 << n)) - 1
    inputs = [m1.var_table(n, j) for j in range(n)]
    depth = max(_m1_sizes(n).values())
    best = {}

    def rec(sig, gates):
        if len(gates) == depth:
            return
        for i in range(len(sig)):
            for j in range(i + 1, len(sig)):
                a, b = sig[i], sig[j]
                for pa in (0, 1):
                    for pb in (0, 1):
                        for xor in ((0, 1) if not (pa or pb) else (0,)):
                            t = (a ^ b) if xor else ((full ^ a if pa else a) & (full ^ b if pb else b))
                            t = full ^ t if t & 1 else t
                            if t == 0 or t in sig:
                                continue
                            g = gates + ((xor, pa, pb, i, j),)
                            if t not in best or len(best[t]) > len(g):
                                best[t] = g
                            rec(sig + [t], g)

    rec(inputs, ())
    return best


def synth(n, f):
    """A minimum-size circuit for truth table f (n <= 3), in the circuit_table layout."""
    full = (1 << (1 << n)) - 1
    if f in (0, full):
        return {"gates": [[6, 0, 0]], "out": n, "neg": f == full}  # x XOR x, one gate by the M1 convention
    for j in range(n):
        v = m1.var_table(n, j)
        if f in (v, full ^ v):
            return {"gates": [], "out": j, "neg": f != v}
    key = full ^ f if f & 1 else f
    gates, sig = [], [m1.var_table(n, j) for j in range(n)]
    for xor, pa, pb, i, j in _synth_table(n)[key]:
        a, b = sig[i], sig[j]
        t = (a ^ b) if xor else ((full ^ a if pa else a) & (full ^ b if pb else b))
        flip = 0 if xor else pa & pb  # stored signals are normalised: bit 0 is 0
        op = 0
        for u in (0, 1):
            for v in (0, 1):
                val = (u ^ v) if xor else ((u ^ pa) & (v ^ pb))
                op |= (val ^ flip) << (2 * u + v)
        gates.append([op, i, j])
        sig.append(full ^ t if t & 1 else t)
    return {"gates": gates, "out": n + len(gates) - 1, "neg": sig[-1] != f}


# ----------------------------------------------------------------------------------------- oracles ----

def oracle_f2(task, claim):
    """F2: the circuit evaluates to f on every input and its gate count, equal to the claimed size, is the M1 minimum."""
    try:
        n, f = task["n"], task["f"]
        ok = circuit_table(n, claim["circuit"]) == f and type(claim["size"]) is int
        return int(ok and claim["size"] == len(claim["circuit"]["gates"]) == _m1_sizes(n)[f])
    except (ValueError, TypeError, KeyError):
        return 0


def oracle_f3(task, claim):
    """F3: the yes/no answer matches M1 (yes iff min size <= s); a yes must carry a circuit for f with at most s gates."""
    try:
        n, f, s = task["n"], task["f"], task["s"]
        truth = _m1_sizes(n)[f] <= s
        if claim["answer"] not in ("yes", "no") or (claim["answer"] == "yes") != truth:
            return 0
        if not truth:
            return 1
        return int(circuit_table(n, claim["circuit"]) == f and len(claim["circuit"]["gates"]) <= s)
    except (ValueError, TypeError, KeyError):
        return 0


def _domain(width):
    return ({"x": x, "y": y} for x in range(1 << width) for y in range(1 << width))


def oracle_f5(task, claim):
    """F5: the label matches the exhaustive run of the predicate over the declared domain; a 'false' label must carry a
    counterexample from that domain on which the predicate (re-run here) is False."""
    try:
        pr.parse(task["source"])
        if type(claim["label"]) is not bool or claim["label"] != task["truth"]:
            return 0
        if claim["label"]:
            return 1
        return int(counterexample_verifies(task, claim["counterexample"]))
    except (pr.PredicateRefused, TypeError, KeyError):
        return 0


def counterexample_verifies(task, env):
    """True iff env is a point of the declared domain on which the predicate (re-run here) is False."""
    w = task["width"]
    if not isinstance(env, dict) or set(env) != {"x", "y"} or any(
            type(env[k]) is not int or not 0 <= env[k] < (1 << w) for k in env):
        return False
    try:
        return pr.parse(task["source"]).run(env, task["step_limit"])[0] is False
    except pr.PredicateRefused:
        return False


ORACLES = {"F2": oracle_f2, "F3": oracle_f3, "F5": oracle_f5}


# ------------------------------------------------------------------------------------ task generators ----

def gen_circuit_tasks(family, n, difficulty, count, seed, tag, yes_rate=None):
    """F2/F3 tasks on n-input truth tables whose M1 minimum size is `difficulty`. F3 also needs yes_rate: a yes task has
    s = min size, a no task s = min size - 1 (the boundary). Ground truth is the M1 table alone."""
    if family not in ("F2", "F3"):
        raise ValueError("family must be F2 or F3")
    _int(n, "n", 1, 4), _int(count, "count", 1, 10**5), _int(difficulty, "difficulty", 0, 7)
    pool = sorted(f for f, v in _m1_sizes(n).items() if v == difficulty)
    if not pool:
        raise ValueError("no truth table has that M1 size")
    if family == "F3":
        _p(yes_rate, "yes_rate")
        if difficulty == 0 and yes_rate < 1:
            raise ValueError("a no task needs min size >= 1")
    elif yes_rate is not None:
        raise ValueError("yes_rate belongs to F3")
    rng = random.Random(task_seed(f"gen-{family}:{tag}", seed, 0))
    out = []
    for i in range(count):
        t = {"family": family, "difficulty": difficulty, "n": n, "f": pool[rng.randrange(len(pool))]}
        if family == "F3":
            t["s"] = difficulty if rng.random() < yes_rate else difficulty - 1
        out.append(t)
    return out


TEMPLATES = ("popcount(x & y) <= min(popcount(x), popcount(y)) + {k}",
             "popcount(x | y) + popcount(x & y) == popcount(x) + popcount(y) + {k}",
             "popcount(x ^ y) <= popcount(x) + popcount(y) - {k}")
KS = (-2, -1, 0, 1, 2)


def lemma_truth(source, width, step_limit, total_steps):
    """(truth, counterexample) from the exhaustive predicate run over x, y in range(2**width)."""
    cx = pr.check_lemma(pr.parse(source), _domain(width), step_limit, total_steps)
    return cx is None, cx


def gen_lemma_tasks(width, count, false_rate, seed, tag, step_limit, total_steps):
    """F5 tasks: a template and k drawn at random, kept only when the exhaustive run gives the planted label
    (false with probability false_rate). Difficulty = width. Ground truth comes from check_lemma, not from the template."""
    _int(width, "width", 1, 5), _int(count, "count", 1, 10**5), _p(false_rate, "false_rate")
    rng = random.Random(task_seed(f"gen-F5:{tag}", seed, 0))
    out = []
    for _ in range(count):
        want_false = rng.random() < false_rate
        for _try in range(1000):
            src = TEMPLATES[rng.randrange(len(TEMPLATES))].format(k=KS[rng.randrange(len(KS))])
            truth, cx = lemma_truth(src, width, step_limit, total_steps)
            if truth != want_false:
                out.append({"family": "F5", "difficulty": width, "width": width, "source": src, "truth": truth,
                            "counterexample": cx, "step_limit": step_limit, "total_steps": total_steps})
                break
        else:
            raise ValueError("no lemma with the planted label found")
    return out


# -------------------------------------------------------------------------------------- scripted claims ----

def right_claim(task):
    """What an agent that solves the task submits (built from M1 and the synthesizer, or the exhaustive run)."""
    fam = task["family"]
    if fam == "F2":
        c = synth(task["n"], task["f"])
        return {"circuit": c, "size": len(c["gates"])}
    if fam == "F3":
        if _m1_sizes(task["n"])[task["f"]] <= task["s"]:
            return {"answer": "yes", "circuit": synth(task["n"], task["f"])}
        return {"answer": "no"}
    return {"label": task["truth"], "counterexample": task["counterexample"]}


def wrong_claim(task, rng):
    """A claim that fails its oracle by construction (tests assert it does): wrong size, negated output, flipped answer
    or label, a bogus counterexample."""
    fam, mode = task["family"], rng.randrange(2)
    if fam == "F2":
        c = synth(task["n"], task["f"])
        if mode:
            return {"circuit": dict(c, neg=not c["neg"]), "size": len(c["gates"])}
        return {"circuit": c, "size": len(c["gates"]) + (1 if rng.randrange(2) else -1)}
    if fam == "F3":
        if _m1_sizes(task["n"])[task["f"]] <= task["s"]:
            return {"answer": "no"} if mode else {"answer": "yes", "circuit": dict(synth(task["n"], task["f"]), neg=not synth(task["n"], task["f"])["neg"])}
        return {"answer": "yes", "circuit": synth(task["n"], task["f"])}  # one gate over s: too big
    if task["truth"]:
        return {"label": False, "counterexample": {"x": 0, "y": 0}}  # a true lemma has no counterexample
    return {"label": True, "counterexample": None} if mode else {"label": False, "counterexample": None}


class R6Agent(ScriptedAdopter):
    """Blind scripted agent: its one work event answers expect when the oracle passes its claim, expect + 1 when not.
    fail_p: this episode's failure probability (the planted model); flag_miss a (None = no view flags);
    conf = (centre, bias) or None. Records every claim, verdict, flag and confidence in .rec[agent]."""

    def __init__(self, seed, task, fail_p, flag_miss, conf):
        super().__init__(1.0, seed)
        self.task, self.fail_p, self.flag_miss, self.conf, self.rec = task, fail_p, flag_miss, conf, {}

    def claim_for(self, a):
        """(claim, planted_fail): the planted draws only choose which claim is made."""
        fails = random.Random(f"fail:{self.seed}:{a}").random() < self.fail_p
        return (wrong_claim(self.task, random.Random(f"mode:{self.seed}:{a}")) if fails else right_claim(self.task)), fails

    def turn(self, ctx):
        out = []
        for e in super().turn(ctx):
            if e["type"] == "work":
                a = ctx.agent
                claim, fails = self.claim_for(a)
                ok = ORACLES[self.task["family"]](self.task, claim)
                if fails is None:
                    fails = not ok
                rec = {"claim": claim, "pass": ok, "planted_fail": fails, "flag": None, "conf": None}
                if self.flag_miss is not None:  # a failing candidate is flagged with probability 1 - a; a passing one never
                    rec["flag"] = int(not ok and random.Random(f"flag:{self.seed}:{a}").random() >= self.flag_miss)
                if self.conf is not None:
                    centre, bias = self.conf
                    rec["conf"] = centre + bias + (random.Random(f"conf:{self.seed}:{a}").random() - 0.5) * 0.2
                self.rec[a] = rec
                e = dict(e, answer=ctx.tasks[e["task"]]["expect"] + (0 if ok else 1))
            out.append(e)
        return out


def _taskset(tasks):
    def f(n, t):
        return {"split": "r6", "seed": t, "n_agents": n, "name_rule": "{agent}-{task}",
                "tasks": [{"id": f"t{t}x{i}", "check": f"r6 {tasks[t]['family']} {t}", "expect": 1} for i in range(n)]}
    return f


def play(tasks, sizes, reruns, seed, tag, plant, flag_miss=None, conf=None, make=None):
    """Run every (size, task, rerun) episode through h.run_arms and the real team.run_episode. tasks: {id: task};
    plant(ep_seed, task) -> the episode's failure probability; conf is a (centre, bias) pair or None; make(ep_seed,
    task), when given, builds the agent instead (RT and F6).
    Returns (per-agent rows in the H2 layout, {(n, task, rerun): agent}). Refuses a row whose pass differs from the oracle."""
    agents = {}

    def kw(arm, n, t, r, ep_seed):
        agents[(n, t, r)] = (make(ep_seed, tasks[t]) if make else
                             R6Agent(ep_seed, tasks[t], plant(ep_seed, tasks[t]), flag_miss, conf))
        return {"adopter": agents[(n, t, r)]}

    rows = h.run_arms(team.run_episode, _taskset(tasks), arms=["none"], sizes=sizes, task_ids=list(tasks),
                      reruns=reruns, practice="A", seed=seed, tag=tag, episode_kw=kw)["none"]
    for r in rows:
        rec = agents[(r["n"], r["task"], r["rerun"])].rec.get(f"a{r['agent']}")
        if rec is None or rec["pass"] != r["pass"]:
            raise ValueError("a row's pass differs from the oracle verdict on the recorded claim")
    return rows, agents


def play_solo(tasks, reruns, seed, tag, plant, conf):
    """n = 1 episodes: run_arms refuses sizes below 2, so this calls team.run_episode directly with the seed
    derivation run_arms uses (ADVISOR QUESTION 1). Rows carry n = 1."""
    rows = []
    for t in tasks:
        for r in range(reruns):
            ep_seed = task_seed(f"{tag}:none:1", seed, h._int(t, "task", 0, 10**6) * 10**6 + r)
            ag = R6Agent(ep_seed, tasks[t], plant(ep_seed, tasks[t]), None, conf)
            ts = _taskset(tasks)(1, t)
            rec = team.run_episode(ts, "none", "A", n_agents=1, seed=ep_seed, adopter=ag)
            (p,) = h.agent_passes(rec, ts)
            if ag.rec["a0"]["pass"] != p:
                raise ValueError("a row's pass differs from the oracle verdict on the recorded claim")
            rows.append({"n": 1, "task": t, "rerun": r, "agent": 0, "pass": p, "seed": seed, "conf": ag.rec["a0"]["conf"]})
    return rows


# ------------------------------------------------------------------------------------------ helpers ----

def make_tasks(family, design, seed, tag, first_id, difficulties=None):
    """{task id: task}: design["tasks"] tasks of the family's planted difficulty (split evenly over `difficulties`
    when a plant mixes several, e.g. to show that spread between tasks is not read as a shared cause)."""
    ds = [design["difficulty"][family]] if difficulties is None else list(difficulties)
    if design["tasks"] % len(ds):
        raise ValueError("tasks must divide evenly over the difficulties")
    count, out = design["tasks"] // len(ds), {}
    for k, d in enumerate(ds):
        if family == "F5":
            ts = gen_lemma_tasks(d, count, design["false_rate"], seed, f"{tag}-{k}", design["step_limit"], design["total_steps"])
        else:
            ts = gen_circuit_tasks(family, design["n_vars"], d, count, seed, f"{tag}-{k}", design["yes_rate"] if family == "F3" else None)
        out.update({first_id + k * count + i: t for i, t in enumerate(ts)})
    return out


def _pmf_bin(i, m, p):
    if p in (0, 1):
        return float(i == (m if p else 0))
    return math.exp(math.lgamma(m + 1) - math.lgamma(i + 1) - math.lgamma(m - i + 1)
                    + i * math.log(p) + (m - i) * math.log1p(-p))


def tail_ge(k, m, p):
    """P(Binomial(m, p) >= k), exact pmf sum."""
    return math.fsum(_pmf_bin(i, m, p) for i in range(k, m + 1))


def clopper_pearson(k, m, level):
    """Exact two-sided interval for a binomial proportion (bisection on the exact tails)."""
    h._level(level, "level")
    a = (1 - level) / 2

    def solve(f):  # f increasing in p; root of f(p) = a
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if f(mid) >= a else (mid, hi)
        return (lo + hi) / 2

    lo = 0.0 if k == 0 else solve(lambda p: tail_ge(k, m, p))
    hi = 1.0 if k == m else 1 - solve(lambda r: tail_ge(m - k, m, r))
    return lo, hi


def _ll(counts, q, c):
    s = 0.0
    for n, cnt in counts.items():
        pm = h.pmf(n, q, c)
        for k, x in enumerate(cnt):
            if x:
                s += -math.inf if pm[k] <= 0 else x * math.log(pm[k])
    return s


def lr_region(counts, planted_q, planted_c, alpha, fit, step):
    """Likelihood-ratio region of (q, c) at level 1 - alpha: 2 (ll_hat - ll) <= chi2_2(1 - alpha) = -2 ln(alpha), a
    closed form for 2 degrees of freedom. Evaluated on a grid of the given step (the reported interval is the grid's
    projection; the planted point is tested exactly). Returns (recovered, delta, threshold, q interval, c interval)."""
    h._level(alpha, "alpha_recover")
    _int(step, "grid_steps", 10, 1000)
    thr = -math.log(alpha)
    pts = [(i / step, j / step) for i in range(step + 1) for j in range(step + 1)]
    lls = {pt: _ll(counts, *pt) for pt in pts}
    hat = max(_ll(counts, fit["q"], fit["c"]), max(lls.values()))
    delta = hat - _ll(counts, planted_q, planted_c)
    inside = [pt for pt in pts if hat - lls[pt] <= thr]
    if delta <= thr:
        inside.append((planted_q, planted_c))
    qs, cs = [p[0] for p in inside], [p[1] for p in inside]
    return delta <= thr, delta, thr, (min(qs), max(qs)), (min(cs), max(cs))


def in_interval(x, interval):
    return interval[0] <= x <= interval[1]


# ------------------------------------------------------------------------------------------------ H2 ----

def run_h2(family, seed, design, plant, est, difficulties=None):
    """H2 on one family at one difficulty: fit sizes 2 and 4, forecast size 8, planted (q, c) from plant."""
    mixed = difficulties is not None and len(set(difficulties)) > 1
    d = design["difficulty"][family] if difficulties is None else difficulties[0]
    q, c = 1 - plant["pass_p"][d], plant["c"]
    pl = lambda s, t: 1.0 if random.Random(f"common:{s}").random() < c else 1 - plant["pass_p"][t["difficulty"]]  # noqa: E731
    fit_t = make_tasks(family, design, seed, "h2fit", 0, difficulties)
    held_t = make_tasks(family, design, seed, "h2held", 1000, difficulties)
    fit_rows, fit_ag = play(fit_t, [2, 4], design["reruns"], 2 * seed, f"h2fit-{family}", pl)
    held_rows, held_ag = play(held_t, [8], design["reruns"], 2 * seed + 1, f"h2held-{family}", pl)
    res = h.h2_primary(fit_rows, held_rows, fit_sizes=[2, 4], target_n=8, level=est["level"], alpha=est["alpha"],
                       B=est["B"], seed=seed, edge=est["edge"])
    ep = h.episode_counts(fit_rows)
    counts = {n: [0] * (n + 1) for n in (2, 4)}
    for (n, _t, _r), x in ep.items():
        counts[n][x] += 1
    ok, delta, thr, qi, ci = lr_region(counts, q, c, est["alpha_recover"], res["fit"], est["grid_steps"])
    if mixed:  # no single planted q: only the decision and the fit are meaningful
        ok, q = None, None
    return {"estimate": {"q": res["fit"]["q"], "c": res["fit"]["c"]}, "interval": {"q": qi, "c": ci},
            "planted": {"q": q, "c": c}, "recovered": ok, "delta": delta, "threshold": thr,
            "decision": res["decision"], "harness": res,
            "runs": [(fit_t, fit_rows, fit_ag), (held_t, held_rows, held_ag)]}


# ------------------------------------------------------------------------------------------------ H3 ----

def run_h3(family, seed, design, plant, est):
    """H3 and its behaviour check. Planted dG = bias_team - bias_solo; planted behaviour difference = ask_effect."""
    d = design["difficulty"][family]
    p0, eff, bt, bs = plant["pass_p"][d], plant["ask_effect"], plant["conf_bias"]["team"], plant["conf_bias"]["solo"]
    p_with = p0 + eff
    _p(p_with, "pass probability with the confidence field")
    for b in (bt, bs):
        if p_with + b - 0.1 < 0 or p_with + b + 0.1 > 1:
            raise ValueError("confidence would clip: the planted bias must not be altered by clipping")
    tasks = make_tasks(family, design, seed, "h3", 0)
    team_rows, ag = play(tasks, [4], design["reruns"], 3 * seed, f"h3team-{family}", lambda s, t: 1 - p_with,
                         conf=(p_with, bt))
    none_rows, _ = play(tasks, [4], design["reruns"], 3 * seed + 1, f"h3none-{family}", lambda s, t: 1 - p0)
    solo = play_solo(tasks, 4 * design["reruns"], 3 * seed + 2, f"h3solo-{family}", lambda s, t: 1 - p_with, (p_with, bs))
    rows = ([{"arm": "team", "task": r["task"], "pass": r["pass"],
              "conf": ag[(r["n"], r["task"], r["rerun"])].rec[f"a{r['agent']}"]["conf"]} for r in team_rows]
            + [{"arm": "solo", "task": r["task"], "pass": r["pass"], "conf": r["conf"]} for r in solo])
    res = h.h3_primary(rows, team_arm="team", solo_arm="solo", B=est["B"], perms=est["perms"], seed=seed,
                       level=est["level"], edge=est["edge"], max_unparseable=est["max_unparseable"])
    beh = h.behaviour_check([{"arm": "team", "task": r["task"], "pass": r["pass"]} for r in team_rows]
                            + [{"arm": "none", "task": r["task"], "pass": r["pass"]} for r in none_rows],
                            with_arm="team", without_arm="none", B=est["B"], seed=seed, level=est["level"])
    planted = bt - bs
    return {"estimate": res["delta_g"], "interval": res["interval"], "planted": planted,
            "recovered": in_interval(planted, res["interval"]), "decision": res["decision"], "harness": res, "rows": rows,
            "behaviour": {"estimate": beh["diff"], "interval": beh["interval"], "planted": eff,
                          "recovered": in_interval(eff, beh["interval"])}}


# ------------------------------------------------------------------------------------------------ H5 ----

def h5_planted_S(f, a, spread, grid=GRID):
    """S under the hidden-state model: mean over N of [1/2 (u(1 + s))^N + 1/2 (u(1 - s))^N - u^N], u = f (1 - a).
    Exactly 0 at spread 0 (independent draws)."""
    u = f * (1 - a)
    return math.fsum(0.5 * (u * (1 + spread)) ** n + 0.5 * (u * (1 - spread)) ** n - u ** n for n in grid) / len(grid)


def _episodes(rows, agents, offset):
    by = {}
    for r in rows:
        by.setdefault((r["task"], r["rerun"]), []).append(r)
    return [{"task": t, "episode": k + offset,
             "cands": [{"flags": agents[(16, t, k)].rec[f"a{r['agent']}"]["flag"], "fails": 1 - r["pass"]}
                       for r in sorted(g, key=lambda r: r["agent"])]}
            for (t, k), g in sorted(by.items())]


def run_h5(family, seed, design, plant, est):
    """H5 at the registered grid [2, 4, 8, 16]: calibration and scored episodes are separate runs of 16 candidates."""
    f, a, s = plant["f"], plant["false_clean"], plant["spread"]
    _p(f, "f"), _p(a, "false_clean"), _p(s, "spread")
    if f * (1 + s) > 1:
        raise ValueError("f (1 + spread) must not exceed 1")
    pl = lambda ep, t: f * (1 + s) if random.Random(f"state:{ep}").random() < 0.5 else f * (1 - s)  # noqa: E731
    d = dict(design, tasks=design["h5_tasks"])
    tasks = make_tasks(family, d, seed, "h5", 0)
    cal_rows, cal_ag = play(tasks, [16], design["cal_reruns"], 4 * seed, f"h5cal-{family}", pl, flag_miss=a)
    sc_rows, sc_ag = play(tasks, [16], design["h5_reruns"], 4 * seed + 1, f"h5sc-{family}", pl, flag_miss=a)
    cal, scored = _episodes(cal_rows, cal_ag, 0), _episodes(sc_rows, sc_ag, 10**5)
    res = h.h5_primary(cal, scored, grid=list(GRID), B=est["B"], perms=est["perms"], seed=seed, level=est["level"],
                       K=est["K"], negligible=est["negligible"], min_clean=h.MIN_CLEAN, min_fail=h.MIN_FAIL)
    planted = h5_planted_S(f, a, s)
    failing = [c for e in cal for c in e["cands"] if c["fails"]]
    miss = sum(c["flags"] == 0 for c in failing)
    ci = clopper_pearson(miss, len(failing), est["level"])
    return {"estimate": res["S"], "interval": res["interval"], "planted": planted,
            "recovered": in_interval(planted, res["interval"]), "decision": res["decision"], "harness": res,
            "episodes": (cal, scored), "false_clean": {"estimate": miss / len(failing), "interval": ci, "planted": a,
                            "recovered": in_interval(a, ci), "failing_candidates": len(failing)}}


# ------------------------------------------------------------------------------------------------ RT ----

ARMS_RT = ("treatment", "control")


class RTAgent(R6Agent):
    """a0 = proposer, a1 = responder, on one F5 lemma. The proposer's label depends on the lemma alone (u, drawn once
    per lemma, so both arms see the same proposer); the responder's draws are keyed by the episode seed.
    rt = {"accept_false", "reject_true", "find", "bogus"}; find / bogus are this arm's responder rates."""

    def __init__(self, seed, task, rt, u):
        super().__init__(seed, task, 0.0, None, None)
        self.rt, self.u = rt, u

    def proposer_claim(self):
        t = self.task
        if t["truth"]:
            return ({"label": False, "counterexample": {"x": 0, "y": 0}} if self.u < self.rt["reject_true"]
                    else {"label": True, "counterexample": None})
        return ({"label": True, "counterexample": None} if self.u < self.rt["accept_false"] else right_claim(t))

    def claim_for(self, a):
        prop = self.proposer_claim()
        if a == "a0":
            return prop, None
        if not prop["label"]:
            return (right_claim(self.task) if not self.task["truth"] else {"label": True, "counterexample": None}), None
        r = random.Random(f"resp:{self.seed}").random()
        if self.task["truth"]:  # a counterexample to a true lemma can never verify
            return ({"label": False, "counterexample": {"x": 0, "y": 0}} if r < self.rt["bogus"]
                    else {"label": True, "counterexample": None}), None
        return (right_claim(self.task) if r < self.rt["find"] else {"label": True, "counterexample": None}), None


def rt_outcome(task, proposer, responder):
    """Override rule, one for both arms: the proposer's label stands unless the responder supplies a counterexample that
    the checker verifies. Returns (accepted, verified_refutation, unverified_counterexample)."""
    cx = responder["label"] is False and responder["counterexample"] is not None
    ok = cx and counterexample_verifies(task, responder["counterexample"])
    return int(proposer["label"] is True and not ok), int(bool(ok)), int(bool(cx) and not ok)


def rt_exact_p(x, y):
    """One-sided exact McNemar toward treatment < control: x lemmas accepted only in control, y only in treatment.
    P(Binomial(x + y, 1/2) >= x); 1 when there are no discordant lemmas."""
    k = x + y
    return math.fsum(math.comb(k, i) for i in range(x, k + 1)) / 2 ** k


def rt_permutation_null(diffs, perms, seed):
    """Sum of the paired differences with arm labels swapped independently within each lemma (a swap negates d)."""
    rng = random.Random(task_seed("rt-null", seed, 0))
    return [sum(d if rng.random() < 0.5 else -d for d in diffs) for _ in range(perms)]


def _cp(k, m, level):
    return clopper_pearson(k, m, level) if m else (0.0, 1.0)


def run_rt(seed, design, plant, est):
    """RT: the share of false lemmas still accepted, treatment minus control, paired by lemma."""
    rt = plant["rt"]
    d = design["difficulty"]["F5"]
    tasks = {i: t for i, t in enumerate(gen_lemma_tasks(d, design["rt_lemmas"], design["false_rate"], seed, "rt",
                                                        design["step_limit"], design["total_steps"]))}
    us = {i: random.Random(task_seed("rt-prop", seed, i)).random() for i in tasks}
    by_src = {id(t): i for i, t in tasks.items()}
    arms, rec = {}, {}
    for k, arm in enumerate(ARMS_RT):
        rates = dict(accept_false=rt["accept_false"], reject_true=rt["reject_true"], find=rt["find"][arm],
                     bogus=rt["bogus"][arm])
        rows, ag = play(tasks, [2], 1, 5 * seed + k, f"rt-{arm}", None,
                        make=lambda ep, t, rates=rates: RTAgent(ep, t, rates, us[by_src[id(t)]]))
        arms[arm] = rows
        rec[arm] = {i: ag[(2, i, 0)] for i in tasks}
    out = {a: {i: rt_outcome(tasks[i], ag.rec["a0"]["claim"], ag.rec["a1"]["claim"]) for i, ag in rec[a].items()}
           for a in ARMS_RT}
    false_ids = [i for i, t in tasks.items() if not t["truth"]]
    true_ids = [i for i, t in tasks.items() if t["truth"]]
    diffs = [out["treatment"][i][0] - out["control"][i][0] for i in false_ids]
    if not diffs:
        raise ValueError("no false lemma drawn")
    x = sum(dv == -1 for dv in diffs)   # accepted only in control
    y = sum(dv == 1 for dv in diffs)    # accepted only in treatment
    planted = rt["accept_false"] * (rt["find"]["control"] - rt["find"]["treatment"])
    interval = h._boot(diffs, h._mean, est["B"], seed, est["level"], "rt-boot")
    prop_acc = [i for i in false_ids if rec["control"][i].rec["a0"]["claim"]["label"] is True]
    true_acc = [i for i in true_ids if rec["control"][i].rec["a0"]["claim"]["label"] is True]
    per_arm = {}
    for arm in ARMS_RT:
        hit = sum(out[arm][i][1] for i in prop_acc)
        bog = sum(out[arm][i][2] for i in true_acc)
        per_arm[arm] = {
            "recall": {"estimate": hit / len(prop_acc) if prop_acc else None,
                       "interval": _cp(hit, len(prop_acc), est["level"]), "planted": rt["find"][arm], "n": len(prop_acc)},
            "unverified": {"estimate": bog / len(true_acc) if true_acc else None,
                           "interval": _cp(bog, len(true_acc), est["level"]), "planted": rt["bogus"][arm],
                           "n": len(true_acc)},
            "accepted": sum(out[arm][i][0] for i in false_ids) / len(false_ids)}
        for key in ("recall", "unverified"):
            e = per_arm[arm][key]
            e["recovered"] = e["estimate"] is not None and in_interval(e["planted"], e["interval"])
    reasons = [] if len(prop_acc) >= est["rt_min_accepted"] else [
        f"false lemmas accepted by the proposer ({len(prop_acc)}) fewer than {est['rt_min_accepted']}"]
    lo, hi = interval
    decision = "uninformative" if reasons else "supported" if hi < 0 else "killed" if lo > 0 else "inconclusive"
    return {"estimate": h._mean(diffs), "interval": interval, "planted": planted,
            "recovered": in_interval(planted, interval), "decision": decision, "uninformative": reasons,
            "discordant": (x, y), "p_one_sided": rt_exact_p(x, y), "diffs": diffs, "arms": per_arm, "rows": arms}


# ------------------------------------------------------------------------------------------------ F6 ----

DEFECTS = (
    ("quantifier_swap", "For every n there is a circuit of size at most n^<k> deciding L on inputs of length n.",
     "forall n, exists C, size(C) <= n^<k> and forall x in {0,1}^n, C(x) = L(x)", "forall n, exists C,",
     "exists C, forall n,"),
    ("n_vs_N", "The machine runs in time polynomial in the bit-length N of its input, with exponent <k>.",
     "forall x, time(M, x) <= N^<k> + <k> where N = |x|", "N^<k> + <k>", "n^<k> + <k>"),
    ("vacuous_hypothesis", "Every satisfiable 3-CNF with at most m clauses is solved within <k> m steps.",
     "forall phi, sat(phi) and clauses(phi) <= m -> steps(phi) <= <k> m", "sat(phi) and clauses(phi) <= m",
     "clauses(phi) < 0"),
    ("uniform_vs_nonuniform", "A single machine decides L for every input length, using at most <k> work cells.",
     "exists M, forall n, forall x in {0,1}^n, M(x) = L(x) and cells(M, x) <= <k>", "exists M, forall n,",
     "forall n, exists M,"),
    ("degenerate_edge", "For every input length n >= 1 the bound f(n) <= <k> g(n) holds.",
     "forall n >= 1, f(n) <= <k> g(n)", "n >= 1", "n >= 5"),
)


def n_spans(length):
    """Spans [start, end) with 0 <= start < end <= length: the support of a uniformly random span guess."""
    return length * (length + 1) // 2


def random_span(rng, length):
    """A span drawn uniformly from the n_spans(length) spans."""
    k = rng.randrange(n_spans(length))
    s0 = 0
    while k >= length - s0:
        k -= length - s0
        s0 += 1
    return [s0, s0 + 1 + k]


def gen_audit_tasks(count, faithful_rate, seed, tag):
    """F6 pairs: an informal statement and a formal one, faithful with probability faithful_rate, else one defect whose
    exact span [start, end) in the formal text is recorded. Ground truth is the planted label and span."""
    _int(count, "count", 1, 10**5), _p(faithful_rate, "faithful_rate")
    rng = random.Random(task_seed(f"gen-F6:{tag}", seed, 0))
    out = []
    for _ in range(count):
        kind, inf, formal, old, new = DEFECTS[rng.randrange(len(DEFECTS))]
        k = str(rng.randrange(1, 10))
        inf, formal, old, new = (x.replace("<k>", k) for x in (inf, formal, old, new))
        if rng.random() < faithful_rate:
            out.append({"family": "F6", "difficulty": 0, "informal": inf, "formal": formal, "defective": False,
                        "defect": None, "span": None})
            continue
        bad = formal.replace(old, new)
        if bad.count(new) != 1 or formal.count(old) != 1:
            raise ValueError("a defect must be a single edit")
        a = bad.index(new)
        out.append({"family": "F6", "difficulty": 0, "informal": inf, "formal": bad, "defective": True, "defect": kind,
                    "span": [a, a + len(new)]})
    return out


def oracle_f6(task, claim):
    """F6: a faithful pair needs the verdict faithful; a defective pair needs the verdict defective with the exact span."""
    try:
        if type(claim["faithful"]) is not bool:
            return 0
        if not task["defective"]:
            return int(claim["faithful"])
        sp = claim["span"]
        return int(claim["faithful"] is False and isinstance(sp, (list, tuple)) and len(sp) == 2
                   and all(type(v) is int for v in sp) and list(sp) == task["span"])
    except (TypeError, KeyError):
        return 0


ORACLES["F6"] = oracle_f6


class F6Agent(R6Agent):
    """Scripted auditor: flags a defective pair with probability detect and a faithful one with false_alarm; a flag
    carries the exact span with probability locate, else a uniformly random span."""

    def __init__(self, seed, task, aud):
        super().__init__(seed, task, 0.0, None, None)
        self.aud = aud

    def claim_for(self, a):
        r = random.Random(f"audit:{self.seed}:{a}")
        t, u = self.task, r.random()
        if t["defective"]:
            if u >= self.aud["detect"]:
                return {"faithful": True, "span": None}, None
            if r.random() < self.aud["locate"]:
                return {"faithful": False, "span": list(t["span"])}, None
        elif u >= self.aud["false_alarm"]:
            return {"faithful": True, "span": None}, None
        return {"faithful": False, "span": random_span(r, len(t["formal"]))}, None


def run_f6(seed, design, plant, est):
    """F6 Definition Audit: rates with exact (Clopper-Pearson) intervals; no hypothesis test (plan section 4)."""
    aud = plant["audit"]
    tasks = {i: t for i, t in enumerate(gen_audit_tasks(design["audit_pairs"], design["faithful_rate"], seed, "f6"))}
    rows, ag = play(tasks, [2], 1, 6 * seed, "f6", None, make=lambda ep, t: F6Agent(ep, t, aud))
    recs = [(tasks[r["task"]], ag[(r["n"], r["task"], r["rerun"])].rec[f"a{r['agent']}"]["claim"]) for r in rows]
    dfc = [(t, c) for t, c in recs if t["defective"]]
    fth = [(t, c) for t, c in recs if not t["defective"]]
    flagged_def = [(t, c) for t, c in dfc if c["faithful"] is False]
    tp, fp = len(flagged_def), sum(c["faithful"] is False for _, c in fth)
    tn = sum(c["faithful"] is True for _, c in fth)
    exact = sum(c["span"] == t["span"] for t, c in flagged_def)

    def rate(k, m, planted):
        ci = _cp(k, m, est["level"])
        return {"estimate": k / m if m else None, "interval": ci, "planted": planted, "n": m, "k": k,
                "recovered": bool(m) and in_interval(planted, ci)}

    exp_tp, exp_fp = aud["detect"] * len(dfc), aud["false_alarm"] * len(fth)
    chance = math.fsum(aud["locate"] + (1 - aud["locate"]) / n_spans(len(t["formal"])) for t, _ in dfc) / len(dfc) if dfc else 0.0
    return {"recall": rate(tp, len(dfc), aud["detect"]), "true_negative": rate(tn, len(fth), 1 - aud["false_alarm"]),
            "precision": rate(tp, tp + fp, exp_tp / (exp_tp + exp_fp) if exp_tp + exp_fp else 0.0),
            "span": rate(exact, tp, chance), "rows": rows, "tasks": tasks}


# ------------------------------------------------------------------------------------------ scorecards ----

LENS = {"F2": "circuit", "F3": "meta_complexity", "F5": "circuit", "F6": "descriptive"}
PLANTED_GATES = ("G2", "G3", "G4")


def make_card(task, task_id, row, rec, card):
    """One scorecard for one scripted run; pass is copied from the oracle row, gates are recomputed by the scorecard
    module, and a planted defect (card["gate_plant"]) only touches the gate-relevant fields. Returns (card, score)."""
    ok, fam, plant_gate = row["pass"], task["family"], row.get("planted_gate")
    src = task.get("source", "")
    crit = {k: {"score": card["rubric"][k], "weight": card["weights"][k], "evidence": "scripted agent: fixed rubric"}
            for k in sc.CRITERIA}
    na = {"status": "not_applicable", "argument": "finite check: no lower bound is claimed"}
    c = {
        "schema_version": sc.SCHEMA_VERSION, "line": "R6", "candidate_id": f"{fam}-{task_id}-{row['n']}-{row['rerun']}-{row['agent']}",
        "iteration": row["rerun"], "commit": "",
        "agent": {"role": "solver", "model": "scripted", "team_size": row["n"], "arm": row.get("arm", "none")},
        "lens": LENS[fam], "claim_type": "finite_lemma",
        "model_of_computation": "" if plant_gate == "G4" else "nonuniform_circuit",
        "input_parameter": "truth_table_2^n", "statement": f"scripted {fam} claim on task {task_id}",
        "predicate": {"path": "", "sha256": hashlib.sha256(src.encode()).hexdigest() if src else "",
                      "domain": "x, y in range(2**width)" if src else "all truth tables", "step_limit": task.get("step_limit", 0)},
        "small_n_claim": {"explicit_constants": False, "threshold_n0": None, "result": "na"},
        "claims": [{"id": "c1", "text": f"{fam} claim", "status": "" if plant_gate == "G2" else (
            "checked_by_oracle" if ok else "conjecture"), "evidence": "oracle re-run on the recorded claim"}],
        "barrier_audit": {"relativization": dict(na), "natural_proofs": dict(na, meter={
            "k": None, "c": None, "s": None, "cost_ops": None, "density": None, "useful": None}),
            "algebrization": dict(na)},
        "hard_gates": {g: "na" for g in sc.GATES}, "criteria": crit, "weighted_total": 0.0, "disqualified": False,
        "disqualification_reasons": [],
        "oracle_checks": {"claims_checkable": 1, "claims_checked": 1, "claims_passed": ok, "max_n": 4,
                          "wall_seconds": 0.0, "checker": f"lab/r6_stage_a.py:oracle_{fam.lower()}"},
        "red_team": {"attempted": False, "verdict": "na", "counterexample": "", "counterexample_verified": None,
                     "label_overridden": False},
        "definition_audit": {"done": False, "auditor": "", "reference_statement": "", "faithful": None, "defect_spans": []},
        "lean": {"kernel_checked": False, "toolchain": "", "axioms": [], "sorry_count": None},
        "separations": {"asymptotic_vs_practical": "a finite check says nothing asymptotic",
                        "worst_vs_average_case": "exhaustive over a finite domain"},
        "performance_row": {"task": str(task_id), "family": fam, "n": row["n"], "rerun": row["rerun"],
                            "agent": row["agent"], "pass": row["pass"], "conf": rec["conf"]},
        "resources": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "wall_seconds": 0.0, "hosted_usd": 0.0},
        "verdict": "revise",
        "reviewer": {"id": "scripted", "independent": False, "notes": "", "overclaim_flag": plant_gate == "G3"},
        "evidence_paths": [],
    }
    g, why = sc.gates(c, briefing_keywords=card["briefing_keywords"], overclaim_patterns=card["overclaim_patterns"])
    dq = "fail" in g.values()
    c.update(hard_gates=g, disqualified=dq, disqualification_reasons=why, verdict="prune" if dq else "revise",
             weighted_total=0.0 if dq else 100 * math.fsum(card["weights"][k] * card["rubric"][k] for k in sc.CRITERIA) / 5)
    res = sc.score(c, weights=card["weights"], briefing_keywords=card["briefing_keywords"],
                   overclaim_patterns=card["overclaim_patterns"])
    if not res["valid"] or res["declared_mismatch"] or c["performance_row"]["pass"] != ok:
        raise ValueError(f"scorecard not accepted: {res}")
    return c, res


def card_report(family, tasks, rows, agents, seed, card):
    """A card for every row; a planted gate failure is drawn per row by hash of (task, rerun, agent). Report per team
    size: rows, planted, gate failures per gate, and whether pass stayed equal to the oracle row."""
    gp = card["gate_plant"]
    out, example = {}, None
    for r in rows:
        key = (r["task"] * 1000 + r["rerun"]) * 100 + r["agent"]
        hit = random.Random(task_seed(f"gate-{family}-{r['n']}", seed, key)).random() < gp["rate"]
        row = dict(r, planted_gate=gp["gate"] if hit else None)
        c, res = make_card(tasks[r["task"]], r["task"], row, agents[(r["n"], r["task"], r["rerun"])].rec[f"a{r['agent']}"], card)
        e = out.setdefault(r["n"], {"rows": 0, "planted": 0, "fail": {g: 0 for g in sc.GATES}, "pass_unchanged": True,
                                    "zero_total_when_disqualified": True})
        e["rows"] += 1
        e["planted"] += hit
        for g, v in res["gates"].items():
            e["fail"][g] += v == "fail"
        e["pass_unchanged"] &= c["performance_row"]["pass"] == r["pass"]
        e["zero_total_when_disqualified"] &= (not res["disqualified"]) or res["weighted_total"] == 0.0
        if hit and example is None:
            example = c
    return {"per_team_size": out, "example_planted_card": example}


# ----------------------------------------------------------------------------------------------- stage A ----

DESIGN = ("n_vars", "tasks", "reruns", "h5_tasks", "cal_reruns", "h5_reruns", "difficulty", "families", "h35_family",
          "yes_rate", "false_rate", "step_limit", "total_steps", "rt_lemmas", "audit_pairs", "faithful_rate")
PLANT = ("pass_p", "c", "conf_bias", "ask_effect", "false_clean", "f", "spread", "rt", "audit")
EST = ("level", "alpha", "alpha_recover", "grid_steps", "B", "perms", "edge", "K", "negligible", "max_unparseable", "rt_min_accepted")
CARD = ("weights", "rubric", "briefing_keywords", "overclaim_patterns", "gate_plant")


def _check_config(design, plant, est, card):
    _need(design, DESIGN, "design"), _need(plant, PLANT, "plant"), _need(est, EST, "est"), _need(card, CARD, "card")
    _int(design["n_vars"], "n_vars", 1, 3)  # the synthesizer behind the scripted agents stops at n = 3
    for k in ("tasks", "reruns", "h5_tasks", "cal_reruns", "h5_reruns"):
        _int(design[k], k, 1, 10**4)
    if not isinstance(design["families"], (list, tuple)) or not design["families"] or not set(design["families"]) <= set(FAMILIES):
        raise ValueError(f"families must be a nonempty subset of {FAMILIES}")
    if design["h35_family"] not in FAMILIES or not isinstance(design["difficulty"], dict):
        raise ValueError("h35_family must be a family and difficulty a dict family -> difficulty")
    for fam in set(design["families"]) | {design["h35_family"]}:
        d = design["difficulty"].get(fam)
        _int(d, f"difficulty[{fam}]", 0, 7)
        if d not in plant["pass_p"]:
            raise ValueError(f"pass_p needs an entry for difficulty {d}")
    for d, p in plant["pass_p"].items():
        _int(d, "pass_p key", 0, 7), _p(p, "pass_p", True, True)
    _p(plant["c"], "c"), _p(plant["ask_effect"] + 0.5, "ask_effect + 0.5")  # ask_effect in [-0.5, 0.5]
    _need(plant["conf_bias"], ("team", "solo"), "conf_bias")
    for k in ("rt_lemmas", "audit_pairs"):
        _int(design[k], k, 2, 10**5)
    _p(design["faithful_rate"], "faithful_rate")
    rt = _need(plant["rt"], ("accept_false", "reject_true", "find", "bogus"), "rt")
    _p(rt["accept_false"], "accept_false"), _p(rt["reject_true"], "reject_true")
    for k in ("find", "bogus"):
        _need(rt[k], ARMS_RT, f"rt.{k}")
        for arm in ARMS_RT:
            _p(rt[k][arm], f"rt.{k}.{arm}")
    for k, v in _need(plant["audit"], ("detect", "false_alarm", "locate"), "audit").items():
        _p(v, f"audit.{k}")
    _int(est["rt_min_accepted"], "rt_min_accepted", 1, 10**5)
    _p(est["level"], "level", True, True), _p(est["alpha_recover"], "alpha_recover", True, True)
    _need(card["gate_plant"], ("rate", "gate"), "gate_plant")
    _p(card["gate_plant"]["rate"], "gate rate")
    if card["gate_plant"]["gate"] not in PLANTED_GATES:
        raise ValueError(f"gate must be one of {PLANTED_GATES}")
    sc._check_weights(card["weights"])
    _need(card["rubric"], sc.CRITERIA, "rubric")


def stage_a(seed, *, design, plant, est, card):
    """Run H2 (per family), H3 and H5 on scripted agents with planted values and report, per hypothesis, the estimate,
    its interval, the planted value and whether it is recovered; one scorecard per H2 row, accepted by the scorecard
    validator. H1 is not instantiated (plan Part II section 2). Every config key is required."""
    _int(seed, "seed", 0, 10**9)
    _check_config(design, plant, est, card)
    out = {"H2": {}, "cards": {}, "not_instantiated": {"H1": "stays with R5 (plan Part II section 2)",
                                                       "not_done": ["F1", "F4"]}}
    for fam in design["families"]:
        r = out["H2"][fam] = run_h2(fam, seed, design, plant, est)
        out["cards"][fam] = [card_report(fam, t, rows, ag, seed, card) for t, rows, ag in r.pop("runs")]
    out["H3"] = run_h3(design["h35_family"], seed, design, plant, est)
    out["H5"] = run_h5(design["h35_family"], seed, design, plant, est)
    out["RT"] = run_rt(seed, design, plant, est)
    out["F6"] = run_f6(seed, design, plant, est)
    return out
