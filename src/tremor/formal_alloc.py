"""Bridge to the Lean EP-1 allocation scorer in formal/alloc_score (third scorer).

score(taskset, log) returns {"status": "OK", "score": {...}}, or a status that is never a score:
  INVALID  : Lean missing, toolchain not exactly v4.35.0, static scan refused the sources, build
             failed, axiom audit failed, executable crashed or timed out, or output unreadable.
  REJECTED : the executable refused the input as malformed (exit 2): a malformed task set, a log that is
             not a list, or input that is not JSON; "reason" carries its message. A malformed event is
             not a rejection: it scores with "valid": false (EP1 section 7), like alloc and alloc2.
Verification (static scan, `lake build`, `#print axioms` audit) runs once per process for a given
source hash and Lean binary.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "formal" / "alloc_score"
LEAN_BIN = ROOT / "data" / "tools" / "lean" / "lean-4.35.0-linux_aarch64" / "bin"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
VERSION_PREFIX = "Lean (version 4.35.0,"
ALLOWED_AXIOMS = frozenset({"propext", "Quot.sound", "Classical.choice"})
ALLOWED_IMPORTS = frozenset({"Lean.Data.Json"})  # plus the project's own AllocScore modules
BANNED = re.compile(r"\b(sorry|admit|axiom|native_decide|unsafe|implemented_by|extern|"
                    r"ofReduceBool|skipKernelTC)\b")
FIELDS = ("distinct_passing", "slots", "duplicates", "name_collisions", "surviving_passing",
          "unknown_task_events", "Y_num", "Y_den", "done_releases", "false_done", "extra_work_events", "valid")
OK, INVALID, REJECTED = "OK", "INVALID", "REJECTED"

_THEOREM = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?theorem\s+(\S+)", re.M)
_PRINT = re.compile(r"^#print axioms (\S+)\s*$", re.M)
_DEPENDS = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]", re.S)
_NONE = re.compile(r"'([^']+)' does not depend on any axioms")
_verified = {}


def lean_sources(project=PROJECT):
    return sorted(p for p in Path(project).rglob("*.lean") if ".lake" not in p.parts)


def static_scan(project=PROJECT):
    """Problems found in the Lean sources and project files; empty list when clean."""
    project = Path(project)
    problems, theorems = [], []
    for p in lean_sources(project):
        text = p.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            m = BANNED.search(line)
            if m:
                problems.append(f"{p.name}:{n}: banned token '{m.group(1)}'")
            im = re.match(r"\s*import\s+(.*)", line)
            if im:
                for mod in im.group(1).split():
                    if mod not in ALLOWED_IMPORTS and mod != "AllocScore" and not mod.startswith("AllocScore."):
                        problems.append(f"{p.name}:{n}: import '{mod}' not allowed")
        if p.name != "Axioms.lean":
            theorems += _THEOREM.findall(text)
    axioms_file = project / "Axioms.lean"
    printed = set(_PRINT.findall(axioms_file.read_text(encoding="utf-8"))) if axioms_file.exists() else set()
    problems += [f"theorem {t} has no '#print axioms' line" for t in theorems if f"AllocScore.{t}" not in printed]
    if not theorems:
        problems.append("no theorems found")
    tc = project / "lean-toolchain"
    if not tc.exists() or tc.read_text(encoding="utf-8").strip() != TOOLCHAIN:
        problems.append(f"lean-toolchain is not exactly {TOOLCHAIN}")
    lf = project / "lakefile.toml"
    if not lf.exists() or re.search(r"^\s*\[\[\s*require", lf.read_text(encoding="utf-8"), re.M):
        problems.append("lakefile.toml missing or declares a dependency")
    return problems


def audit_axioms(output, expected):
    """Parse `#print axioms` output. Returns problems: a theorem not reported, or a disallowed axiom."""
    found = {name: [a.strip() for a in axs.split(",") if a.strip()] for name, axs in _DEPENDS.findall(output)}
    found.update({name: [] for name in _NONE.findall(output)})
    problems = [f"{t}: no axiom report" for t in expected if t not in found]
    problems += [f"{t}: disallowed axiom {a}" for t, axs in found.items() for a in axs if a not in ALLOWED_AXIOMS]
    return problems


def _run(cmd, path, timeout, cwd=PROJECT, **kw):
    env = dict(os.environ, PATH=path, CUDA_VISIBLE_DEVICES="")
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, **kw)


def verify(path=None, build_timeout=1800, project=PROJECT):
    """(ok, reason, exe path). `path` is the PATH used to find lean and lake; `project` the Lean project."""
    path = path if path is not None else f"{LEAN_BIN}{os.pathsep}{os.environ.get('PATH', '')}"
    project = Path(project)
    problems = static_scan(project)
    if problems:
        return False, "static scan: " + "; ".join(problems), None
    lean, lake = shutil.which("lean", path=path), shutil.which("lake", path=path)
    if not lean or not lake:
        return False, "lean or lake not found on PATH", None
    try:
        version = _run([lean, "--version"], path, 60, project).stdout.strip()
        if not version.startswith(VERSION_PREFIX):
            return False, f"lean is not 4.35.0: {version!r}", None
        h = hashlib.sha256(f"{lean}\0{lake}\0{version}\0{project.resolve()}".encode())
        for p in lean_sources(project) + [project / "lakefile.toml", project / "lean-toolchain"]:
            h.update(p.read_bytes())
        key = h.hexdigest()
        exe = project / ".lake" / "build" / "bin" / "allocscore"
        if key in _verified:
            return True, "", exe
        b = _run([lake, "build"], path, build_timeout, project)
        if b.returncode != 0:
            return False, f"lake build failed: {(b.stdout + b.stderr)[-2000:]}", None
        a = _run([lake, "env", "lean", "Axioms.lean"], path, build_timeout, project)
        if a.returncode != 0:
            return False, f"axiom audit did not run: {(a.stdout + a.stderr)[-2000:]}", None
        expected = _PRINT.findall((project / "Axioms.lean").read_text(encoding="utf-8"))
        bad = audit_axioms(a.stdout + a.stderr, expected)
        if bad:
            return False, "axiom audit: " + "; ".join(bad), None
        if not exe.exists():
            return False, "executable missing after build", None
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"verification error: {e}", None
    _verified[key] = True
    return True, "", exe


def _valid_score(s):
    return (isinstance(s, dict) and set(s) == set(FIELDS) and type(s["valid"]) is bool
            and all(type(s[k]) is int and s[k] >= 0 for k in FIELDS if k != "valid"))


def score_many(cases, *, path=None, timeout=600, project=PROJECT):
    """Score [(taskset, log), ...] in one executable run: {"status": OK, "scores": [...]} or no score."""
    ok, reason, exe = verify(path, project=project)
    if not ok:
        return {"status": INVALID, "reason": reason}
    try:
        payload = json.dumps([{"taskset": ts, "log": log} for ts, log in cases], allow_nan=False)
    except (TypeError, ValueError) as e:
        return {"status": REJECTED, "reason": f"not JSON: {e}"}
    try:
        r = subprocess.run([str(exe)], input=payload, capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, CUDA_VISIBLE_DEVICES=""))
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": INVALID, "reason": f"executable error: {e}"}
    if r.returncode == 2:
        return {"status": REJECTED, "reason": r.stderr.strip()}
    if r.returncode != 0:
        return {"status": INVALID, "reason": f"executable exit {r.returncode}: {r.stderr.strip()[-500:]}"}
    try:
        out = json.loads(r.stdout)
    except ValueError:
        return {"status": INVALID, "reason": "output is not JSON"}
    if not isinstance(out, list) or len(out) != len(cases) or not all(map(_valid_score, out)):
        return {"status": INVALID, "reason": "output does not have the score schema"}
    return {"status": OK, "scores": out}


def score(taskset, log, *, path=None, timeout=60, project=PROJECT):
    """Lean score of one episode log: {"status": OK, "score": {...}} or INVALID / REJECTED with a reason.
    An OK score with "valid": false is a void episode (EP1 section 7), never a number to use."""
    r = score_many([(taskset, log)], path=path, timeout=timeout, project=project)
    return {"status": OK, "score": r["scores"][0]} if r["status"] == OK else r
