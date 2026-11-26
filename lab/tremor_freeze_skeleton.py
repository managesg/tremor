"""Freeze-record skeleton for lab/tremor_admission_gate.py.

Fills only what git and the files can compute (protocol path and sha256 at the
pinned commit, the commit = current HEAD, its tree, protected-input sha256).
Every field that needs an author or custodian decision is None, '' or [] so the
gate REFUSES the record until a person fills it. No default number, limit,
window or custodian is ever invented. Reuses the gate's scrubbed `git` helper.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

from lab import tremor_admission_gate as g

# field -> (heading regex of the section that owns it, regex of the freeze-record item that names it).
# Numbers are looked up in the given protocol's own text, never assumed (L2/L3/L4/M7 number differently).
_LIMITS = r"Resource and budget limits|Spend"
_FREEZE = r"What the freeze record must contain"
_MODEL = r"Model snapshot"
_FIELDS = {
    "protected_inputs": r"Protected inputs", "config_hash": r"Code tree hash",
    "model_snapshot": _MODEL, "task_family_revision": _MODEL, "scorer_ids": _MODEL,
    "contrasts": _MODEL, "stopping_rules": _MODEL, "expected_and_max_resources": _MODEL,
    "approval_review_evidence": r"Approval and review evidence", "d1_basis": r"D1 basis",
    "inherited_pins": r"inherited from the M3",
}
_LIMIT_FIELDS = ("reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop")
HOSTED_NOTE = ("effective hosted cap is the caller's cap (the owner's shared USD 10), "
               "never the protocol's own stop")
NOT_FOUND = "section not found"


def skeleton(protocol_path, repo_root, batch, protected_inputs=()):
    if not isinstance(batch, str) or g._BATCH.fullmatch(batch) is None:
        g._refuse(f"bad batch id: {batch!r}")
    rel = g._relpath(protocol_path, "protocol")
    rc, commit = g._gitline(repo_root, "rev-parse", "--verify", "HEAD^{commit}")
    if rc or g._HEX40.fullmatch(commit) is None:
        g._refuse("cannot resolve HEAD")
    rc, tree = g._gitline(repo_root, "rev-parse", commit + "^{tree}")
    if rc:
        g._refuse("cannot resolve the tree of HEAD")
    rc, blob = g._git(repo_root, "cat-file", "blob", f"{commit}:{rel}")
    if rc:
        g._refuse(f"protocol {rel} not in HEAD")
    rec = {k: None for k in g._FREEZE_KEYS}
    rec.update(batch=batch, protocol_path=rel, protocol_sha256=hashlib.sha256(blob).hexdigest(),
               commit=commit, tree=tree,
               protected_inputs=[{"path": p, "sha256": g._input_sha(repo_root, p), "custodian": ""}
                                 for p in protected_inputs])
    for k in g._PRESENCE_ONLY:
        rec[k] = ""
    return rec


def _refs(text):
    """{field: reference} found in this protocol's headings and freeze-record items."""
    heads, items, cur = [], [], None
    for line in text.split("\n"):
        m = re.match(r"## (\d+a?)\. (.*)", line)
        if m:
            heads.append((m.group(1), m.group(2)))
            cur = m.group(1) if re.search(_FREEZE, m.group(2)) else None
            continue
        if cur is not None:
            n = re.match(r"(\d+)\. (.*)", line)
            if n:
                items.append([n.group(1), n.group(2)])
    refs = {}
    fz = next((n for n, h in heads if re.search(_FREEZE, h)), None)
    for k, rx in _FIELDS.items():
        it = next((i for i, tx in items if re.search(rx, tx)), None)
        if fz and it:
            refs[k] = f"section {fz} item {it}"
    lim = next((n for n, h in heads if re.search(_LIMITS, h)), None)
    for k in _LIMIT_FIELDS:
        if lim:
            refs[k] = f"section {lim}"
    return refs


def missing(record, repo_root="."):
    """[(field, reference)] of author or custodian fields still empty. The reference is looked up in
    the record's own protocol at its pinned commit; 'section not found' when that file lacks it."""
    refs = {}
    try:
        rc, blob = g._git(repo_root, "cat-file", "blob", f"{record.get('commit')}:{record.get('protocol_path')}")
        if not rc:
            refs = _refs(blob.decode("utf-8", "replace"))
    except (TypeError, ValueError):
        pass

    def ref(k):
        r = refs.get(k, NOT_FOUND)
        return f"{r}; {HOSTED_NOTE}" if k in ("hosted_usd_plan", "hosted_usd_stop") else r

    out = []
    for k in _LIMIT_FIELDS:
        v = record.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            out.append((k, ref(k)))
    pins = record.get("protected_inputs")
    if not isinstance(pins, list) or not pins:
        out.append(("protected_inputs", ref("protected_inputs")))
    else:
        for i, p in enumerate(pins):
            if not isinstance(p, dict) or not g._nonempty(p.get("custodian")):
                out.append((f"protected_inputs[{i}].custodian", ref("protected_inputs")))
    for k in g._PRESENCE_ONLY:
        if not g._nonempty(record.get(k)):
            out.append((k, ref(k)))
    return out


def write_new(record, out):
    """Atomic, refuses to overwrite: hard-link a finished temp file into place."""
    d = os.path.dirname(os.path.abspath(out))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".skeleton-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write("\n")
        try:
            os.link(tmp, out)
        except FileExistsError:
            g._refuse(f"{out} already exists; not overwriting")
    finally:
        os.unlink(tmp)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tremor_freeze_skeleton")
    ap.add_argument("protocol")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--input", action="append", default=[], help="protected input path (repeatable)")
    a = ap.parse_args(argv)
    try:
        rec = skeleton(a.protocol, a.repo_root, a.batch, a.input)
        write_new(rec, a.out)
    except g.AdmissionRefused as e:
        print(f"REFUSED: {e}")
        return 2
    for k, s in missing(rec, a.repo_root):
        print(f"MISSING {k} ({s})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
