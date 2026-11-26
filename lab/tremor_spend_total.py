"""Read-only spend total over every ledger in a directory (default runs/spend), owner rule: unknown cost counts at its
upper estimate. total = every charge line + the reservation worst_usd of every reserved call with no charge (failed or
unbilled_unknown calls), as spend.Ledger._sum does. Counts only this directory: any other spend must be added by hand.

    python3 -m lab.tremor_spend_total [LEDGER_DIR] [--batch pilot4]   # --batch also prints one line per call
"""
import argparse
import glob
import json
import os
import sys

from murmuration import spend


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def file_total(path, batch=None):
    """(usd, rows) for one ledger file; rows are per-call tuples (id, in, out, stop, usd, status) for `batch` only."""
    lines = read(path)
    charges = {x["id"]: x for x in lines if x["kind"] == "charge"}
    reserves = {x["id"]: x for x in lines if x["kind"] == "reserve"}
    unbilled = {x["id"] for x in lines if x["kind"] == "unbilled_unknown"}
    usd = sum(x["usd"] for x in charges.values()) + sum(r["worst_usd"] for i, r in reserves.items() if i not in charges)
    rows = []
    for i, r in reserves.items():
        if batch is not None and r.get("batch") != batch:
            continue
        c = charges.get(i)
        if c is None:
            rows.append((i, None, None, None, r["worst_usd"], "UNCHARGED(worst case)" + (" unbilled_unknown" if i in unbilled else "")))
        else:
            u = c.get("usage") or {}
            rows.append((i, u.get("input_tokens"), u.get("output_tokens"), c.get("stop_reason"), c["usd"],
                         "charged" if c.get("usage") else "charged(no usage: worst case)"))
    return usd, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ledger_dir", nargs="?", default=spend.PILOT_LEDGER_DIR)
    ap.add_argument("--batch", choices=sorted(spend.BATCH_SPECS))
    a = ap.parse_args(argv)
    files = sorted(glob.glob(os.path.join(a.ledger_dir, "*.jsonl")))
    total = batch_usd = 0.0
    for f in files:
        usd, rows = file_total(f, a.batch)
        total += usd
        print(f"{os.path.basename(f)} usd={usd:.7f}")
        run = 0.0
        for row in rows if a.batch else ():
            run += row[4]
            print("  ", *row[:4], f"{row[4]:.7f}", f"{run:.7f}", row[5])
        batch_usd += run
    cap = spend.BATCH_SPECS[a.batch]["usd"] if a.batch else None
    over = total > spend.HARD_CAP_USD or (cap is not None and batch_usd > cap)
    print(f"total_usd={total:.7f} cap_total={spend.HARD_CAP_USD}" + (f" batch={a.batch} batch_usd={batch_usd:.7f} cap_batch={cap}" if cap else "")
          + (" OVER CAP: STOP" if over else "") + " (this directory only; add any other spend by hand)")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
