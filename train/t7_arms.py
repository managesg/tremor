"""T7 arms (0, A, B, C, D), problem sampling, truncation accuracy and a crash-safe JSONL writer.
Model code is injected via `generate`; nothing heavy is imported here."""
import json
import os
import random

# Released-edit checkpoint id is unverified (gate G3); C's setting is chosen on practice problems.
ARMS = {
    "0": {"desc": "base, thinking on", "thinking": True},
    "A": {"desc": "released edited checkpoint", "thinking": True, "checkpoint": None},
    "B": {"desc": "base, thinking off", "thinking": False},
    "C": {"desc": "base, thinking on, repetition penalty", "thinking": True, "repetition_penalty": None},
    "D": {"desc": "loop direction removed from MLP layers 15,19", "thinking": True, "layers": [15, 19]},
}


def sample_problems(ids, n, seed):
    return random.Random(seed).sample(sorted(ids), n)


def accuracy_at_cap(records, cap):
    """Correct only if the full answer was correct and finished within `cap` tokens (truncation read)."""
    if not records:
        raise ValueError("no records")
    return sum(1 for r in records if r["correct"] and r["tokens"] <= cap) / len(records)


def write_result(path, rec):
    """Append one record as a full line, flushed and fsynced, so a stopped run stays valid."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_results(path):
    """Valid records only; a torn final line is ignored."""
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def run(arm, problems, cap, out, generate, seed=None):
    """generate(arm_spec, problem, cap) -> {"correct": bool, "tokens": int, ...}.
    Resumes past records with the same (id, arm, cap, seed), so a shared file cannot skip another arm.
    shortcut: records written before arm/cap/seed were stored never match, so they re-run; fine pre-run."""
    spec = ARMS[arm]
    done = {(r.get("id"), r.get("arm"), r.get("cap"), r.get("seed")) for r in read_results(out)}
    for p in problems:
        if (p["id"], arm, cap, seed) not in done:
            write_result(out, {"id": p["id"], "arm": arm, "cap": cap, "seed": seed, **generate(spec, p, cap)})
