"""R6 T1: builds F6 definition-audit CANDIDATE pairs from the vp-vnp Statement.lean (untrusted data, read as text only).

Read before use:
- INFORMAL SIDE: each informal statement is the Lean DOCSTRING text, so a pair audits the code against its own comments,
  not against the paper's prose (informal_source 'lean-docstring'). Replace when R6-O25 lands (prose transcribed twice
  and agreed).
- STATUS: every defect is 'semantic change by inspection'; none was checked in Lean. vnp_equality_on_01 is marked
  uncertain and must be EXCLUDED from any scored pool until a human with Lean confirms elaboration.
- SPAN: the MINIMAL-DIFF span: the smallest contiguous region of the defective text left after trimming the common prefix
  and suffix against the faithful text, as code points [start, end) with no normalisation (start == end for a pure
  deletion, e.g. hc_cycle_predicate). Computed from the pair, never typed.
- TELLS (known): length changes vs the faithful text: vp_degree_bound_dropped -30, hc_cycle_predicate -11,
  main_charp_dropped +1, vnp_equality_on_01 +105, the others 0; the literal `True` in the vp defect is a tell.
- LEAKS: the faithful text is public with a known sha256, so an agent with tools could recognise faithful pairs by hash.
  Contamination (R6-O28): agents must not be shown the paper or the repository.
- SEALING (R6-O3): the pair data for an experiment are sealed by the custodian; this module only builds candidates. A
  sealed build passes sealed=True and no caller text (the source then goes through load_source and its hash check).
"""
import hashlib
import os

from lab import r6_stage_a as SA

SOURCE_SHA256 = "f090345dafa13c7629ff0c0737bb1c2fe5d60e8b2d08372281cbb2e65b506ffd"
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PATH = os.path.join(_ROOT, "docs", "reports", "tremor", "vpvnp_source", "Statement.lean")
FALLBACK_PATH = os.path.join(_ROOT, "runs", "vpvnp-repo-files", "Statement.lean")
EVIDENCE = "semantic change by inspection"
INFORMAL_SOURCE = "lean-docstring"  # replace when R6-O25 lands

# id, prefix + old + suffix (unique in the file), new, informal (verbatim docstring), why, may_elaborate
_RAW = (
    ("beyond_exponent_nat", "(1 / 3 : ", "ℝ", ")", "ℕ",
     "More than `m ^ (c * (log₂ m) ^ (1/3))` gates.",
     "1/3 becomes natural-number division = 0, so the exponent factor is 1 and the bound collapses to m ^ c", "likely"),
    ("computes_self_reference", "(∃ i ", "<", " k, ∃ j < k, l k = l i + l j)", "≤",
     "each of\nthem is a variable, a constant, or the sum or product of two earlier ones (possibly the same one). Variables and\nconstants count as gates.",
     "a sum gate may cite itself (i = k): l k = l k + l j holds whenever some earlier gate j < k is zero (a constant gate C 0 is legal), so l k is then unconstrained and every polynomial has a 2-gate circuit", "likely"),
    ("vp_degree_bound_dropped", "card (f.vars n) ≤ n ^ a + a ∧ ", "(f.poly n).totalDegree ≤ n ^ a + a", " ∧\n    Computes", "True",
     "VP: the number of variables, the degree and the circuit size are polynomially bounded in `n`.",
     "the degree bound becomes vacuous, so the class VP gets larger", "likely"),
    ("main_quantifier_swap", "def MainTheorem : Prop :=\n  ", "∃ c : ℝ, 0 < c ∧ ∀ p : ℕ,", " ∃ m₀ : ℕ, ∀ (F : Type u) [Field F] [CharP F p]",
     "∀ p : ℕ, ∃ c : ℝ, 0 < c ∧",
     "There is an absolute constant `c > 0`, and for each characteristic `p` an `m₀`",
     "c may depend on the characteristic p: the constant is no longer absolute, a weaker theorem", "likely"),
    ("hc_cycle_predicate", "σ.", "IsCycleOn Set.univ", ", ∏ i, X (i, σ i)", "IsCycle",
     "the sum over the permutations with a single cycle through all points",
     "IsCycle is the permutation-level predicate (one non-trivial cycle, fixed points allowed), not a cycle through all points", "likely"),
    ("main_charp_dropped", "∀ (F : Type u) [Field F] ", "[CharP F p]", ", ∀ m ≥ m₀, ∀ s : ℕ,\n    (Computes",
     "[Nonempty F]",
     "over every field of characteristic `p`",
     "the characteristic hypothesis is replaced by a vacuous instance, so p is unlinked to F: with p = 3 and F of characteristic 2, perm = det has polynomial-size circuits (known fact), so the perm clause is false; the binder compiles", "likely"),
    ("separation_subset_weak", "∀ (F : Type u) [Field F], VP F ", "⊂", " VNP F",
     "⊆", "over every field VP is a proper subset of VNP",
     "strict inclusion becomes inclusion: VP = VNP would satisfy the statement", "likely"),
    ("vnp_equality_on_01", "∀ n, ", "f.poly n = ∑ e : Fin (r n) → Bool, aeval (Sum.elim X fun i => if e i then 1 else 0) (g n)", "}",
     "∀ x : f.vars n → Bool, aeval (fun v => if x v then (1 : F) else 0) (f.poly n) = ∑ e : Fin (r n) → Bool, aeval (Sum.elim (fun v => if x v then (1 : F) else 0) fun i => if e i then 1 else 0) (g n)",
     "the families `f n = ∑ g n (x, e)`, as polynomials",
     "polynomial equality becomes agreement on 0/1 inputs only (the paper's gap between formal and Boolean equality); may not compile",
     "uncertain"),
)


def load_source(path=None, sha256=SOURCE_SHA256):
    """Read the file as UTF-8 text (no newline translation, no normalisation) and refuse a digest mismatch."""
    path = path or (SOURCE_PATH if os.path.exists(SOURCE_PATH) else FALLBACK_PATH)
    with open(path, "rb") as fh:
        raw = fh.read()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError(f"source digest mismatch for {path}")
    return raw.decode("utf-8")


def defect_specs():
    """The registered defects: id, context_before, old, context_after, new, informal, why, may_elaborate, evidence."""
    keys = ("id", "before", "old", "after", "new", "informal", "why", "may_elaborate")
    return [dict(zip(keys, r), evidence=EVIDENCE) for r in _RAW]


def locate(text, spec):
    """Code-point offset of spec['old'] in text; before+old+after must occur exactly once. Raises otherwise."""
    ctx = spec["before"] + spec["old"] + spec["after"]
    if not spec["old"] or not spec["new"] or spec["old"] == spec["new"]:
        raise ValueError(f"{spec['id']}: old and new must be non-empty and differ")
    if text.count(ctx) != 1:
        raise ValueError(f"{spec['id']}: context occurs {text.count(ctx)} times, need exactly 1")
    return text.index(ctx) + len(spec["before"])


def minimal_span(faithful, defective):
    """[start, end) in the defective text after trimming the common prefix and suffix against the faithful text."""
    if faithful == defective:
        raise ValueError("no difference")
    p = 0
    while faithful[p:p + 1] == defective[p:p + 1] and p < min(len(faithful), len(defective)):
        p += 1
    q = 0
    while q < min(len(faithful), len(defective)) - p and faithful[-1 - q] == defective[-1 - q]:
        q += 1
    return [p, len(defective) - q]


def placements(faithful, defective, span):
    """Positions where a region of the span's width in the defective text, replaced by the faithful text it stands for,
    restores the faithful text. More than one means the minimal-diff span is ambiguous (the edit sits by identical text)."""
    a, b = span
    old = faithful[a:a + len(faithful) - (len(defective) - (b - a))]
    return sum(defective[:i] + old + defective[i + b - a:] == faithful for i in range(len(defective) - (b - a) + 1))


def _inputs(text, specs, sealed):
    if sealed and (text is not None or specs is not None):
        raise ValueError("sealed build: caller text or specs refused, the source goes through load_source")
    return (load_source() if text is None else text), (defect_specs() if specs is None else specs)


def build_pair(defect_id, text=None, specs=None, sealed=False):
    """Faithful text, defective text and the minimal-diff span in the defective text."""
    text, specs = _inputs(text, specs, sealed)
    spec = {s["id"]: s for s in specs}.get(defect_id)
    if spec is None:
        raise KeyError(defect_id)
    a = locate(text, spec)
    bad = text[:a] + spec["new"] + text[a + len(spec["old"]):]
    if bad == text or bad[:a] != text[:a] or bad[a:a + len(spec["new"])] != spec["new"]:
        raise ValueError(f"{defect_id}: not a single changing edit")
    if spec["informal"] not in text:
        raise ValueError(f"{defect_id}: informal statement is not verbatim in the source")
    span = minimal_span(text, bad)
    if placements(text, bad, span) != 1:
        raise ValueError(f"{defect_id}: the minimal-diff span is not unique (the edit sits next to identical text)")
    return {"id": defect_id, "faithful": text, "defective": bad, "span": span,
            "informal": spec["informal"], "informal_source": INFORMAL_SOURCE, "why": spec["why"],
            "may_elaborate": spec["may_elaborate"], "evidence": spec["evidence"]}


def defective_task(defect_id, text=None, specs=None, sealed=False):
    p = build_pair(defect_id, text, specs, sealed)
    return {"family": "F6", "difficulty": 0, "informal": p["informal"], "informal_source": INFORMAL_SOURCE,
            "formal": p["defective"], "defective": True, "defect": defect_id, "span": p["span"]}


def faithful_pairs(text=None, specs=None, sealed=False):
    """True negatives: the file unmodified, one per defect's informal statement."""
    text, specs = _inputs(text, specs, sealed)
    return [{"family": "F6", "difficulty": 0, "informal": s["informal"], "informal_source": INFORMAL_SOURCE,
             "formal": text, "defective": False, "defect": None, "span": None} for s in specs]


def oracle(task, claim):
    return SA.oracle_f6(task, claim)


def render_prompt(task):
    return ("Decide whether the FORMAL Lean text is a faithful rendering of the INFORMAL statement. If not, mark the "
            "smallest contiguous region you would change to restore the original, as a code-point [start, end) of the "
            "FORMAL text (an insertion or deletion point has start == end).\n\n"
            f"INFORMAL (source: {task['informal_source']}):\n{task['informal']}\n\nFORMAL:\n{task['formal']}")


def prompt_sha256(task):
    """sha256 of the UTF-8 rendered prompt (the same digest as r6_p0_probe.prompt_sha256 on a string)."""
    return hashlib.sha256(render_prompt(task).encode("utf-8")).hexdigest()
