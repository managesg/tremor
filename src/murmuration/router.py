"""Router: plain code that reads task specs, runs the named cell, enforces ceiling and budget, writes
the evidence bundle. Task spec: {"id", "class", "payload", "cell", optional "budget":
{"tokens","seconds"}, "expect", "actions"}. verify needs "cell". Stdlib only.
"""
import glob
import hashlib
import json
import os

from murmuration import cell as cellmod


class IndependenceError(Exception):
    """A result may not be verified by a cell of the same model family without a deterministic check."""


# One allowlist and one canonicaliser for the whole package: they live in cell.py.
MODEL_FAMILIES = cellmod.MODEL_FAMILIES
model_key = cellmod.model_key
family_key = cellmod.family_key


def _h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _sha(spec):
    """Binds a bundle to its task; "expect" is the checker, not part of the task."""
    return _h({k: v for k, v in spec.items() if k != "expect"})


def _cap(*vals):
    v = [x for x in vals if x is not None]
    return min(v) if v else None


def _budget(spec):
    """Spec budget: absent is fine; present means an object whose tokens/seconds, if present, are valid numbers."""
    b = spec.get("budget", {})
    if not isinstance(b, dict):
        raise ValueError("budget must be an object")
    return tuple(cellmod.num(b[k], f"budget.{k}") if k in b else None for k in ("tokens", "seconds"))


def _bundle(spec, c, policy, entry, log_head, result):
    """The one bundle builder. run_task and verify both call it, from the log entry (attempted actions, cost) and
    the cell's own files, so status, spend and the policy decision are always recomputed, never read back."""
    acts, cost = entry["actions"], entry["cost"]
    if not isinstance(acts, list) or not all(isinstance(a, str) for a in acts):
        raise ValueError("actions must be a list of strings")
    tokens = cellmod.num(cost["tokens_in"], "tokens_in") + cellmod.num(cost["tokens_out"], "tokens_out")
    seconds = cellmod.num(cost["seconds"], "seconds")
    bt, bs = _budget(spec)
    deny, allow = set(policy.get("deny", [])), set(policy.get("allow", []))
    denied = [a for a in acts if a in deny or a not in allow]  # deny wins; default deny
    if denied:
        status = "escalate"  # a ceiling violation is never executed and never accepted
    elif tokens > _cap(bt, policy["max_tokens"]) or seconds > _cap(bs, policy["max_seconds"]):
        status = "budget_exceeded"
    else:
        status = "done"
    return {"task_id": spec["id"], "class": spec["class"], "cell": c["id"], "kind": c["kind"], "model": c["model"],
            "status": status, "result": result if status == "done" else None,
            "actions_allowed": [a for a in acts if a not in denied] if status == "done" else [],
            "actions_denied": denied, "cost": cost, "spec_sha256": _sha(spec), "log_head": log_head}


def run_task(spec, cell_dir):
    """Execute spec in cell_dir; returns (and writes to outbox/) the evidence bundle. The bundle file is
    <id>.json and is never overwritten; a re-run needs an explicit integer spec["version"] (<id>.v<N>.json).
    The existence check, the log append and the exclusive bundle create run under the cell lock."""
    if not isinstance(spec, dict) or not cellmod.valid_name(spec.get("id")):
        raise ValueError(f"bad task id {spec.get('id') if isinstance(spec, dict) else spec!r}")
    ver = spec.get("version")
    if "version" in spec:
        cellmod.num(ver, "version", positive=True)
        if not isinstance(ver, int):
            raise ValueError("version must be an integer")
    fname = f"{spec['id']}.json" if "version" not in spec else f"{spec['id']}.v{ver}.json"
    c, policy = cellmod.load(cell_dir)
    bpath = cellmod.join(cell_dir, "outbox", fname)
    if os.path.lexists(bpath):
        raise ValueError(f"bundle {fname} exists; pass a new integer 'version' to re-run")
    _budget(spec)
    w = cellmod.work(c, spec)  # handlers are pure; a real worker must check the ceiling before it acts
    cost = {"tokens_in": w["tokens"]["input"], "tokens_out": w["tokens"]["output"], "seconds": w["seconds"]}
    draft = _bundle(spec, c, policy, {"actions": w["actions"], "cost": cost}, None, w["answer"])
    entry = {"task": spec["id"], "status": draft["status"], "actions": w["actions"], "cost": cost, "cell": c["id"],
             "spec_sha256": _sha(spec), "cell_sha256": _h(c), "policy_sha256": _h(policy),
             "result_sha256": _h(draft["result"])}
    with cellmod.locked(cell_dir):
        if os.path.lexists(bpath):
            raise ValueError(f"bundle {fname} exists; pass a new integer 'version' to re-run")
        try:
            os.mkdir(cellmod.join(cell_dir, "outbox"))  # never makedirs: a cell dir moved away is not recreated
        except FileExistsError:
            pass
        bpath = cellmod.join(cell_dir, "outbox", fname)  # re-check the directory after creating it
        bundle = _bundle(spec, c, policy, entry, cellmod._append(cell_dir, entry), draft["result"])
        cellmod._write(bpath, json.dumps(bundle, sort_keys=True), exclusive=True)
    return bundle


LIMITS = ("allow", "deny", "max_tokens", "max_seconds")


def looser(run, named):
    """True if policy `run` permits anything policy `named` does not, on any dimension: an allow entry named
    lacks, a deny entry named has and run lacks, a higher token or seconds cap, or any other key that differs."""
    return (not set(run.get("allow", [])) <= set(named.get("allow", []))
            or not set(named.get("deny", [])) <= set(run.get("deny", []))
            or run["max_tokens"] > named["max_tokens"] or run["max_seconds"] > named["max_seconds"]
            or {k: v for k, v in run.items() if k not in LIMITS} != {k: v for k, v in named.items() if k not in LIMITS})


def _anchored(spec, bundle, cells_dir):
    """The worker cell of a bundle that is exactly what the log and the cell root recompute, status "done";
    else None. Every field is rebuilt by _bundle from cells_dir/<cell> (cell.json, policy.json) and the log
    line at log_head, and compared as canonical JSON. The verdict is bound to the cell the spec names: the
    run cell (bundle cell, = the log entry's cell id and policy hash) must be no looser than spec["cell"]'s
    policy on any dimension; a spec that names no cell is refused. Never raises on malformed input."""
    try:
        wd = cellmod.join(cells_dir, bundle["cell"])
        c, policy = cellmod.load(wd)
        _, npolicy = cellmod.load(cellmod.join(cells_dir, spec["cell"]))
        head = bundle["log_head"]
        if (c["id"] != bundle["cell"] or looser(policy, npolicy)
                or not isinstance(head, str) or not cellmod.verify_log(wd, head)):
            return None
        e = cellmod.log_entry(wd, head)
        if not isinstance(e, dict) or (e.get("task"), e.get("spec_sha256"), e.get("cell_sha256"),
                                       e.get("policy_sha256"), e.get("result_sha256")) != (
                spec["id"], _sha(spec), _h(c), _h(policy), _h(bundle["result"])):  # cell_sha256 binds the cell id
            return None
        rebuilt = _bundle(spec, c, policy, e, head, bundle["result"])
        if rebuilt["status"] != "done" or e.get("status") != "done" or _h(rebuilt) != _h(bundle):
            return None
        return c
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RecursionError):
        return None


def verify(spec, bundle, cells_dir, *, verifier_dir=None):
    """Accept/reject a bundle for spec: one check on every path. The bundle must be what _anchored recomputes
    from cells_dir/<bundle["cell"]> and its log (status, spend, policy decision, model, result hash), on a cell
    no looser than cells_dir/<spec["cell"]>. Then the
    deterministic check (spec["expect"]); else a verifier cell of a different model family recomputes the answer."""
    wc = _anchored(spec, bundle, cells_dir)
    if wc is None:
        return False
    if "expect" in spec:
        try:
            return _h(bundle["result"]) == _h(spec["expect"])
        except (TypeError, ValueError, RecursionError):  # an expect JSON cannot hold matches nothing
            return False
    if verifier_dir is None:
        raise IndependenceError("no deterministic check and no verifier cell")
    if os.path.realpath(verifier_dir) != cellmod.join(cells_dir, os.path.basename(os.path.realpath(verifier_dir))):
        raise ValueError("verifier cell is not under the cells root")
    v, _ = cellmod.load(verifier_dir)
    if cellmod.family_key(v["model"]) == cellmod.family_key(wc["model"]):
        raise IndependenceError(f"verifier model {v['model']!r} is the worker's family; needs another family or the owner")
    vb = run_task({"id": f"verify-{spec['id']}", "version": cellmod.log_count(verifier_dir) + 1, "class": "verify",
                   "payload": {"id": spec["id"], "class": spec["class"], "payload": spec["payload"], "result": bundle["result"]}},
                  verifier_dir)
    return vb["status"] == "done" and vb["result"] is True


def run_dir(tasks_dir, cells_dir):
    """Run every tasks_dir/*.json on the cell named in spec["cell"]; returns bundles in file order."""
    out = []
    for p in sorted(glob.glob(os.path.join(tasks_dir, "*.json"))):
        with open(p) as f:
            spec = json.load(f)
        if not isinstance(spec, dict):
            raise ValueError("task spec must be an object")
        out.append(run_task(spec, cellmod.join(cells_dir, spec.get("cell"))))  # join: plain name, no symlink
    return out
