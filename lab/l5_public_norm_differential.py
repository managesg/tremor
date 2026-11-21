"""Check public Python grader receipts with the pinned Lean sibling predicate."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from lab import adapter_lineage, l5_grader_custody


def _natural_id(value, prefix):
    if not value.startswith(prefix) or not value[len(prefix):].isascii() or not value[len(prefix):].isdigit():
        raise ValueError("unexpected synthetic identity")
    return int(value[len(prefix):])


def _statement(case):
    frame = case["frame"]
    action, state = frame["action"], frame["state"]
    task_ids = {task["id"]: ordinal for ordinal, task in enumerate(frame["reference"]["tasks"])}
    task = task_ids[action["task"]]
    worker = _natural_id(action["agent"], "a")
    holder = "none" if state["claim_holder"] is None else f"(some {_natural_id(state['claim_holder'], 'a')})"
    reviews = ", ".join(
        f"⟨{task_ids[review['refs'][0]]}, {_natural_id(review['refs'][1], 'a')}, "
        f"{_natural_id(review['agent'], 'a')}, {review['round']}⟩"
        for review in state["reviews"]
    )
    attempt = f"(⟨{task}, {worker}, {state['round']}, {holder}, [{reviews}]⟩ : L5PublicSibling.Attempt)"
    norm = str(case["verdict"]["norm_allows"]).lower()
    executed = str(case["execution"]["executed"]).lower()
    violation = str(case["execution"]["executed_norm_violation"]).lower()
    return (
        f"example : L5PublicSibling.allows L5PublicSibling.four {attempt} = {norm} := by decide\n"
        f"example : L5PublicSibling.executedViolation L5PublicSibling.four {attempt}"
        f" {executed} = {violation} := by decide\n"
    )


def verify(source, lean, *, source_sha256, lean_sha256):
    """Replay Python's public four-worker cases and prove the same verdicts in Lean."""
    raw = Path(source).read_bytes()
    adapter_lineage._match(source, hashlib.sha256(raw).hexdigest(), source_sha256)
    binary = Path(lean).resolve(strict=True)
    with binary.open("rb") as stream:
        adapter_lineage._match(binary, hashlib.file_digest(stream, "sha256").hexdigest(), lean_sha256)
    report = l5_grader_custody.development_report()
    cases = report["cases"]
    if report["scientific_n2_frozen"] or not cases:
        raise ValueError("expected nonempty public grader development cases")
    with TemporaryDirectory(prefix="tremor-l5-lean-") as folder:
        proof = Path(folder) / "PublicNormProof.lean"
        proof.write_bytes(raw + b"\n" + "".join(_statement(case) for case in cases.values()).encode())
        completed = subprocess.run([str(binary), str(proof)], capture_output=True, text=True, timeout=10)
        if completed.returncode:
            raise ValueError(f"Lean did not verify the public cases: {completed.stdout}{completed.stderr}")
    return {
        "evidence": "public_synthetic_l5_python_lean_agreement",
        "case_names": sorted(cases),
        "verified_statements": 2 * len(cases),
        "lean_source_sha256": source_sha256,
        "lean_binary_sha256": lean_sha256,
        "python_evaluator_sha256": l5_grader_custody.evaluator_digest(),
        "scientific_n2_frozen": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("lean", type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--lean-sha256", required=True)
    args = parser.parse_args()
    try:
        result = verify(**vars(args))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
