"""W1-10 episode runner. run() plays one E8.3 SQL sequence and returns one record; stdlib only.

task is a sqlseq family name. Missing values are None, never 0 (scripted has no cache tokens).
"""
import json
import os
import sqlite3
import tempfile
import time
import urllib.parse

from murmuration import backend_claude, manifest, spend
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


def _claude(task, arm, seed, qs, db, *, allow_backend=False, spend_ledger=None, price_sheet=None, api_key=None,
            model="claude-sonnet-5-5", base_url=backend_claude.DEFAULT_BASE_URL, max_tokens=300, temperature=0.0,
            token_cap=80_000, wall_seconds=300.0, ceiling=spend.DEFAULT_CEILING, max_calls=None,
            allow_host=None, dry_run=False, **kw):
    """One request per question: the model writes a SELECT, we run it read-only. Paid; opt-in on every axis.

    dry_run: loopback fake server only; any api_key is discarded so no real key can leave the process."""
    if not allow_backend:
        raise RuntimeError("claude backend needs allow_backend=True (CLI: --allow-backend)")
    if not spend_ledger or not price_sheet:
        raise RuntimeError("claude backend needs an explicit spend_ledger path and price_sheet path")
    if dry_run:
        host = urllib.parse.urlsplit(base_url).hostname
        if host not in backend_claude.LOOPBACK:
            raise RuntimeError("dry_run needs a loopback base_url (the fake server)")
        api_key, allow_host = "dry-run-no-key", host
    led = spend.Ledger(spend_ledger, spend.PriceSheet.load(price_sheet), ceiling, max_calls)
    cl = backend_claude.ClaudeClient(api_key, led, base_url, allow_host=allow_host)
    ep = backend_claude.Episode(f"{task}:{arm}:{seed}", token_cap, wall_seconds)
    schema = "\n".join(r[0] for r in db.execute("SELECT sql FROM sqlite_master WHERE type='table'"))
    system = "You answer questions about a SQLite database by replying with exactly one SELECT statement and nothing else. " \
             "Make the statement return the final answer as a single value (money in dollars, two decimals)."
    ans, tok = {}, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for q in qs:
        hint = f"\nNote: {NOTE}" if arm in ("oracle", "raw-notes") else ""
        rec = cl.call(ep, f"{ep.id}:q{q['id']}:a0", model,
                      [{"role": "user", "content": f"Schema:\n{schema}{hint}\nQuestion: {q['q']}"}],
                      max_tokens, temperature, system)
        u = rec["usage"]
        tok["input"] += u.get("input_tokens") or 0
        tok["output"] += u.get("output_tokens") or 0
        tok["cache_read"] += u.get("cache_read_input_tokens") or 0
        tok["cache_write"] += u.get("cache_creation_input_tokens") or 0
        if rec["void"]:
            break
        ans[q["id"]] = _run_sql(db, rec["text"], q["kind"])
    extra = {"void": ep.void, "model_requested": model,
             "models_returned": sorted({r["returned_model"] for r in ep.records}),
             "usd": ep.usd, "calls": len(ep.records), "price_sheet": led.sheet.source()}
    return ans, tok, extra


def _run_sql(db, text, kind):
    sql = text.strip().strip("`").removeprefix("sql").strip().rstrip(";")
    if not sql.lower().startswith("select") or ";" in sql:
        return None  # not a single SELECT: counts as a wrong answer
    try:
        v = db.execute(sql).fetchone()
    except sqlite3.Error:
        return None
    if not v or v[0] is None:
        return None
    try:
        return str(int(v[0])) if kind == "count" else f"{float(v[0]):.2f}"
    except (TypeError, ValueError):
        return None


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
            out = BACKENDS[backend](task, arm, seed, qs, db, **kw)
            ans, tokens, extra = out if len(out) == 3 else (*out, {})
        finally:
            db.close()
    rec = {"task": task, "arm": arm, "seed": seed, "backend": backend, "tokens": tokens,
           "tokens_method": "api usage" if backend == "claude" else "len//4 estimate",
           "score": None if extra.get("void") else sqlseq.score(ans, qs), "wall_seconds": time.monotonic() - t0,
           "manifest": manifest.build({"task": task, "arm": arm, "backend": backend}, seed, extra.get("price_sheet"))}
    rec.update({k: v for k, v in extra.items() if k != "price_sheet"})
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{task}__{arm}__{seed}__{backend}.jsonl")
        with open(path + ".tmp", "w") as f:  # temp + rename: a stopped run never leaves a torn line
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        os.replace(path + ".tmp", path)
    return rec
