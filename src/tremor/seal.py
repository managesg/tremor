"""Evaluator seal: defensive checks that the scorer, answer keys and prereg were not touched by a run. Stdlib only.

A voided run is never scored. Environment checks look at variable NAMES only, never values.
"""
import os
import re

from tremor import manifest

# a credential-looking name: a whole word TOKEN/SECRET/..., or a provider prefix. Names only, values are never read.
_CRED = re.compile(r"(^|_)(API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIALS?|PRIVATE_?KEY|ACCESS_?KEY)(_|$)"
                   r"|^(ANTHROPIC|OPENAI|AWS|AZURE|GOOGLE_APPLICATION|HF|HUGGINGFACE)_", re.I)


class StartRefused(Exception):
    """The run must not start."""


def credential_names(env):
    return sorted(n for n in env if _CRED.search(n))


def start_assert(env, agent_tree, key_paths):
    """Fail if a credential-pattern variable is set, or an answer key lies inside the agent's tree."""
    names = credential_names(env)
    if names:
        raise StartRefused(f"credential-pattern environment variables set: {names}")
    tree = os.path.realpath(agent_tree)
    for k in key_paths:
        real = os.path.realpath(k)
        if os.path.commonpath([tree, real]) == tree:
            raise StartRefused(f"answer key inside the agent tree: {k}")


class Seal:
    def __init__(self, paths, root=None):
        self.paths, self.root = list(paths), root
        self.before = manifest.tree_hash(self.paths, root)  # a missing or symlinked path raises here

    def close(self, outputs=(), canaries=()):
        """Re-hash and scan outputs. Returns {"voided", "reasons", "before", "after"}; voided runs are never scored."""
        reasons = []
        try:
            after = manifest.tree_hash(self.paths, self.root)
        except (OSError, ValueError) as e:  # deleted, replaced by a symlink, or unreadable: all count as a write
            after = None
            reasons.append(f"sealed path unreadable after run: {type(e).__name__}")
        if after is not None and after != self.before:
            reasons.append("sealed scorer, key or prereg changed during the run")
        for out in outputs:
            blob = out.decode("utf-8", "replace") if isinstance(out, bytes) else str(out)
            if any(c and c in blob for c in canaries):
                reasons.append("decoy canary key string found in an output")
                break
        return {"voided": bool(reasons), "reasons": reasons, "before": self.before, "after": after}


def seal(paths, root=None):
    return Seal(paths, root)


def check_unsolvable(task, scored_solved, log):
    """An unsolvable task scored solved means the scorer or the run is broken: append to log, return False (failure)."""
    if task.get("unsolvable") and scored_solved:
        log.append({"event": "unsolvable_scored_solved", "task": task.get("id")})
        return False
    return True


def record_limits(limits):
    """Resource limits are part of the condition: {"limits", "condition"} where condition is the config hash."""
    return {"limits": dict(limits), "condition": manifest.config_hash(limits)}


def count_conditions(limit_sets):
    """Two different limits are two conditions; identical limits are one."""
    return len({record_limits(l)["condition"] for l in limit_sets})
