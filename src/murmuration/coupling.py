"""E2.1 co-change coupling from git history before a cutoff."""
import subprocess
from collections import Counter
from itertools import combinations


# shortcut: counts raw pair co-occurrence per commit (commits touching >50 files skipped as
# bulk edits), no rename tracking, no weighting by recency; upgrade if E2.1 needs normalisation.
def coupling(repo_path, before_sha, max_files=50):
    """{(file_a, file_b): commits touching both}, using history reachable from before_sha."""
    if not isinstance(before_sha, str) or not before_sha or before_sha.startswith("-"):
        raise ValueError("before_sha must be a revision, not an option")  # git would read '-…' as a flag
    git = ["git", "-C", repo_path, "-c", "core.quotePath=false"]
    if not subprocess.run(git + ["for-each-ref", "--count=1"], capture_output=True, text=True,
                          check=True).stdout.strip():
        return {}  # no refs: an empty repo has no history to couple
    # no --no-merges needed: git log --name-only lists no files for a merge, so a merge adds no
    # pairs and its parents' commits are counted once each (pinned by the merge test)
    out = subprocess.run(git + ["log", "--name-only", "--format=%x00", before_sha],
                         capture_output=True, text=True, check=True, encoding="utf-8", errors="replace").stdout
    pairs = Counter()
    for c in out.split("\0"):
        files = sorted({f for f in c.splitlines() if f})
        if 2 <= len(files) <= max_files:
            pairs.update(combinations(files, 2))
    return dict(pairs)
