"""Admission gate for the R2 batches (L2-O15, L3-O15, L4-O17; ADM:26, ADM:91).

check() is a pure dry run. admit() checks, then claims the admission once
(O_EXCL claim file) and records used=true. Only read-only `git` is run; no
model is called and no run is started.

Key names follow lab/smollm3_smoke_admission.py: batch, valid_from_utc,
valid_until_utc, reserved_gpu_hours. Mapping from the earlier draft:
batch_id->batch, window_start->valid_from_utc, window_end->valid_until_utc,
gpu_hours_limit->reserved_gpu_hours, hosted_usd_limit->hosted_usd_plan and
hosted_usd_stop (protocol section 13; numbers come from the record, no default).

Freeze record (exact keys): batch, protocol_path, protocol_sha256, commit (40
hex), tree, protected_inputs [{path, sha256, custodian}], reserved_gpu_hours,
hosted_usd_plan, hosted_usd_stop, plus the ADM:47 fields config_hash,
model_snapshot, task_family_revision, scorer_ids, contrasts, stopping_rules,
expected_and_max_resources, approval_review_evidence, d1_basis, inherited_pins
(non-empty; presence only). Admission record (exact keys): batch, one_use,
used, valid_from_utc, valid_until_utc (UTC, [from, until)), reserved_gpu_hours,
hosted_usd_plan, hosted_usd_stop, owner_words, freeze_record_sha256.
Paths are relative to repo_root.
"""
import argparse
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

FLOOR_COMMIT = "c0daf55"
_HEX40 = re.compile(r"[0-9a-f]{40}")
_FREEZE_KEYS = {"batch", "protocol_path", "protocol_sha256", "commit", "tree", "protected_inputs",
                "reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop", "config_hash",
                "model_snapshot", "task_family_revision", "scorer_ids", "contrasts",
                "stopping_rules", "expected_and_max_resources", "approval_review_evidence",
                "d1_basis", "inherited_pins"}
_PRESENCE_ONLY = sorted(_FREEZE_KEYS - {"batch", "protocol_path", "protocol_sha256", "commit", "tree",
                                        "protected_inputs", "reserved_gpu_hours", "hosted_usd_plan",
                                        "hosted_usd_stop"})
_ADMISSION_KEYS = {"batch", "one_use", "used", "valid_from_utc", "valid_until_utc",
                   "reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop", "owner_words",
                   "freeze_record_sha256"}
_BATCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
_INPUT_KEYS = {"path", "sha256", "custodian"}


class AdmissionRefused(Exception):
    pass


def _refuse(msg):
    raise AdmissionRefused(msg)


def _unique(pairs):
    d = dict(pairs)
    if len(d) != len(pairs):
        _refuse("duplicate key in record")
    return d


def _bad_const(v):
    _refuse(f"non-finite constant in record: {v}")


def _open_regular(path, root=None):
    """Open a regular file read-only, or refuse. Returns a binary file object (caller closes).

    Closed: (1) with `root` (a real directory path), path must lie under it and is opened openat-style,
    one component at a time from the root's descriptor with O_NOFOLLOW (O_DIRECTORY for parents), so a
    parent directory swapped for a symlink at any moment is refused; (2) after the open, Linux's
    /proc/self/fd link must equal the expected path under root (no /proc/self/fd: refused, not
    skipped); (3) lstat before open, O_NOFOLLOW on the last component, and the descriptor's device and
    inode must equal that lstat; (4) a regular file only.
    NOT closed: the root directory itself being swapped (the caller declares it), and a file whose
    content changes after it is read. Without `root` only (3) and (4) apply (small JSON records).
    """
    dirfd = None
    try:
        before = os.lstat(path)
        if stat.S_ISLNK(before.st_mode):
            _refuse(f"{path} is a symlink")
        if root is None:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        else:
            if not os.path.isdir("/proc/self/fd"):
                _refuse("no /proc/self/fd: cannot verify the opened file (Linux only)")
            rel = os.path.relpath(path, root)
            parts = rel.split(os.sep)
            if rel.startswith("..") or os.path.isabs(rel) or not parts or "" in parts or "." in parts:
                _refuse(f"{path} is not under {root}")
            dirfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            for name in parts[:-1]:
                nxt = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dirfd)
                os.close(dirfd)
                dirfd = nxt
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
    except OSError as e:
        _refuse(f"cannot read {path}: {e}")
    finally:
        if dirfd is not None:
            os.close(dirfd)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            _refuse(f"{path} is not a regular file")
        if (st.st_dev, st.st_ino) != (before.st_dev, before.st_ino):
            _refuse(f"{path} changed between check and open")
        if root is not None and os.readlink(f"/proc/self/fd/{fd}") != os.path.join(root, rel):
            _refuse(f"{path}: opened file is not the file under the root")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def _read(path):
    with _open_regular(path) as f:
        return f.read()


def _load(path, keys, what):
    raw = _read(path)
    try:
        d = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_bad_const)
    except (ValueError, RecursionError) as e:
        _refuse(f"cannot parse {path}: {e}")
    if not isinstance(d, dict):
        _refuse(f"{what} record is not a JSON object")
    if set(d) != keys:
        _refuse(f"{what} record keys differ: unknown {sorted(set(d) - keys)} missing {sorted(keys - set(d))}")
    return d, hashlib.sha256(raw).hexdigest()


def _git(repo_root, *args):
    # Scrub GIT_* so a caller's GIT_DIR and friends cannot redirect the checks or claims.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    r = subprocess.run(["git", "-C", repo_root, *args], capture_output=True, env=env)
    return r.returncode, r.stdout


def _gitline(repo_root, *args):
    rc, out = _git(repo_root, *args)
    return rc, out.decode("utf-8", "replace").strip()


def _num(d, key, what):
    v = d.get(key)
    try:
        ok = not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and v >= 0
    except OverflowError:
        ok = False
    if not ok:
        _refuse(f"{what} {key} is not a finite non-negative number")
    return v


def _caller_num(v, name, positive=False):
    try:
        ok = not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) \
            and (v > 0 if positive else v >= 0)
    except OverflowError:
        ok = False
    if not ok:
        _refuse(f"caller {name} is not a finite {'positive' if positive else 'non-negative'} number")
    return v


def _nonempty(v):
    return not isinstance(v, bool) and v not in (None, 0) and not (isinstance(v, str) and not v.strip()) \
        and not (isinstance(v, (list, dict)) and not v)


def _utc(s, what):
    if isinstance(s, datetime):
        t = s
    else:
        try:
            t = datetime.fromisoformat(s.replace("Z", "+00:00")) if isinstance(s, str) else None
        except ValueError:
            t = None
    if t is None or t.tzinfo is None or t.utcoffset() != timedelta(0):
        _refuse(f"{what} is not a UTC time")
    return t


def _relpath(p, what):
    if not isinstance(p, str) or not p or os.path.isabs(p) or p.startswith(("/", "\\")) \
            or ".." in re.split(r"[\\/]", p) or "\x00" in p:
        _refuse(f"{what} path must be relative with no '..': {p!r}")
    return p


def _input_sha(repo_root, rel):
    _relpath(rel, "protected input")
    root = os.path.realpath(repo_root)
    full = os.path.join(root, rel)
    real = os.path.realpath(full)
    if os.path.commonpath([root, real]) != root:
        _refuse(f"protected input escapes repo_root: {rel}")
    if real != os.path.normpath(full) or os.path.islink(full):
        _refuse(f"protected input is or traverses a symlink: {rel}")
    with _open_regular(full, root) as f:  # chunked: a large input is never loaded whole
        return hashlib.file_digest(f, "sha256").hexdigest()


def check(freeze_record_path, admission_record_path, now_utc, repo_root, **caps):
    _check(freeze_record_path, admission_record_path, now_utc, repo_root, **caps)
    return True


def _check(freeze_record_path, admission_record_path, now_utc, repo_root, *,
           hosted_cap, gpu_cap, max_window_hours, owner_words):
    fr, fr_sha = _load(freeze_record_path, _FREEZE_KEYS, "freeze")
    ad, ad_sha = _load(admission_record_path, _ADMISSION_KEYS, "admission")
    now = _utc(now_utc, "now_utc")
    _caller_num(hosted_cap, "hosted_cap")
    _caller_num(gpu_cap, "gpu_cap")
    _caller_num(max_window_hours, "max_window_hours", positive=True)
    for k in _PRESENCE_ONLY:
        if not _nonempty(fr[k]):
            _refuse(f"freeze {k} missing or empty")
    # commit: exact 40-hex, existing, ancestor of HEAD, at or after the floor, tree matches
    commit = fr["commit"]
    if not isinstance(commit, str) or _HEX40.fullmatch(commit) is None:
        _refuse("pinned commit must be 40 lowercase hex")
    rc, full = _gitline(repo_root, "rev-parse", "--verify", commit + "^{commit}")
    if rc or full != commit:
        _refuse("pinned commit not found or does not resolve to itself")
    if _git(repo_root, "merge-base", "--is-ancestor", commit, "HEAD")[0]:
        _refuse("pinned commit is not an ancestor of HEAD")
    rc, floor = _gitline(repo_root, "rev-parse", "--verify", FLOOR_COMMIT + "^{commit}")
    if rc:
        _refuse(f"floor commit {FLOOR_COMMIT} not found")
    if _git(repo_root, "merge-base", "--is-ancestor", floor, commit)[0]:
        _refuse(f"pinned commit is before {FLOOR_COMMIT}")
    rc, tree = _gitline(repo_root, "rev-parse", commit + "^{tree}")
    if rc or tree != fr["tree"]:
        _refuse("tree hash mismatch")
    # protocol bytes at the pinned commit, not the working tree
    rel = _relpath(fr["protocol_path"], "protocol")
    rc, blob = _git(repo_root, "cat-file", "blob", f"{commit}:{rel}")
    if rc:
        _refuse(f"protocol {rel} not in pinned commit")
    if hashlib.sha256(blob).hexdigest() != fr["protocol_sha256"]:
        _refuse("protocol sha256 mismatch at pinned commit")
    # protected inputs
    pins = fr["protected_inputs"]
    if not isinstance(pins, list) or not pins:
        _refuse("freeze protected_inputs missing or empty")
    for p in pins:
        if not isinstance(p, dict) or set(p) != _INPUT_KEYS:
            _refuse(f"protected input malformed: {p!r}")
        if not _nonempty(p["custodian"]):
            _refuse(f"protected input custodian empty: {p['path']!r}")
        if _input_sha(repo_root, p["path"]) != p["sha256"]:
            _refuse(f"protected input changed: {p['path']}")
    # admission record
    if not isinstance(ad["batch"], str) or _BATCH.fullmatch(ad["batch"]) is None or ad["batch"] != fr["batch"]:
        _refuse("admission batch differs from freeze batch")
    if ad["freeze_record_sha256"] != fr_sha:
        _refuse("admission freeze_record_sha256 does not match the freeze file")
    if ad["one_use"] is not True:
        _refuse("admission one_use is not true")
    if ad["used"] is not False:
        _refuse("admission already used (or used flag not false)")
    start, end = _utc(ad["valid_from_utc"], "valid_from_utc"), _utc(ad["valid_until_utc"], "valid_until_utc")
    if not start <= now < end:
        _refuse("now is outside the admission window [from, until)")
    if end - start > timedelta(hours=max_window_hours):
        _refuse("admission window longer than max_window_hours")
    for key in ("reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop"):
        if _num(ad, key, "admission") > _num(fr, key, "freeze"):
            _refuse(f"admission {key} above freeze limit")
    if ad["reserved_gpu_hours"] > gpu_cap:
        _refuse("admission reserved_gpu_hours above gpu_cap")
    for key in ("hosted_usd_plan", "hosted_usd_stop"):
        if ad[key] > hosted_cap:
            _refuse(f"admission {key} above shared hosted cap")
    if not isinstance(owner_words, str) or not owner_words.strip() or ad["owner_words"] != owner_words:
        _refuse("owner words missing or not equal to the required string")
    return fr_sha, ad_sha, ad["batch"]


def admit(freeze_record_path, admission_record_path, now_utc, repo_root, **caps):
    """check() then claim the batch once, in the git common dir, whatever copy or freeze is shown.

    A claim left behind keeps the batch spent (fail closed).
    """
    fr_sha, ad_sha, batch = _check(freeze_record_path, admission_record_path, now_utc, repo_root, **caps)
    # Shared by every worktree of the repository; one claim per batch, whatever the freeze sha.
    rc, common = _gitline(repo_root, "rev-parse", "--git-common-dir")
    if rc or not common:
        _refuse("cannot resolve the git common dir")
    cdir = os.path.join(os.path.realpath(os.path.join(repo_root, common)), "tremor-admission-claims")
    os.makedirs(cdir, mode=0o700, exist_ok=True)
    st = os.lstat(cdir)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        _refuse("claim directory is a symlink or not a directory")
    if st.st_mode & 0o077 or st.st_uid != os.getuid():
        _refuse("claim directory is not owner-only")
    try:
        fd = os.open(os.path.join(cdir, batch), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        _refuse("batch already claimed")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"freeze_record_sha256": fr_sha,
                   "admission_record": os.path.abspath(admission_record_path),
                   "claimed_utc": datetime.now(timezone.utc).isoformat()}, f)
    ad, ad_sha2 = _load(admission_record_path, _ADMISSION_KEYS, "admission")
    if ad_sha2 != ad_sha:
        _refuse("admission record changed while being claimed")
    ad["used"] = True
    d = os.path.dirname(os.path.abspath(admission_record_path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".admit-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(ad, f, indent=2)
        os.replace(tmp, admission_record_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return True


def plan(freeze_record_path, admission_record_path):
    """Dry-run description only; starts nothing."""
    fr, _ = _load(freeze_record_path, _FREEZE_KEYS, "freeze")
    ad, _ = _load(admission_record_path, _ADMISSION_KEYS, "admission")
    return (f"would admit batch {ad['batch']!r} on commit {fr['commit']} "
            f"window [{ad['valid_from_utc']}, {ad['valid_until_utc']}) "
            f"gpu_hours<={ad['reserved_gpu_hours']} hosted_usd plan<={ad['hosted_usd_plan']} "
            f"stop<={ad['hosted_usd_stop']}; this gate launches nothing")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tremor_admission_gate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "admit"):
        c = sub.add_parser(name)
        c.add_argument("freeze")
        c.add_argument("admission")
        c.add_argument("--now", required=True)
        c.add_argument("--hosted-cap", required=True, type=float)
        c.add_argument("--gpu-cap", required=True, type=float)
        c.add_argument("--max-window-hours", required=True, type=float)
        c.add_argument("--owner-words", required=True)
        c.add_argument("--repo-root", default=".")
    a = ap.parse_args(argv)
    try:
        {"check": check, "admit": admit}[a.cmd](a.freeze, a.admission, a.now, a.repo_root, hosted_cap=a.hosted_cap, gpu_cap=a.gpu_cap,
              max_window_hours=a.max_window_hours, owner_words=a.owner_words)
    except AdmissionRefused as e:
        print(f"REFUSED: {e}")
        return 2
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
