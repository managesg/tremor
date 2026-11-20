"""W1-10 episode runner. run() plays one E8.3 SQL sequence and returns one record; stdlib only.

task is a sqlseq family name. Missing values are None, never 0 (scripted has no cache tokens).
"""
import json
import os
import sqlite3
import tempfile
import time

from murmuration import manifest
from murmuration.trapbench import sqlseq

ARMS = ("stateless", "oracle", "raw-notes")
NOTE = "orders join customers on customers.code, not id. money columns hold cents."


def _answer(db, q, fam, informed):
    cust, order, ref, money = sqlseq.FAMILIES[fam]
    on, div = ("c.code", 100) if informed else ("c.id", 1)
    agg = {"spend": f"SUM({money})", "count": "COUNT(*)", "max": f"MAX({money})"}[q["kind"]]
    r = db.execute(f"SELECT {agg} FROM {order} o JOIN {cust} c ON o.{ref}={on} WHERE c.name=?", (q["name"],)).fetchone()[0] or 0
    return str(r) if q["kind"] == "count" else f"{r / div:.2f}"


def _scripted(task, arm, seed, qs, db):
    """Deterministic; tokens are len//4 estimates of the prompt/answer text, not model counts."""
    informed = arm in ("oracle", "raw-notes")
    ans, tin, tout = {}, 0, 0
    for q in qs:
        ans[q["id"]] = _answer(db, q, task, informed)
        tin += (len(q["q"]) + (len(NOTE) if arm == "raw-notes" else 0)) // 4
        tout += len(ans[q["id"]]) // 4 + 1
    return ans, {"input": tin, "output": tout, "cache_read": None, "cache_write": None}


def _local_hf(task, arm, seed, qs, db, **kw):
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as e:
        raise RuntimeError(f"local_hf backend needs torch and transformers, not installed here: {e}") from e
    # shortcut: no inference loop yet; wire it when a local model path is approved (never downloads).
    raise NotImplementedError("local_hf inference loop not written; needs a local model path")


def _claude(*a, **kw):
    # STUB: Claude backend waits for owner approval (paid calls). Do not implement before a yes.
    raise NotImplementedError("claude backend is not approved yet")


BACKENDS = {"scripted": _scripted, "local_hf": _local_hf, "claude": _claude}


def run(task, arm, seed, backend, out_dir=None, **kw):
    if task not in sqlseq.FAMILIES:
        raise ValueError(f"unknown task {task!r}")
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}")
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as d:
        qs = sqlseq.gen(seed, task, d)
        db = sqlite3.connect(os.path.join(d, "db.sqlite"))
        try:
            ans, tokens = BACKENDS[backend](task, arm, seed, qs, db, **kw)
        finally:
            db.close()
    rec = {"task": task, "arm": arm, "seed": seed, "backend": backend, "tokens": tokens,
           "tokens_method": "len//4 estimate",
           "score": sqlseq.score(ans, qs), "wall_seconds": time.monotonic() - t0,
           "manifest": manifest.build({"task": task, "arm": arm, "backend": backend}, seed)}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{task}__{arm}__{seed}__{backend}.jsonl")
        with open(path + ".tmp", "w") as f:  # temp + rename: a stopped run never leaves a torn line
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        os.replace(path + ".tmp", path)
    return rec
