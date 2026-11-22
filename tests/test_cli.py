import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SUBS = ["report", "synth", "sweep", "allowlist", "hazard", "tokens", "memlint", "coupling", "manifest",
        "trap-gen", "seq-gen", "run", "power-parse", "prereg-check"]


def cli(*args, stdin=None):
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
    return subprocess.run([sys.executable, "-W", "ignore", "-m", "murmuration", *args],
                          capture_output=True, text=True, env=env, input=stdin, cwd=ROOT)


class CliTests(unittest.TestCase):
    def test_help_exits_zero(self):
        for s in [None] + SUBS:
            r = cli(*([s] if s else []), "--help")
            self.assertEqual(r.returncode, 0, (s, r.stderr))

    def test_seq_gen_then_scripted_run(self):
        with tempfile.TemporaryDirectory() as d:
            g = json.loads(cli("seq-gen", "shop", os.path.join(d, "seq"), "--seed", "2").stdout)
            self.assertEqual(g["questions"], 40)
            r = cli("run", "shop", "oracle", "--seed", "2", "--out-dir", os.path.join(d, "o"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["score"], 1.0)
            self.assertEqual(len(os.listdir(os.path.join(d, "o"))), 1)

    def test_run_refuses_unscripted_backend(self):
        for b in ("local_hf", "claude"):
            r = cli("run", "shop", "oracle", "--backend", b)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--allow-backend", json.loads(r.stdout)["error"])

    def test_synth_to_report_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            open(p, "w").write(cli("synth", "--seed", "1").stdout)
            rep = json.loads(cli("report", p, "--salt", "x").stdout)
            self.assertGreater(rep["n_events"], 0)
            self.assertEqual(len(rep["policies"]), 4)
            for sub in ("sweep", "allowlist", "hazard"):
                r = cli(sub, p, "--salt", "x")
                self.assertEqual(r.returncode, 0, (sub, r.stderr))
                json.loads(r.stdout)

    def test_events_commands_require_salt_or_explicit_unsafe_flag(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            open(p, "w").write(cli("synth", "--seed", "1").stdout)
            for sub in ("report", "sweep", "allowlist", "hazard"):
                r = cli(sub, p)
                self.assertEqual(r.returncode, 2, sub)
                self.assertIn("--salt", json.loads(r.stdout)["error"])
                self.assertEqual(cli(sub, p, "--unsafe-raw-keys").returncode, 0, sub)

    def test_manifest_root_feeds_sha_and_tree_hash(self):
        with tempfile.TemporaryDirectory() as d:
            for c in (["init", "-q"], ["add", "-A"]):
                subprocess.run(["git", "-C", d, *c], check=True, capture_output=True)
            os.makedirs(os.path.join(d, "src"))
            open(os.path.join(d, "src", "a.py"), "w").write("x=1\n")
            subprocess.run(["git", "-C", d, "add", "-A"], check=True)
            subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "1"], check=True)
            sha = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            rec = json.loads(cli("manifest", "--root", d, "--tree", os.path.join(d, "src"), os.path.join(d, "src")).stdout)
            self.assertEqual(rec["git_sha"], sha)
            from murmuration import manifest
            self.assertEqual(rec["tree_hash"], manifest.tree_hash([os.path.join(d, "src")], d))
            # a symlink under the tree is refused with a clear error, not hashed around
            os.symlink(os.path.join(d, "src", "a.py"), os.path.join(d, "src", "l.py"))
            r = cli("manifest", "--root", d, "--tree", os.path.join(d, "src"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("symlink", json.loads(r.stdout)["error"])

    def test_prereg_check(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "src"))
            os.makedirs(os.path.join(d, "train"))
            open(os.path.join(d, "src", "a.py"), "w").write("x=1\n")
            open(os.path.join(d, "train", "b.py"), "w").write("y=1\n")
            pre = os.path.join(d, "pre.md")
            open(pre, "w").write("Status: DRAFT\ncode_tree_hash:\n")
            r = cli("prereg-check", pre, "--tree", "src", "train", "--root", d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("blank", json.loads(r.stdout)["error"])
            h = json.loads(cli("manifest", "--root", d, "--tree", os.path.join(d, "src"), os.path.join(d, "train")).stdout)["tree_hash"]
            open(pre, "w").write(f"code_tree_hash: {h}\n")
            r = cli("prereg-check", pre, "--tree", "src", "train", "--root", d)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertTrue(json.loads(r.stdout)["match"])
            open(os.path.join(d, "src", "a.py"), "w").write("x=2\n")
            r = cli("prereg-check", pre, "--tree", "src", "train", "--root", d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("mismatch", json.loads(r.stdout)["error"])

    def test_manifest_and_prereg_check_share_the_selected_source_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "lab" / "fixture.py"
            module.parent.mkdir()
            module.write_text("value = 1\n", encoding="utf-8")
            pre = root / "pre.md"

            relative = cli("manifest", "--root", directory, "--tree", "lab")
            absolute = cli("manifest", "--root", directory, "--tree", str(module.parent))
            self.assertEqual(relative.returncode, 0, relative.stdout)
            self.assertEqual(absolute.returncode, 0, absolute.stdout)
            tree_hash = json.loads(relative.stdout)["tree_hash"]
            self.assertEqual(tree_hash, json.loads(absolute.stdout)["tree_hash"])

            pre.write_text(f"code_tree_hash: {tree_hash}\n", encoding="utf-8")
            accepted = cli("prereg-check", str(pre), "--root", directory, "--tree", "lab")
            self.assertEqual(accepted.returncode, 0, accepted.stdout)
            self.assertTrue(json.loads(accepted.stdout)["match"])

            module.write_text("value = 2\n", encoding="utf-8")
            refused = cli("prereg-check", str(pre), "--root", directory, "--tree", "lab")
            self.assertEqual(refused.returncode, 2, refused.stdout)
            self.assertIn("mismatch", json.loads(refused.stdout)["error"])

    def test_power_parse(self):
        r = cli("power-parse", "-", stdin="2026/01/01 00:00:00.000, 100.0, 50\n2026/01/01 00:00:10.000, 100.0, 50\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertAlmostEqual(json.loads(r.stdout)["joules_gpu"], 1000.0)


if __name__ == "__main__":
    unittest.main()
