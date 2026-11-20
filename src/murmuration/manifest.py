"""Run manifest: tree hash and provenance record. Stdlib only. Missing values are None, never 0."""
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone


def _nolink(p):
    # a symlink is not followed by os.walk, so hashing around it would be a silent false pass
    if os.path.islink(p):
        raise ValueError(f"symlink refused in tree hash: {p}")
    return p


def _files(paths):
    for p in paths:
        p = _nolink(os.path.abspath(p))
        if os.path.isdir(p):
            for d, dirs, names in os.walk(p):
                dirs[:] = sorted(x for x in dirs if x != "__pycache__")
                for x in dirs:
                    _nolink(os.path.join(d, x))
                for n in sorted(names):
                    if not n.endswith(".pyc"):
                        yield _nolink(os.path.join(d, n))
        else:
            yield p


def tree_hash(paths, root=None):
    """sha256 over (path relative to root, bytes). root defaults to the common parent of paths.

    A file move changes the hash; moving the whole checkout (new absolute root) does not.
    """
    files = {os.path.abspath(f) for f in _files(paths)}
    if root is None:
        root = os.path.commonpath([os.path.abspath(p) if os.path.isdir(p) else os.path.dirname(os.path.abspath(p)) for p in paths] or ["."])
    items = []
    for f in sorted(files):
        with open(f, "rb") as fh:
            items.append((os.path.relpath(f, os.path.abspath(root)).replace(os.sep, "/"), hashlib.sha256(fh.read()).digest()))
    h = hashlib.sha256()
    for rel, d in sorted(items):
        h.update(rel.encode() + b"\0" + d)
    return h.hexdigest()


def config_hash(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()


def _git_sha(root):
    # shortcut: git SHA only, dirty tree not flagged; pair with tree_hash for exact code identity.
    try:
        r = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def build(config, seed, price_sheet=None, root="."):
    """price_sheet: source URL/path and date as read at run time, or None if unreadable."""
    return {
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(root),
        "config_hash": config_hash(config),
        "seed": seed,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "price_sheet_source": price_sheet,
    }
