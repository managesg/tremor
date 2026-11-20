import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import memlint  # noqa: E402


class MemLintTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = self.td.name
        with open(os.path.join(self.root, "a.py"), "w") as f:
            f.write("x\n")

    def tearDown(self):
        self.td.cleanup()

    def rec(self, **kw):
        return {"id": "r1", "claim": "c", "source": "a.py:1", **kw}

    def test_clean(self):
        self.assertEqual(memlint.lint(self.rec(), self.root), [])
        self.assertEqual(memlint.lint(self.rec(source="abc1234"), self.root), [])

    def test_no_source(self):
        r = self.rec()
        del r["source"]
        self.assertEqual(memlint.lint(r, self.root), ["source_missing"])
        self.assertEqual(memlint.lint(self.rec(source=" "), self.root), ["source_missing"])

    def test_dangling_and_escape(self):
        self.assertEqual(memlint.lint(self.rec(source="nope.py:3"), self.root), ["source_dangling"])
        self.assertEqual(memlint.lint(self.rec(source="../x"), self.root), ["source_outside_root"])

    def test_secrets(self):
        for s in ("sk-abcdefgh12345", "AKIAABCDEFGHIJKLMNOP", "-----BEGIN PRIVATE KEY-----"):
            self.assertIn("secret_canary", memlint.lint(self.rec(claim=s), self.root))

    def test_more_secret_shapes(self):
        # built at runtime so no secret-looking literal sits in the repo
        shapes = ["gh" + "p_" + "a1" * 20, "github" + "_pat_" + "A" * 30, "xo" + "xb-" + "1234567890-abcdef",
                  "eyJ" + "hbGciOiJIUzI1" + ".eyJ" + "zdWIiOiIxMjM0" + ".sig_part", "AI" + "za" + "B" * 35,
                  "Bea" + "rer " + "z" * 24, "aws_secret" + "_access_key=abc", "tok" + "en=abcdefgh12"]
        for s in shapes:
            out = memlint.lint(self.rec(claim=s), self.root)
            self.assertEqual(out, ["secret_canary"], s[:4])
            self.assertNotIn(s, json.dumps(out))
        self.assertEqual(memlint.lint(self.rec(claim="the token budget is large"), self.root), [])

    def test_sibling_prefix_escape(self):
        sib = self.root + "-evil"
        os.mkdir(sib)
        self.addCleanup(os.rmdir, sib)
        open(os.path.join(sib, "x.py"), "w").close()
        self.addCleanup(os.remove, os.path.join(sib, "x.py"))
        src = "../" + os.path.basename(self.root) + "-evil/x.py"
        self.assertEqual(memlint.lint(self.rec(source=src), self.root), ["source_outside_root"])

    def test_nul_in_source_is_a_violation_not_a_crash(self):
        self.assertEqual(memlint.lint(self.rec(source="a.py\0x"), self.root), ["source_dangling"])

    def test_non_utf8_and_nul_files_are_counted(self):
        with open(os.path.join(self.root, "bad.jsonl"), "wb") as f:
            f.write(b"\xff\xfe not utf8\n")
        with open(os.path.join(self.root, "nul.jsonl"), "wb") as f:
            f.write(b'{"id": "n\x00"}\n')
        out = memlint.lint_dir(self.root)
        self.assertEqual(out, {"records": 2, "clean": 0, "violations": {"unparseable": 2}})

    def test_size(self):
        self.assertIn("too_large", memlint.lint(self.rec(claim="x" * 5000), self.root))

    def test_supersedes_and_ttl(self):
        self.assertIn("supersedes_unknown", memlint.lint(self.rec(supersedes="zz"), self.root))
        self.assertEqual(memlint.lint(self.rec(supersedes="zz"), self.root, {"zz"}), [])
        self.assertIn("ttl_unparseable", memlint.lint(self.rec(valid_until="soon"), self.root))
        self.assertEqual(memlint.lint(self.rec(valid_until="2027-01-01T00:00:00Z"), self.root), [])

    def test_lint_dir_counts_only(self):
        rows = [self.rec(), self.rec(id="r2", supersedes="r1"), self.rec(id="r3", source="gone.py")]
        with open(os.path.join(self.root, "m.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        out = memlint.lint_dir(self.root)
        self.assertEqual(out, {"records": 4, "clean": 2,
                               "violations": {"source_dangling": 1, "unparseable": 1}})

    def test_canary_in_later_memory(self):
        can = {"CANARY-zq81": "t1"}
        trap = self.rec(id="t1", claim="trap CANARY-zq81")
        later = self.rec(id="r9", claim="seen CANARY-zq81 again")
        self.assertEqual(memlint.lint(trap, self.root, canaries=can), [])
        self.assertEqual(memlint.lint(later, self.root, canaries=can), ["note_canary"])
        self.assertEqual(memlint.lint(later, self.root), [])
        with open(os.path.join(self.root, "m.jsonl"), "w") as f:
            f.write(json.dumps(trap) + "\n" + json.dumps(later) + "\n")
        self.assertEqual(memlint.lint_dir(self.root, can)["violations"], {"note_canary": 1})

    def test_relay_lint(self):
        theirs = "".join(chr(97 + i % 26) for i in range(60))
        notes = [{"author": "b", "text": theirs}]
        rl = memlint.relay_lint
        self.assertEqual(rl("x " + theirs[:40] + " y", "a", notes), ["verbatim_relay"])
        self.assertEqual(rl("x " + theirs[:39] + " y", "a", notes), [])  # 39 bytes pass
        self.assertEqual(rl(theirs, "b", notes), [])  # own text passes
        q = '"' + theirs[:45] + '"'
        self.assertEqual(rl(q, "a", notes), ["verbatim_relay"])  # quoted, no source
        self.assertEqual(rl(q, "a", notes, source="a.py:1", root=self.root), [])
        self.assertEqual(rl("> " + theirs[:45], "a", notes, source="https://example.org/n"), [])
        self.assertEqual(rl(q, "a", notes, source="gone.py", root=self.root), ["verbatim_relay"])
        self.assertEqual(rl(q + " " + theirs[:41], "a", notes, source="a.py"), ["verbatim_relay"])  # copy outside quote
        self.assertEqual(rl("\u00e9" * 20, "a", [{"author": "b", "text": "\u00e9" * 20}]), ["verbatim_relay"])  # 40 bytes


if __name__ == "__main__":
    unittest.main()
