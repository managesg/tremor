"""T7 problem samples, both defined by seed. The smoke sample is drawn from the complement of the main one,
so the two are disjoint by construction (tested in tests/test_t7_samples.py)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t7_arms import sample_problems  # noqa: E402

MAIN_SEED, MAIN_N = 20261119, 100
SMOKE_SEED, SMOKE_N = 20261120, 20


def load_math500(path):
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    ids = [r["unique_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate unique_id")
    return {r["unique_id"]: r for r in rows}


def main_ids(ids):
    return sample_problems(ids, MAIN_N, MAIN_SEED)


def smoke_ids(ids):
    return sample_problems(set(ids) - set(main_ids(ids)), SMOKE_N, SMOKE_SEED)
