import argparse
import importlib.util
import json
import os
import re
import sys

from . import coupling, hazard, ledger, manifest, memlint, runner, stats, synth, tokens
from .trapbench import sqlseq, traps


def _power():
    # train/ is not a package; load it by path from the repo root
    p = os.path.join(os.path.dirname(__file__), "..", "..", "train", "power.py")
    spec = importlib.util.spec_from_file_location("murmuration_power", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _events(a):
    if not a.salt and not a.unsafe_raw_keys:
        raise ValueError("capability keys would print raw: pass --salt, or --unsafe-raw-keys to accept that")
    rx = re.compile(a.deny_regex, re.S) if a.deny_regex else ledger.DENY_RE
    return ledger.parse(a.paths, rx, a.salt)


def _out(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def build_parser():
    ap = argparse.ArgumentParser(prog="murmuration", description="Permission replay ledger and Wave 1 tools. JSON to stdout, counts only.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def events_parser(name, help):
        p = sub.add_parser(name, help=help)
        p.add_argument("paths", nargs="+")
        p.add_argument("--salt", help="hash capability keys so the output is shareable (required unless --unsafe-raw-keys)")
        p.add_argument("--unsafe-raw-keys", action="store_true", help="print raw capability keys; output is not shareable")
        p.add_argument("--deny-regex", help="override the denial-text regex")
        return p

    r = events_parser("report", "replay policies over transcript files/dirs")
    r.add_argument("--tau", type=float, default=14.0, help="decay days for grow_decay")
    r.add_argument("--promote-after", type=int, default=3)
    r.add_argument("--deny", action="append", default=[], help="ceiling: capability key never promoted")
    r.add_argument("--allow", action="append", default=[], help="initial static allowlist key")
    s = sub.add_parser("synth", help="print a seeded synthetic transcript (illustration only)")
    s.add_argument("--seed", type=int, default=1)
    w = events_parser("sweep", "H1 tau sweep: tau chosen on train sessions, scored on held-out sessions")
    w.add_argument("--taus", type=float, nargs="+", default=[1, 3, 7, 14, 30])
    w.add_argument("--train-frac", type=float, default=0.7)
    w.add_argument("--promote-after", type=int, default=3)
    w.add_argument("--deny", action="append", default=[])
    al = events_parser("allowlist", "mine an allowlist on train sessions, score on test sessions")
    al.add_argument("--train-frac", type=float, default=0.7)
    al.add_argument("--promote-after", type=int, default=3)
    al.add_argument("--deny", action="append", default=[])
    events_parser("hazard", "E1.2 reuse-gap fit: power law vs exponential")
    t = sub.add_parser("tokens", help="token usage: probe key names, or per-session ledger (counts only)")
    t.add_argument("mode", choices=["probe", "ledger"])
    t.add_argument("paths", nargs="+")
    t.add_argument("--salt", help="required for ledger")
    m = sub.add_parser("memlint", help="provenance lint of a directory of *.json/*.jsonl memory records")
    m.add_argument("path")
    c = sub.add_parser("coupling", help="E2.1 co-change pairs from git history before a commit")
    c.add_argument("repo")
    c.add_argument("before_sha")
    c.add_argument("--max-files", type=int, default=50)
    c.add_argument("--top", type=int, default=50)
    mf = sub.add_parser("manifest", help="run manifest, optionally with a tree hash")
    mf.add_argument("--config", default="{}", help="JSON object hashed into the manifest")
    mf.add_argument("--seed", type=int, default=0)
    mf.add_argument("--root", default=".")
    mf.add_argument("--tree", nargs="*", default=[], help="paths to tree-hash")
    pc = sub.add_parser("prereg-check", help="fail unless the code tree still matches a prereg's code_tree_hash")
    pc.add_argument("prereg_file")
    pc.add_argument("--tree", nargs="+", required=True, help="paths to tree-hash, resolved against --root")
    pc.add_argument("--root", default=".")
    tg = sub.add_parser("trap-gen", help="write a planted-wrong-note toy repo")
    tg.add_argument("family", choices=sorted(traps.FAMILIES))
    tg.add_argument("out")
    tg.add_argument("--seed", type=int, default=1)
    sg = sub.add_parser("seq-gen", help="write an E8.3 SQLite sequence and questions.json")
    sg.add_argument("family", choices=sorted(sqlseq.FAMILIES))
    sg.add_argument("out")
    sg.add_argument("--seed", type=int, default=1)
    ru = sub.add_parser("run", help="play one E8.3 episode (scripted backend by default)")
    ru.add_argument("task", choices=sorted(sqlseq.FAMILIES))
    ru.add_argument("arm", choices=runner.ARMS)
    ru.add_argument("--seed", type=int, default=1)
    ru.add_argument("--backend", default="scripted", choices=sorted(runner.BACKENDS))
    ru.add_argument("--allow-backend", action="store_true", help="explicitly request local_hf or claude")
    ru.add_argument("--out-dir")
    pp = sub.add_parser("power-parse", help="integrate nvidia-smi CSV power samples (file or - for stdin)")
    pp.add_argument("csv")
    pp.add_argument("--baseline-csv", help="separate pre-job idle record")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        return _main(a)
    except ValueError as e:
        return _fail(str(e))


def _main(a):
    if a.cmd == "synth":
        sys.stdout.write(synth.generate(a.seed))
    elif a.cmd == "report":
        deny = [ledger.salted(k, a.salt) for k in a.deny]
        allow = [ledger.salted(k, a.salt) for k in a.allow]
        _out(ledger.report(_events(a), a.tau, a.promote_after, deny, allow))
    elif a.cmd == "sweep":
        deny = [ledger.salted(k, a.salt) for k in a.deny]
        _out(ledger.tau_sweep(_events(a), tuple(a.taus), a.train_frac, a.promote_after, deny))
    elif a.cmd == "allowlist":
        deny = {ledger.salted(k, a.salt) for k in a.deny}
        _out(ledger.mine_allowlist(_events(a), a.train_frac, a.promote_after, deny))
    elif a.cmd == "hazard":
        _out(hazard.fit(hazard.gaps(_events(a))))
    elif a.cmd == "tokens":
        if a.mode == "probe":
            _out(tokens.probe(a.paths))
        elif not a.salt:
            return _fail("tokens ledger needs --salt")
        else:
            _out(tokens.ledger(a.paths, a.salt))
    elif a.cmd == "memlint":
        _out(memlint.lint_dir(a.path))
    elif a.cmd == "coupling":
        pairs = coupling.coupling(a.repo, a.before_sha, a.max_files)
        top = sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))[:a.top]
        _out({"pairs_total": len(pairs), "top": [{"a": k[0], "b": k[1], "commits": n} for k, n in top]})
    elif a.cmd == "manifest":
        rec = manifest.build(json.loads(a.config), a.seed, root=a.root)
        try:
            rec["tree_hash"] = manifest.tree_hash(a.tree, a.root) if a.tree else None
        except (ValueError, OSError) as e:
            return _fail(str(e))
        _out(rec)
    elif a.cmd == "prereg-check":
        m = re.search(r"^code_tree_hash:[ \t]*(\S*)", open(a.prereg_file, encoding="utf-8").read(), re.M)
        if not m or not m.group(1):
            return _fail(f"{a.prereg_file}: code_tree_hash is missing or blank; freeze it first")
        try:
            stats.check_prereg(m.group(1), [os.path.join(a.root, t) for t in a.tree])
        except (ValueError, OSError) as e:
            return _fail(str(e))
        _out({"prereg": a.prereg_file, "code_tree_hash": m.group(1), "match": True})
    elif a.cmd == "trap-gen":
        traps.gen(a.seed, a.family, a.out)
        _out({"family": a.family, "seed": a.seed, "out": a.out, "trap": json.load(open(os.path.join(a.out, "trap.json")))})
    elif a.cmd == "seq-gen":
        qs = sqlseq.gen(a.seed, a.family, a.out)
        with open(os.path.join(a.out, "questions.json"), "w") as f:
            json.dump(qs, f)
        _out({"family": a.family, "seed": a.seed, "out": a.out, "questions": len(qs), "split": sqlseq.split_of(a.family)})
    elif a.cmd == "run":
        if a.backend != "scripted" and not a.allow_backend:
            return _fail(f"backend {a.backend!r} is not scripted; pass --allow-backend to request it explicitly")
        try:
            _out(runner.run(a.task, a.arm, a.seed, a.backend, a.out_dir))
        except (RuntimeError, NotImplementedError) as e:
            return _fail(str(e))
    elif a.cmd == "power-parse":
        p = _power()
        read = lambda f: sys.stdin.read() if f == "-" else open(f).read()
        try:
            base = p.baseline_watts(p.parse_csv(read(a.baseline_csv))) if a.baseline_csv else None
            _out(p.sample(p.parse_csv(read(a.csv)), base))
        except ValueError as e:
            return _fail(str(e))
    return 0


def _fail(msg):
    print(json.dumps({"error": msg}), file=sys.stdout)
    return 2


if __name__ == "__main__":
    sys.exit(main())
