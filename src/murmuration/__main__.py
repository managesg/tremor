import argparse
import json
import re
import sys

from . import ledger, synth


def main():
    ap = argparse.ArgumentParser(prog="murmuration", description="Permission replay ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="replay policies over transcript files/dirs")
    r.add_argument("paths", nargs="+")
    r.add_argument("--tau", type=float, default=14.0, help="decay days for grow_decay")
    r.add_argument("--promote-after", type=int, default=3)
    r.add_argument("--deny", action="append", default=[], help="ceiling: capability key never promoted")
    r.add_argument("--allow", action="append", default=[], help="initial static allowlist key")
    r.add_argument("--salt", help="hash capability keys so the output is shareable")
    r.add_argument("--deny-regex", help="override the denial-text regex")
    s = sub.add_parser("synth", help="print a seeded synthetic transcript (illustration only)")
    s.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "synth":
        sys.stdout.write(synth.generate(a.seed))
        return
    rx = re.compile(a.deny_regex, re.S) if a.deny_regex else ledger.DENY_RE
    ev = ledger.parse(a.paths, rx, a.salt)
    deny = [ledger.salted(k, a.salt) for k in a.deny]
    allow = [ledger.salted(k, a.salt) for k in a.allow]
    print(json.dumps(ledger.report(ev, a.tau, a.promote_after, deny, allow), indent=2))


main()
