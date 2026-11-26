import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from lab import tremor_admission_gate as g
from lab import tremor_freeze_skeleton as s

NOW = "2026-12-01T12:00:00Z"
WORDS = "I admit batch L3-C-R2 once"
CAPS = dict(hosted_cap=15, gpu_cap=10, max_window_hours=48, owner_words=WORDS)


def sha(b):
    return hashlib.sha256(b).hexdigest()


class SkeletonTests(unittest.TestCase):
    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True,
                              text=True).stdout.strip()

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        (self.root / "proto.md").write_bytes(b"protocol")
        self.git("add", "."); self.git("commit", "-qm", "floor")
        self.floor = self.git("rev-parse", "HEAD")
        (self.root / "input.txt").write_bytes(b"input")
        self.git("add", "."); self.git("commit", "-qm", "pin")
        old = g.FLOOR_COMMIT
        g.FLOOR_COMMIT = self.floor
        self.addCleanup(setattr, g, "FLOOR_COMMIT", old)
        self.fp = str(self.root / "freeze.json")
        self.ap = str(self.root / "adm.json")

    def sk(self, inputs=("input.txt",)):
        return s.skeleton("proto.md", str(self.root), "L3-C-R2", inputs)

    def write_pair(self, fr):
        Path(self.fp).write_text(json.dumps(fr))
        Path(self.ap).write_text(json.dumps({
            "batch": "L3-C-R2", "one_use": True, "used": False,
            "valid_from_utc": "2026-12-01T00:00:00Z", "valid_until_utc": "2026-12-02T00:00:00Z",
            "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
            "owner_words": WORDS, "freeze_record_sha256": sha(Path(self.fp).read_bytes())}))

    def gate(self):
        return g.check(self.fp, self.ap, NOW, str(self.root), **CAPS)

    def fill(self, r):
        r = json.loads(json.dumps(r))
        for k in g._PRESENCE_ONLY:
            r[k] = f"v-{k}"
        r.update(reserved_gpu_hours=10, hosted_usd_plan=9, hosted_usd_stop=15)
        for p in r["protected_inputs"]:
            p["custodian"] = "alice"
        return r

    def test_computed_fields(self):
        r = self.sk()
        head = self.git("rev-parse", "HEAD")
        self.assertEqual(r["commit"], head)
        self.assertEqual(r["tree"], self.git("rev-parse", "HEAD^{tree}"))
        self.assertEqual(r["protocol_sha256"], sha(b"protocol"))
        self.assertEqual(r["protocol_path"], "proto.md")
        self.assertEqual(r["batch"], "L3-C-R2")
        self.assertEqual(r["protected_inputs"], [{"path": "input.txt", "sha256": sha(b"input"), "custodian": ""}])
        self.assertEqual(set(r), g._FREEZE_KEYS)

    def test_protocol_sha_is_from_commit_not_worktree(self):
        (self.root / "proto.md").write_bytes(b"edited")
        self.assertEqual(self.sk()["protocol_sha256"], sha(b"protocol"))

    def test_no_invented_values(self):
        r = self.sk(())
        self.assertEqual(r["protected_inputs"], [])
        for k in ("reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop"):
            self.assertIsNone(r[k])
        for k in g._PRESENCE_ONLY:
            self.assertEqual(r[k], "")
        self.assertEqual(len(s.missing(r)), 3 + 1 + len(g._PRESENCE_ONLY))

    def test_gate_refuses_unfilled_for_right_reason(self):
        self.write_pair(self.sk())
        with self.assertRaisesRegex(g.AdmissionRefused, "freeze .* missing or empty"):
            self.gate()

    def test_gate_refuses_each_unfilled_field(self):
        filled = self.fill(self.sk())
        for k in list(g._PRESENCE_ONLY) + ["reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop"]:
            with self.subTest(k=k):
                r = dict(filled); r[k] = self.sk()[k]
                self.write_pair(r)
                with self.assertRaises(g.AdmissionRefused):
                    self.gate()
                self.assertIn(k, [m[0] for m in s.missing(r)])
        r = self.fill(self.sk()); r["protected_inputs"][0]["custodian"] = ""
        self.write_pair(r)
        with self.assertRaisesRegex(g.AdmissionRefused, "custodian"):
            self.gate()
        self.assertEqual([m[0] for m in s.missing(r)], ["protected_inputs[0].custodian"])

    def test_filled_is_accepted(self):
        r = self.fill(self.sk())
        self.assertEqual(s.missing(r), [])
        self.write_pair(r)
        self.assertTrue(self.gate())

    def test_missing_without_sections_says_not_found(self):
        m = dict(s.missing(self.sk(()), str(self.root)))
        self.assertEqual(m["d1_basis"], s.NOT_FOUND)
        self.assertEqual(m["protected_inputs"], s.NOT_FOUND)
        self.assertTrue(m["reserved_gpu_hours"] == s.NOT_FOUND)

    def real(self, name):
        """missing() for the real protocol file, committed into the throwaway repo."""
        src = Path(__file__).resolve().parents[2] / "prereg" / name
        (self.root / name).write_bytes(src.read_bytes())
        self.git("add", "."); self.git("commit", "-qm", name)
        r = s.skeleton(name, str(self.root), "B1", ())
        return dict(s.missing(r, str(self.root)))

    def test_real_l2(self):
        m = self.real("R2-L2-C-protocol.md")
        self.assertEqual(m["d1_basis"], "section 15 item 7")
        self.assertEqual(m["inherited_pins"], "section 15 item 8")
        self.assertEqual(m["model_snapshot"], "section 15 item 4")
        self.assertTrue(m["reserved_gpu_hours"].startswith("section 13"))

    def test_real_l3(self):
        m = self.real("R2-L3-C-protocol.md")
        self.assertEqual(m["model_snapshot"], "section 15 item 5")
        self.assertEqual(m["approval_review_evidence"], "section 15 item 7")
        self.assertEqual(m["d1_basis"], "section 15 item 8")
        self.assertEqual(m["inherited_pins"], s.NOT_FOUND)

    def test_real_l4(self):
        m = self.real("R2-L4-C-protocol.md")
        self.assertEqual(m["model_snapshot"], "section 15 item 5")
        self.assertEqual(m["d1_basis"], "section 15 item 8")
        self.assertEqual(m["inherited_pins"], s.NOT_FOUND)

    def test_real_m7(self):
        m = self.real("M7-grover-protocol-draft.md")
        self.assertEqual(m["protected_inputs"], "section 13 item 3")
        self.assertEqual(m["model_snapshot"], "section 13 item 4")
        self.assertEqual(m["approval_review_evidence"], "section 13 item 6")
        self.assertTrue(m["reserved_gpu_hours"].startswith("section 11"))
        self.assertEqual(m["d1_basis"], s.NOT_FOUND)
        self.assertEqual(m["inherited_pins"], s.NOT_FOUND)
        self.assertNotIn("section 15", " ".join(m.values()))

    def commit_proto(self, text):
        (self.root / "proto.md").write_text(text)
        self.git("add", "."); self.git("commit", "-qm", "proto")

    def test_missing_reads_the_pinned_commit_not_head(self):
        self.commit_proto("## 5. What the freeze record must contain\n3. Model snapshot\n")
        rec = self.sk()
        self.commit_proto("## 7. What the freeze record must contain\n9. Model snapshot\n")
        self.assertEqual(dict(s.missing(rec, str(self.root)))["model_snapshot"], "section 5 item 3")

    def test_refs_take_the_freeze_section_and_its_first_match(self):
        r = s._refs("## 2. Other\n1. Model snapshot early\n"
                    "## 5. What the freeze record must contain\n3. Model snapshot a\n4. Model snapshot b\n")
        self.assertEqual(r["model_snapshot"], "section 5 item 3")

    def test_hosted_note_on_every_hosted_limit(self):
        m = self.real("R2-L3-C-protocol.md")
        for k in ("hosted_usd_plan", "hosted_usd_stop"):
            self.assertIn("owner's shared USD 10", m[k])
        self.assertNotIn("USD 10", m["reserved_gpu_hours"])

    def test_bad_inputs_refused(self):
        for bad in ("../x", "/etc/passwd", "absent.txt"):
            with self.assertRaises(g.AdmissionRefused):
                self.sk((bad,))
        with self.assertRaisesRegex(g.AdmissionRefused, "must be relative"):
            s.skeleton("../proto.md", str(self.root), "L3-C-R2")
        with self.assertRaises(g.AdmissionRefused):
            s.skeleton("nope.md", str(self.root), "L3-C-R2")
        with self.assertRaises(g.AdmissionRefused):
            s.skeleton("proto.md", str(self.root), "bad batch!")

    def test_git_env_scrubbed(self):
        head = self.git("rev-parse", "HEAD")
        os.environ["GIT_DIR"] = str(self.root / "nonexistent")
        self.addCleanup(os.environ.pop, "GIT_DIR", None)
        self.assertEqual(self.sk()["commit"], head)

    def test_cli_writes_and_refuses_overwrite(self):
        out = str(self.root / "out.json")
        argv = ["proto.md", "--batch", "L3-C-R2", "--out", out, "--repo-root", str(self.root)]
        self.assertEqual(s.main(argv), 0)
        first = Path(out).read_bytes()
        self.assertEqual(json.loads(first)["commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(s.main(argv + ["--input", "input.txt"]), 2)
        self.assertEqual(Path(out).read_bytes(), first)
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith(".skeleton-")], [])

    def test_cli_refuses_dangling_symlink_out(self):
        out = self.root / "link.json"
        out.symlink_to(self.root / "target.json")
        self.assertEqual(s.main(["proto.md", "--batch", "L3-C-R2", "--out", str(out),
                                 "--repo-root", str(self.root)]), 2)
        self.assertFalse((self.root / "target.json").exists())


if __name__ == "__main__":
    unittest.main()
