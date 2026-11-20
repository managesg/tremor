"""Provenance lint for memory records (PLAN 5.2, H4). Stdlib only.

Checks that a source exists, not that the claim is true. Violations are short codes;
record contents are never returned or printed.
"""
import json
import os
import re
from collections import Counter
from datetime import datetime

MAX_BYTES = 4096
SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{12,}|PRIVATE KEY"
    r"|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}"
    r"|eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}|AIza[0-9A-Za-z_-]{30,}"
    r"|(?i:bearer\s+[A-Za-z0-9._~+/=-]{20,})|(?i:aws_secret_access_key\s*[=:])"
    r"|(?i:token\s*[=:]\s*[\"']?[A-Za-z0-9._~+/=-]{8,})")
# shortcut: commit pointers are checked by shape only (no git call), upgrade if dangling commits matter.
COMMIT_RE = re.compile(r"[0-9a-f]{7,40}")


def _source_ok(src, root):
    if not isinstance(src, str) or not src.strip():
        return "source_missing"
    if COMMIT_RE.fullmatch(src):
        return None
    path = re.sub(r":\d+(-\d+)?$", "", src)
    if "\0" in path:
        return "source_dangling"
    base = os.path.realpath(root)
    full = os.path.realpath(os.path.join(base, path))
    if full != base and not full.startswith(base + os.sep):
        return "source_outside_root"
    return None if os.path.isfile(full) else "source_dangling"


RELAY_BYTES = 40
QUOTE_RE = re.compile(r'(?m)^>.*$|"[^"\n]*"|\u201c[^\u201d\n]*\u201d')


def relay_lint(text, author, notes, source=None, root="."):
    """Codes for a note write: ['verbatim_relay'] if it holds RELAY_BYTES or more consecutive bytes
    of another author's note, outside a quoted span that carries a source link. notes: [{author, text}]."""
    if not isinstance(text, str):
        return []
    linked = isinstance(source, str) and bool(source.strip()) and (
        re.match(r"https?://\S+", source) is not None or _source_ok(source, root) is None)
    body = text.encode("utf-8")
    if linked:  # a quoted, source-linked span is cut out; \0 keeps windows from bridging the cut
        body = QUOTE_RE.sub("\0", text).encode("utf-8")
    n = RELAY_BYTES
    if len(body) < n:
        return []
    wins = {body[i:i + n] for i in range(len(body) - n + 1)}
    for note in notes:
        if not isinstance(note, dict) or note.get("author") == author or not isinstance(note.get("text"), str):
            continue
        other = note["text"].encode("utf-8")
        if any(other[i:i + n] in wins for i in range(len(other) - n + 1)):
            return ["verbatim_relay"]
    return []


def lint(rec, root, known_ids=(), canaries=None):
    """Return a list of violation codes for one record dict (empty = clean).

    canaries: {canary_string: id of the trap note that holds it}; a canary in any other record
    is "note_canary" (a trap note surfacing in later memory)."""
    if not isinstance(rec, dict):
        return ["not_a_record"]
    v = []
    s = _source_ok(rec.get("source"), root)
    if s:
        v.append(s)
    text = json.dumps(rec, ensure_ascii=False)
    if SECRET_RE.search(text):
        v.append("secret_canary")
    if len(text.encode("utf-8")) > MAX_BYTES:
        v.append("too_large")
    if any(c and c in text and rec.get("id") != origin for c, origin in (canaries or {}).items()):
        v.append("note_canary")
    sup = rec.get("supersedes")
    if sup is not None and sup not in known_ids:
        v.append("supersedes_unknown")
    vu = rec.get("valid_until")
    if vu is not None:
        try:
            datetime.fromisoformat(str(vu).replace("Z", "+00:00"))
        except ValueError:
            v.append("ttl_unparseable")
    return v


def _records(path):
    """Yield (record_or_None) per record in *.json / *.jsonl under path; None = unparseable."""
    for name in sorted(os.listdir(path)):
        p = os.path.join(path, name)
        if not os.path.isfile(p) or not name.endswith((".json", ".jsonl")):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                lines = [f.read()] if name.endswith(".json") else [ln for ln in f if ln.strip()]
        except UnicodeDecodeError:
            yield None  # one unparseable file, counted, never raised
            continue
        for ln in lines:
            try:
                yield json.loads(ln)
            except ValueError:
                yield None


def lint_dir(path, canaries=None):
    """Counts only: {'records', 'clean', 'violations': {code: n}}."""
    recs = list(_records(path))
    ids = {r["id"] for r in recs if isinstance(r, dict) and "id" in r}
    counts, clean = Counter(), 0
    for r in recs:
        found = ["unparseable"] if r is None else lint(r, path, ids, canaries)
        counts.update(found)
        clean += not found
    return {"records": len(recs), "clean": clean, "violations": dict(counts)}
