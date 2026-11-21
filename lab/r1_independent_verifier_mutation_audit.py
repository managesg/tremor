"""Inject public development faults into alloc.score in memory and test the corpus."""

from hashlib import sha256
import inspect
import json
from pathlib import Path
from unittest.mock import patch

from lab import r1_public_arithmetic_mutants as corpus
from murmuration.trapbench import alloc, alloc2


SOURCE_SHA256 = {
    "alloc.py": "07ae29d898ee57efea40f02116ab6157d8920350637ea0293a152a9e3988932f",
    "alloc2.py": "c78207f7dab9d66daa3b42a72afb5fa22c0063b26518a5f0937a572c4534000a",
    "r1_public_arithmetic_mutants.py": "ebb3e1e1d983117a8198ee98ce5d6a058ef6277bb405422b574b0b2e9ea436d6",
}


MUTANTS = (
    ("allow_numeric_aliases", 'type(e.get("answer")) is int and e["answer"] == expect[e["task"]]',
     'e.get("answer") == expect[e["task"]]'),
    ("ignore_incorrect_integer", 'type(e.get("answer")) is int and e["answer"] == expect[e["task"]]',
     'type(e.get("answer")) is int'),
    ("count_refused_work", ' and not e.get("rejected")', ''),
    ("count_duplicate_passing_slots", '"distinct_passing": len(passing)',
     '"distinct_passing": sum(passes(e) for e in work)'),
    ("first_writer_survives", 'last[e.get("name") or ""] = e', 'last.setdefault(e.get("name") or "", e)'),
    ("ignore_survival_clobber", '"surviving_passing": len(surviving)', '"surviving_passing": len(passing)'),
    ("always_no_duplicates", '"duplicates": len(work) - len({e["task"] for e in work})', '"duplicates": 0'),
    ("always_no_name_collisions", '"name_collisions": len(work) - len(last)', '"name_collisions": 0'),
    ("permit_repeat_worker_validity", ' and extra == 0', ''),
    ("permit_malformed_validity", 'len(ok) == len(log) and extra == 0', 'extra == 0'),
    ("normalize_by_attempts", 'len(passing) / ts["n_agents"] if valid', 'len(passing) / len(work) if valid'),
    ("void_on_out_of_inventory_work", ' and len(work) <= ts["n_agents"]',
     ' and len(work) <= ts["n_agents"] and unknown == 0'),
)


def _compile_score(source):
    scope = vars(alloc).copy()
    exec(compile(source, "<public arithmetic verifier>", "exec"), scope)
    return scope["score"]


def verify():
    source_pins = {Path(module.__file__).name: sha256(Path(module.__file__).read_bytes()).hexdigest()
                   for module in (alloc, alloc2, corpus)}
    if source_pins != SOURCE_SHA256:
        raise ValueError("public mutation check must use the reviewed scorer and corpus source")
    source = inspect.getsource(alloc.score)
    taskset = corpus._taskset()
    clean = alloc.oracle_log(taskset)
    cases = corpus._cases(clean)

    def select(scorer, rows):
        return {key: value for key, value in scorer(rows, taskset).items() if key in corpus.CHECKS}

    unmodified = _compile_score(source)
    baseline = select(unmodified, clean)
    assert baseline == dict(zip(corpus.CHECKS, corpus.CLEAN, strict=True))
    for rows, expected in cases.values():
        assert select(unmodified, rows) == dict(zip(corpus.CHECKS, expected, strict=True))
    reordered, _ = cases["reordered_distinct_work"]
    assert select(unmodified, reordered) == baseline
    assert corpus.evaluate()["protected_n2"] is False

    killed = []
    for label, original, replacement in MUTANTS:
        assert source.count(original) == 1, label
        mutant = _compile_score(source.replace(original, replacement, 1))
        witnessed = {}
        for case, (rows, expected) in cases.items():
            expected = dict(zip(corpus.CHECKS, expected, strict=True))
            observed = select(mutant, rows)
            if observed != expected:
                witnessed[case] = {"expected": expected, "mutant": observed}
        assert witnessed, label
        with patch.object(alloc, "score", mutant):
            try:
                corpus.evaluate()
            except ValueError as error:
                assert str(error).startswith("alloc disagrees"), error
            else:
                raise AssertionError(f"corpus accepted {label}")
        killed.append({"mutation": label, "original": original, "replacement": replacement, "failures": witnessed})
    return {
        "evidence": "independent_public_arithmetic_verifier_mutation_check",
        "technique": "compile twelve actual alloc.score code mutations individually in memory",
        "source_sha256": source_pins,
        "unmodified_case_checks": len(cases),
        "unmodified_clean": baseline,
        "unmodified_distinct_reorder": select(unmodified, reordered),
        "mutants_killed": len(killed),
        "mutants": killed,
        "protected_n2": False,
        "bench_acceptance_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True, indent=2, allow_nan=False))
