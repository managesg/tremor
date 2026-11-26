"""Sealed-input manifest for the freeze record's protected_inputs (R6-O3/O4). Format and checks only.

The custodian is a named person not yet appointed; this module takes the id as an argument and
never supplies one. Manifest keys: custodian, sealed_utc, sealed_roots (declared directories,
repo-relative), files [{path, sha256, size, kind}], manifest_sha256 (sha256 of the canonical JSON
of the other keys). Every sealed file lies under a sealed root. No git, no network, no model.

RUNNER CONTRACT: the runner must read ONLY the manifest's listed paths, never a directory or a
glob. verify() reports any unlisted entry under a sealed root (recursive, symlinks not followed,
dot files, .DS_Store and __pycache__ included) as `extra` and ok False; the custodian removes it.
The only ignored entry is the manifest file itself, named by the caller (`manifest_path`).

LIMITS: manifest_sha256 shows self-consistency only; nothing here authenticates the custodian or
proves the manifest is the one the custodian made. no_overlap compares two manifests, not disks:
a trivially edited copy with a different hash passes, a stale manifest passes, the visible
manifest is whatever the caller declares, and two sets under one repo_root prove nothing about
hiding the held-out set from the agent. Files are hashed in chunks through one descriptor opened
openat-style from the repo root with O_NOFOLLOW per component, then checked against lstat (device,
inode), /proc/self/fd (Linux only: refused where absent) and one hard link only. A parent directory
swapped for a symlink at any moment is refused. NOT closed: the repo root itself being swapped, and
content changing after it is hashed.
"""
import hashlib
import json
import os
import re
import unicodedata

from lab import tremor_admission_gate as g

_KEYS = {"custodian", "sealed_utc", "sealed_roots", "files", "manifest_sha256"}
_FILE_KEYS = {"path", "sha256", "size", "kind"}
_HEX64 = re.compile(r"[0-9a-f]{64}")


class SealError(Exception):
    pass


def _fail(msg):
    raise SealError(msg)


def _digest(body):
    try:
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as e:
        raise SealError(f"manifest is not plain JSON: {e}") from None
    return hashlib.sha256(raw.encode()).hexdigest()


def _key(p):
    return unicodedata.normalize("NFC", p).casefold()


def _utc(s, what, allow_datetime=False):
    if not isinstance(s, str) and not (allow_datetime and hasattr(s, "tzinfo")):
        _fail(f"{what} must be a string")
    try:
        return g._utc(s, what)
    except g.AdmissionRefused as e:
        raise SealError(str(e)) from None


def _rel(p):
    try:
        g._relpath(p, "sealed input")
    except g.AdmissionRefused as e:
        raise SealError(str(e)) from None
    if p != os.path.normpath(p) or "\\" in p:
        _fail(f"sealed input path is not normalized: {p!r}")
    return p


def _full(repo_root, rel):
    """Absolute path of rel inside repo_root; refuses escapes and any symlink in the chain,
    also when the file itself is missing."""
    root = os.path.realpath(repo_root)
    full = os.path.join(root, _rel(rel))
    if os.path.commonpath([root, os.path.realpath(full)]) != root:
        _fail(f"sealed input escapes repo_root: {rel}")
    if os.path.islink(full) or os.path.realpath(full) != full:
        _fail(f"sealed input is or traverses a symlink: {rel}")
    return full


def _hash(full, rel, repo_root):
    try:
        with g._open_regular(full, os.path.realpath(repo_root)) as f:
            if os.fstat(f.fileno()).st_nlink > 1:
                _fail(f"{rel}: more than one hard link")
            sha = hashlib.file_digest(f, "sha256").hexdigest()
            return sha, f.tell()
    except (g.AdmissionRefused, OSError) as e:
        raise SealError(f"{rel}: {e}") from None


def _custodian(c):
    if not isinstance(c, str) or not c.strip():
        _fail("custodian id is empty")
    return c


def _no_collision(paths, what):
    seen = {}
    for p in paths:
        k = _key(p)
        if k in seen:
            _fail(f"{what} collide after NFC and casefold: {seen[k]!r} and {p!r}")
        seen[k] = p


def _under(p, roots):
    return any(p.startswith(r + "/") for r in roots)  # the slash: h/sub2/x is not under h/sub


def seal(paths, custodian_id, repo_root, now_utc, sealed_roots=None):
    """sealed_roots default: the directories holding the files; a file at the repo root needs an
    explicit root, and a root is never the repo root itself."""
    _custodian(custodian_id)
    sealed = _utc(now_utc, "now_utc", allow_datetime=True)
    if isinstance(paths, (str, bytes)):
        _fail("paths must be a list of paths, not a string")
    paths = list(paths)
    if not paths:
        _fail("no paths to seal")
    if len(set(paths)) != len(paths):
        _fail("duplicate path")
    _no_collision(paths, "paths")
    if sealed_roots is None:
        sealed_roots = sorted({os.path.dirname(p) for p in paths})
    if isinstance(sealed_roots, (str, bytes)):
        _fail("sealed_roots must be a list, not a string")
    roots = sorted(sealed_roots)
    for r in roots:
        if not isinstance(r, str) or not r or not os.path.isdir(_full(repo_root, r)):
            _fail(f"sealed root is not a directory under repo_root: {r!r}")
    files = []
    for p in sorted(paths):
        sha, size = _hash(_full(repo_root, p), p, repo_root)
        files.append({"path": p, "sha256": sha, "size": size,
                      "kind": os.path.splitext(p)[1].lstrip(".").lower() or "file"})
    body = {"custodian": custodian_id, "sealed_utc": sealed.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sealed_roots": roots, "files": files}
    m = {**body, "manifest_sha256": _digest(body)}
    _check_shape(m)
    return m


def _check_shape(m):
    """Manifest structure and own digest; no filesystem."""
    if not isinstance(m, dict) or set(m) != _KEYS:
        _fail("manifest keys differ from the sealed-input format")
    _custodian(m["custodian"])
    _utc(m["sealed_utc"], "sealed_utc")
    roots, files = m["sealed_roots"], m["files"]
    if not isinstance(roots, list) or not roots:
        _fail("manifest sealed_roots missing or empty")
    for r in roots:
        if not isinstance(r, str):
            _fail(f"bad sealed root: {r!r}")
        _rel(r)
    if len(set(roots)) != len(roots):
        _fail("duplicate sealed root")
    if not isinstance(files, list) or not files:
        _fail("manifest files missing or empty")
    seen = set()
    for f in files:
        if not isinstance(f, dict) or set(f) != _FILE_KEYS:
            _fail(f"manifest file entry malformed: {f!r}")
        _rel(f["path"])
        if f["path"] in seen:
            _fail(f"duplicate path in manifest: {f['path']}")
        seen.add(f["path"])
        if not _under(f["path"], roots):
            _fail(f"{f['path']} is not under a sealed root")
        if not isinstance(f["sha256"], str) or _HEX64.fullmatch(f["sha256"]) is None:
            _fail(f"bad sha256 for {f['path']}")
        if isinstance(f["size"], bool) or not isinstance(f["size"], int) or f["size"] < 0:
            _fail(f"bad size for {f['path']}")
        if not isinstance(f["kind"], str) or not f["kind"]:
            _fail(f"bad kind for {f['path']}")
    _no_collision([f["path"] for f in files], "manifest paths")
    body = {k: m[k] for k in m if k != "manifest_sha256"}
    if m["manifest_sha256"] != _digest(body):
        _fail("manifest sha256 does not match its content")
    return m


def _bad_const(v):
    _fail(f"non-finite constant in manifest: {v}")


def _unique(pairs):
    try:
        return g._unique(pairs)
    except g.AdmissionRefused:
        raise SealError("duplicate key in manifest") from None


def load(text_or_path):
    """Parse a manifest from JSON text (starts with '{') or a file path; refuse duplicate keys at any
    depth and NaN/Infinity, then check shape and the self-digest."""
    if isinstance(text_or_path, str) and text_or_path.lstrip().startswith("{"):
        text = text_or_path
    else:
        try:
            text = g._read(text_or_path).decode("utf-8")
        except (g.AdmissionRefused, OSError, UnicodeDecodeError, TypeError) as e:
            raise SealError(f"cannot read manifest: {e}") from None
    try:
        m = json.loads(text, object_pairs_hook=_unique, parse_constant=_bad_const)
    except (ValueError, RecursionError) as e:
        raise SealError(f"cannot parse manifest: {e}") from None
    return _check_shape(m)


def verify(manifest, repo_root, manifest_path=None):
    """Re-hash every sealed file. Returns {"ok": bool, "files": {path: ok|changed|missing}, "extra": [...]}.

    extra = every entry under a sealed root (recursive, symlinks not followed) that the manifest does
    not list; the only exception is manifest_path, the manifest file's own repo-relative name.
    A symlink in a listed path's chain (even for a missing file), an escape, or more than one hard
    link raises SealError.
    """
    m = _check_shape(manifest)
    if manifest_path is not None:
        _rel(manifest_path)
    status, listed = {}, {f["path"] for f in m["files"]}
    for f in m["files"]:
        full = _full(repo_root, f["path"])
        if not os.path.lexists(full):
            status[f["path"]] = "missing"
            continue
        sha, size = _hash(full, f["path"], repo_root)
        status[f["path"]] = "ok" if (sha, size) == (f["sha256"], f["size"]) else "changed"
    root, extra = os.path.realpath(repo_root), set()

    def onerror(e):
        _fail(f"cannot scan {e.filename}: {e}")
    for r in m["sealed_roots"]:
        top = _full(repo_root, r)
        if not os.path.isdir(top):
            continue  # its files already show as missing
        for dirpath, dirnames, filenames in os.walk(top, onerror=onerror):
            names = filenames + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]
            for n in names:
                rel = os.path.relpath(os.path.join(dirpath, n), root)
                if rel not in listed and rel != manifest_path:
                    extra.add(rel)
    extra = sorted(extra)
    return {"ok": all(v == "ok" for v in status.values()) and not extra, "files": status, "extra": extra}


def to_protected_inputs(manifest):
    m = _check_shape(manifest)
    return [{"path": f["path"], "sha256": f["sha256"], "custodian": m["custodian"]} for f in m["files"]]


def no_overlap(visible_manifest, sealed_manifest):
    """True when the two manifests share no path and no sha256 (paths compared after NFC and casefold);
    else SealError. Compares manifests, not disks: see LIMITS in the module docstring."""
    vis, sea = _check_shape(visible_manifest)["files"], _check_shape(sealed_manifest)["files"]
    paths = {_key(f["path"]) for f in vis} & {_key(f["path"]) for f in sea}
    hashes = {f["sha256"] for f in vis} & {f["sha256"] for f in sea}
    if paths or hashes:
        _fail(f"sealed set overlaps the visible set: paths {sorted(paths)} hashes {sorted(hashes)}")
    return True
