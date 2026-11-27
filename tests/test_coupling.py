import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor import coupling  # noqa: E402


def git(d, *a):
    return subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                          capture_output=True, text=True, check=True).stdout.strip()


def commit(d, files, msg):
    for f in files:
        with open(os.path.join(d, f), "a") as fh:
            fh.write(msg + "\n")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", msg)


class CouplingTest(unittest.TestCase):
    def test_option_like_revision_is_refused(self):
        # Row-155 review defect 6: "--output=<file>" reached git as an option and wrote the file.
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            commit(d, ["a", "b"], "1")
            target = os.path.join(d, "pwned")
            with self.assertRaises(ValueError):
                coupling.coupling(d, "--output=" + target)
            self.assertFalse(os.path.exists(target))

    def test_cutoff(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            commit(d, ["a", "b"], "1")
            commit(d, ["a", "b", "c"], "2")
            cut = git(d, "rev-parse", "HEAD")
            commit(d, ["a", "c"], "3")
            commit(d, ["a", "b"], "4")
            self.assertEqual(coupling.coupling(d, cut),
                             {("a", "b"): 2, ("a", "c"): 1, ("b", "c"): 1})
            self.assertEqual(coupling.coupling(d, "HEAD")[("a", "b")], 3)

    def test_empty_repo_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            self.assertEqual(coupling.coupling(d, "HEAD"), {})

    def test_not_a_repo_still_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(subprocess.CalledProcessError):
                coupling.coupling(d, "HEAD")

    def test_non_ascii_path_is_not_quoted(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            commit(d, ["caf\u00e9.txt", "b"], "1")
            self.assertEqual(coupling.coupling(d, "HEAD"), {("b", "caf\u00e9.txt"): 1})

    def test_merge_commit_adds_no_pairs_of_its_own(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q", "-b", "main")
            commit(d, ["a", "b"], "1")
            git(d, "checkout", "-q", "-b", "side")
            commit(d, ["c", "d"], "2")
            git(d, "checkout", "-q", "main")
            commit(d, ["a", "e"], "3")
            git(d, "merge", "-q", "--no-ff", "-m", "merge", "side")
            self.assertEqual(coupling.coupling(d, "HEAD"), {("a", "b"): 1, ("c", "d"): 1, ("a", "e"): 1})


if __name__ == "__main__":
    unittest.main()
