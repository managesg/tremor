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
import sys
import tempfile

from lab import tremor_admission_gate as g

# field -> protocol section (prereg/R2-L2-C-protocol.md section 15 items; limits from section 13)
SECTIONS = {
    "protected_inputs": "15.3", "reserved_gpu_hours": "13", "hosted_usd_plan": "13",
    "hosted_usd_stop": "13", "config_hash": "15.2", "model_snapshot": "15.4",
    "task_family_revision": "15.4", "scorer_ids": "15.4", "contrasts": "15.4",
    "stopping_rules": "15.4", "expected_and_max_resources": "15.4",
    "approval_review_evidence": "15.6", "d1_basis": "15.7", "inherited_pins": "15.8",
}
_NUMBERS = ("reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop")


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


def missing(record):
    """[(field, protocol section)] of the author or custodian fields still empty."""
    out = []
    for k in _NUMBERS:
        v = record.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            out.append((k, SECTIONS[k]))
    pins = record.get("protected_inputs")
    if not isinstance(pins, list) or not pins:
        out.append(("protected_inputs", SECTIONS["protected_inputs"]))
    else:
        for i, p in enumerate(pins):
            if not isinstance(p, dict) or not g._nonempty(p.get("custodian")):
                out.append((f"protected_inputs[{i}].custodian", SECTIONS["protected_inputs"]))
    for k in g._PRESENCE_ONLY:
        if not g._nonempty(record.get(k)):
            out.append((k, SECTIONS[k]))
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
    for k, s in missing(rec):
        print(f"MISSING {k} (protocol section {s})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
