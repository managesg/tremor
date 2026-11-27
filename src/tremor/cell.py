"""A cell is a directory of plain files; every model, the strongest included, is a cell. Stdlib only.

cells/<id>/  cell.json  policy.json  log.jsonl  log.head  log.lock  (router writes outbox/<task>.json bundles)
cell.json: {"id", "kind", "model"}. policy.json (the ceiling): {"allow": [...], "deny": [...],
"max_tokens": int, "max_seconds": float}; deny wins.
shortcut: policy is not signed (no key handling yet); add policy.json.sig verification before any real run.
"""
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import re
import time
import unicodedata

GENESIS = "0" * 64
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")  # ids and cell names: one path component, never ".."
MAX_NUM = 10**12  # a larger limit is "unlimited" in practice, so it is refused
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def valid_name(s):
    return isinstance(s, str) and NAME.fullmatch(s) is not None and ".." not in s  # fullmatch: no trailing newline


def num(v, what, positive=False):
    """The one validator for every limit, budget and policy number: a real int/float (not bool, not a string),
    finite (NaN fails the chained comparison), within [0, MAX_NUM] ((0, MAX_NUM] if positive)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{what} must be a number, got {type(v).__name__}")
    if not ((0 < v if positive else 0 <= v) and v <= MAX_NUM):
        raise ValueError(f"{what} must be finite and {'positive' if positive else 'non-negative'} (max {MAX_NUM}): {v!r}")
    return v


# The allowlist: canonical model-family key -> the token run that names it. An id maps to a key when that run
# appears contiguously in the id's tokens; an id that maps to no key, or to more than one, is refused. Later
# tokens (dates, '-001', '-preview') do not change the family. A reordered id such as 'claude-5-5-haiku' is
# refused, not guessed: 'sonnet-5-2-fable-5-5' must not read as fable-5-2.
# Scripted and local cells share one key each: two scripted (or two local) cells are never independent.
MODEL_FAMILIES = {
    "haiku-5-5": ("haiku", "5", "5"),
    "sonnet-5-5": ("sonnet", "5", "5"),
    "opus-5-5": ("opus", "5", "5"),
    "fable-5-2": ("fable", "5", "2"),
    "local": ("local",),
    "scripted": ("scripted",),
}


def _tokens(m):
    """NFKC, control/format characters (zero-width, bidi, tags, soft hyphen) dropped, dash variants to '-',
    case-folded; then ASCII letter and digit runs, so every separator and letter/digit boundary is equal."""
    if not isinstance(m, str) or "\x00" in m:
        raise ValueError(f"bad model id {m!r}")
    s = unicodedata.normalize("NFKC", m)
    s = "".join("-" if unicodedata.category(c) == "Pd" or c == "\u2212" else c
                for c in s if unicodedata.category(c) not in ("Cc", "Cf")).casefold()
    if not s.isascii():
        raise ValueError(f"bad model id {m!r}")
    return re.findall(r"[a-z]+|[0-9]+", s)


def model_key(m):
    """The canonical family key of model id m, from the MODEL_FAMILIES allowlist; fail closed: an id that maps to
    no key or to several (e.g. 'scripted-haiku-5-5') raises ValueError, so an unknown spelling is never independent."""
    t = _tokens(m)
    keys = [k for k, r in MODEL_FAMILIES.items() if any(tuple(t[i:i + len(r)]) == r for i in range(len(t)))]
    if len(keys) != 1:
        raise ValueError(f"unknown model id {m!r}: maps to {len(keys)} allowlisted families")
    return keys[0]


family_key = model_key  # keys are families already; kept so callers name the comparison they make


def join(root, *parts):
    """The only path join: root and every part must be plain names, no symlink anywhere on the way, and the
    resolved result must be the joined path itself."""
    if os.path.islink(root):
        raise ValueError(f"symlinked root escapes the cell: {root!r}")
    cur = os.path.realpath(root)
    for p in parts:
        if not valid_name(p):
            raise ValueError(f"bad path component {p!r}")
        cur = os.path.join(cur, p)
        if os.path.islink(cur):
            raise ValueError(f"symlink inside a cell escapes it: {cur!r}")
    if os.path.realpath(cur) != cur:
        raise ValueError(f"path escapes the cell: {cur!r}")
    return cur


def _open(path, flags):
    """Open a join()ed (resolved, absolute) path with no symlink followed anywhere: every directory from '/' is
    opened relative to the previous one with O_NOFOLLOW, then the file itself; finally the open file must be the
    one at the path (same device and inode). A component swapped for a symlink after join() fails closed."""
    parts = path.split("/")
    if not os.path.isabs(path) or os.path.realpath(path) != path or "" in parts[1:]:
        raise ValueError(f"not a resolved path: {path!r}")
    d = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for p in parts[1:-1]:
            nd = os.open(p, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=d)
            os.close(d)
            d = nd
        fd = os.open(parts[-1], flags | NOFOLLOW, 0o644, dir_fd=d)
    except OSError as e:
        if e.errno not in (errno.ELOOP, errno.ENOTDIR):
            raise
        raise ValueError(f"symlink on the way, path escapes the cell: {path!r}") from None
    finally:
        os.close(d)
    try:
        st, at = os.fstat(fd), os.stat(path, follow_symlinks=False)
        if (st.st_dev, st.st_ino) != (at.st_dev, at.st_ino):
            raise ValueError(f"path changed while opening, escapes the cell: {path!r}")
    except BaseException:
        os.close(fd)
        raise
    return fd


def _write(path, text, append=False, exclusive=False):
    fl = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_EXCL if exclusive else os.O_TRUNC)
    with os.fdopen(_open(path, fl), "w") as f:
        f.write(text)


def _read(path):
    with os.fdopen(_open(path, os.O_RDONLY), "rb") as f:
        return f.read()


LOCK_TIMEOUT = 10.0  # seconds; a cell busy for longer fails closed (TimeoutError), never proceeds unlocked


@contextlib.contextmanager
def locked(path, shared=False, create=True):
    """Exclusive (or shared) flock on <cell>/log.lock: one writer appends, checks the chain and writes a bundle at
    a time. Not reentrant: code inside the block calls the unlocked helpers (_append, _chain)."""
    try:
        fd = _open(join(path, "log.lock"), (os.O_RDWR | os.O_CREAT) if create else os.O_RDONLY)
    except FileNotFoundError:
        if create:
            raise
        yield  # no writer has ever run here
        return
    try:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"cell busy: {path!r}")
                time.sleep(0.002)
        yield
    finally:
        os.close(fd)  # closing releases the lock


def _check_policy(policy):
    """Missing, non-finite or non-positive limits are an error, never 'unlimited'."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    for k in ("max_tokens", "max_seconds"):
        num(policy.get(k), k, positive=True)
    for k in ("allow", "deny"):
        v = policy.get(k, [])
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            raise ValueError(f"policy {k} must be a list of strings")


def _check_cell(c):
    if not isinstance(c, dict) or not valid_name(c.get("id")) or not isinstance(c.get("kind"), str):
        raise ValueError("bad cell.json")
    model_key(c.get("model"))


def _words(p):
    return sorted(set(str(p["text"]).lower().split()))


def _plan(p, sid=""):
    g = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{sid}-{p['goal']}")  # plan id in the sub-id: same goal, distinct plans
    return [{"id": f"{g}-{i}", "class": "extract", "payload": {"text": s.strip()}}
            for i, s in enumerate(p["steps"])]


def answer(spec):
    """The pure answer to spec; the verify class recomputes it from scratch, independent of the worker."""
    if spec["class"] == "plan":
        return _plan(spec["payload"], spec.get("id", ""))
    return HANDLERS[spec["class"]](spec["payload"])


def _verify(p):
    return answer({"id": p.get("id", ""), "class": p["class"], "payload": p["payload"]}) == p.get("result")


# class -> pure function of the payload. Stub and strong share them: same spec, same answer.
HANDLERS = {"extract": _words, "plan": _plan, "verify": _verify}
# per-kind scripted cost model: (tokens per payload char // 4 multiplier, simulated seconds)
COSTS = {"stub": (1, 0.0), "scripted_strong": (20, 1.0)}


def create(path, cid, kind, model, policy):
    _check_policy(policy)
    _check_cell({"id": cid, "kind": kind, "model": model})
    os.makedirs(path, exist_ok=True)
    for name, obj in (("cell.json", {"id": cid, "kind": kind, "model": model}), ("policy.json", policy)):
        _write(join(path, name), json.dumps(obj, sort_keys=True))
    return path


def load(path):
    out = {}
    for name in ("cell.json", "policy.json"):
        out[name[:-5]] = json.loads(_read(join(path, name)))
    _check_policy(out["policy"])
    _check_cell(out["cell"])
    return out["cell"], out["policy"]


def work(cell, spec):
    """Run the scripted worker of cell's kind. Returns {answer, actions, tokens, seconds}.

    spec["actions"] (capability keys the task makes the cell attempt) is how tests and perturbations
    exercise the ceiling; a real worker would request them itself.
    """
    kind = cell["kind"]
    if kind not in COSTS:
        raise ValueError(f"unknown cell kind {kind!r}")
    if not isinstance(spec.get("class"), str) or spec["class"] not in HANDLERS:
        raise ValueError(f"unknown task class {spec.get('class')!r}")
    acts = spec.get("actions", [])
    if not isinstance(acts, list) or not all(isinstance(a, str) for a in acts):
        raise ValueError("actions must be a list of strings")
    extra = num(spec.get("extra_seconds", 0.0), "extra_seconds")
    mult, secs = COSTS[kind]
    size = len(json.dumps(spec["payload"], sort_keys=True))
    ans = answer(spec)
    tin = size // 4 * mult
    tout = len(json.dumps(ans, sort_keys=True)) // 4 * mult + 1
    return {"answer": ans, "actions": list(acts), "tokens": {"input": tin, "output": tout}, "seconds": secs + extra}


def _lines(path):
    p = join(path, "log.jsonl")
    return _read(p).splitlines() if os.path.exists(p) else []


def log_count(path):
    return len(_lines(path))


def append_log(path, entry):
    """Append one line carrying the sha256 of the previous line, under the cell lock; the new head hash and line
    count are also recorded outside the log, in log.head, so edits to the last line, truncation and deletion show."""
    with locked(path):
        return _append(path, entry)


def _append(path, entry):
    """append_log without the lock: only for a caller already holding locked(path). Refuses a broken chain."""
    if not _chain(path):
        raise ValueError(f"log chain of {path!r} does not verify; refusing to append")
    lines = _lines(path)
    prev = hashlib.sha256(lines[-1]).hexdigest() if lines else GENESIS
    line = json.dumps({"prev": prev, "entry": entry}, sort_keys=True)
    _write(join(path, "log.jsonl"), line + "\n", append=True)
    head = hashlib.sha256(line.encode()).hexdigest()
    tmp = join(path, "log.head.tmp")  # one writer at a time under the lock, so one tmp name is safe
    _write(tmp, json.dumps({"head": head, "n": len(lines) + 1}))
    os.replace(tmp, join(path, "log.head"))
    return head


def log_entry(path, head):
    """The entry of the line whose hash is `head` (call after verify_log), else None."""
    for line in _lines(path):
        if hashlib.sha256(line).hexdigest() == head:
            return json.loads(line).get("entry")
    return None


def verify_log(path, expected_head=None):
    """True iff the chain is intact AND ends at the recorded head (log.head). expected_head, e.g. a
    bundle's log_head, must additionally be one of the chain's line hashes. Any malformed shape, or a cell
    busy past LOCK_TIMEOUT, is False. Reads under a shared lock, so a concurrent append is never half-seen.
    shortcut: unkeyed hashes, so a full rewrite of log.jsonl plus log.head verifies; sign before real runs."""
    try:
        with locked(path, shared=True, create=False):
            return _chain(path, expected_head)
    except (ValueError, OSError):  # TimeoutError is an OSError
        return False


def _chain(path, expected_head=None):
    try:
        lines = _lines(path)
        hp = join(path, "log.head")
        if not os.path.exists(hp):
            return not lines and expected_head is None
        rec = json.loads(_read(hp))
        prev, hashes = GENESIS, []
        for line in lines:
            row = json.loads(line)
            if not isinstance(row, dict) or row["prev"] != prev:
                return False
            prev = hashlib.sha256(line).hexdigest()
            hashes.append(prev)
        if not isinstance(rec, dict):
            return False
    except (ValueError, KeyError, TypeError, OSError):
        return False
    return (prev, len(lines)) == (rec.get("head", GENESIS), rec.get("n")) and (expected_head is None or expected_head in hashes)
