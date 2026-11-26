import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab import tremor_admission_gate as g
from lab import tremor_sealed_inputs as s

NOW = "2026-12-01T12:00:00Z"
WORDS = "I admit batch L3-C-R2 once"
PRESENCE = ["config_hash", "model_snapshot", "task_family_revision", "scorer_ids", "contrasts",
            "stopping_rules", "expected_and_max_resources", "approval_review_evidence",
            "d1_basis", "inherited_pins"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def reseal(m, **kv):
    """Rebuild a manifest with a correct digest after editing fields (to reach deeper checks)."""
    body = {k: v for k, v in {**m, **kv}.items() if k != "manifest_sha256"}
    return {**body, "manifest_sha256": s._digest(body)}


class SealedTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "held").mkdir()
        (self.root / "held" / "a.json").write_bytes(b"alpha")
        (self.root / "held" / "b.csv").write_bytes(b"bravo")
        self.paths = ["held/a.json", "held/b.csv"]
        self.m = s.seal(self.paths, "cust-1", str(self.root), NOW)

    def v(self, m=None):
        return s.verify(m or self.m, str(self.root))

    def refused(self, fn, *a, match=None, **kw):
        with self.assertRaises(s.SealError) as cm:
            fn(*a, **kw)
        if match:
            self.assertIn(match, str(cm.exception))

    # format and happy path
    def test_seal_format(self):
        self.assertEqual(set(self.m), {"custodian", "sealed_utc", "sealed_roots", "files", "manifest_sha256"})
        self.assertEqual(self.m["sealed_roots"], ["held"])
        self.assertEqual(self.m["custodian"], "cust-1")
        self.assertEqual(self.m["sealed_utc"], NOW)
        self.assertEqual(self.m["files"][0], {"path": "held/a.json", "sha256": sha(b"alpha"), "size": 5, "kind": "json"})
        self.assertEqual([f["path"] for f in self.m["files"]], self.paths)
        json.dumps(self.m)

    def test_seal_order_independent(self):
        self.assertEqual(s.seal(self.paths[::-1], "cust-1", str(self.root), NOW), self.m)

    def test_datetime_now(self):
        from datetime import datetime, timezone
        self.assertEqual(s.seal(self.paths, "c", str(self.root), datetime(2026, 12, 1, 12, tzinfo=timezone.utc))["sealed_utc"], NOW)

    def test_verify_ok(self):
        r = self.v()
        self.assertEqual(r, {"ok": True, "files": {p: "ok" for p in self.paths}, "extra": []})

    def test_kind_without_suffix(self):
        (self.root / "held" / "noext").write_bytes(b"x")
        self.assertEqual(s.seal(["held/noext"], "c", str(self.root), NOW)["files"][0]["kind"], "file")

    # tampering
    def test_changed_content(self):
        (self.root / "held" / "a.json").write_bytes(b"ALPHA")
        r = self.v()
        self.assertFalse(r["ok"])
        self.assertEqual(r["files"], {"held/a.json": "changed", "held/b.csv": "ok"})

    def test_changed_same_hash_cannot_hide_size(self):
        m = reseal(self.m, files=[{**self.m["files"][0], "size": 6}, self.m["files"][1]])
        self.assertEqual(self.v(m)["files"]["held/a.json"], "changed")

    def test_missing(self):
        os.unlink(self.root / "held" / "b.csv")
        r = self.v()
        self.assertFalse(r["ok"])
        self.assertEqual(r["files"]["held/b.csv"], "missing")

    def test_extra(self):
        (self.root / "held" / "c.txt").write_bytes(b"new")
        r = self.v()
        self.assertFalse(r["ok"])
        self.assertEqual(r["extra"], ["held/c.txt"])
        self.assertEqual(set(r["files"].values()), {"ok"})

    def test_repo_root_file_needs_explicit_root_and_no_root_is_repo_root(self):
        (self.root / "top.txt").write_bytes(b"t")
        self.refused(s.seal, ["top.txt"], "c", str(self.root), NOW)
        self.refused(s.seal, ["top.txt"], "c", str(self.root), NOW, sealed_roots=[""])
        self.refused(s.seal, ["held/a.json"], "c", str(self.root), NOW, sealed_roots=["nodir"])
        self.refused(s.seal, ["held/a.json"], "c", str(self.root), NOW, sealed_roots="held")
        self.refused(s.seal, ["held/a.json"], "c", str(self.root), NOW, sealed_roots=["other"])

    def test_file_outside_declared_roots_refused(self):
        (self.root / "other").mkdir()
        (self.root / "other" / "o.txt").write_bytes(b"o")
        self.refused(s.seal, ["held/a.json", "other/o.txt"], "c", str(self.root), NOW,
                     sealed_roots=["held"], match="not under a sealed root")

    def test_extra_is_recursive_and_reports_hidden_names(self):
        (self.root / "held" / "sub" / "deep").mkdir(parents=True)
        for n in ("sub/deep/x.bin", ".DS_Store", "sub/__pycache__x.pyc", ".hidden"):
            (self.root / "held" / n).write_bytes(b"x")
        r = self.v()
        self.assertFalse(r["ok"])
        self.assertEqual(r["extra"], ["held/.DS_Store", "held/.hidden", "held/sub/__pycache__x.pyc",
                                      "held/sub/deep/x.bin"])

    def test_extra_symlink_reported_not_followed(self):
        (self.root / "outside").mkdir()
        (self.root / "outside" / "big.txt").write_bytes(b"o")
        os.symlink(self.root / "outside", self.root / "held" / "dirlink")
        os.symlink(self.root / "outside" / "big.txt", self.root / "held" / "filelink")
        self.assertEqual(self.v()["extra"], ["held/dirlink", "held/filelink"])

    def test_manifest_file_itself_is_the_only_ignored_entry(self):
        (self.root / "held" / "MANIFEST.json").write_text(json.dumps(self.m))
        self.assertEqual(self.v()["extra"], ["held/MANIFEST.json"])
        self.assertTrue(s.verify(self.m, str(self.root), manifest_path="held/MANIFEST.json")["ok"])
        (self.root / "held" / "other.json").write_bytes(b"o")
        self.assertEqual(s.verify(self.m, str(self.root), manifest_path="held/MANIFEST.json")["extra"],
                         ["held/other.json"])
        self.refused(s.verify, self.m, str(self.root), "../x")

    def test_missing_root_dir_reports_files_missing(self):
        for n in ("a.json", "b.csv"):
            os.unlink(self.root / "held" / n)
        os.rmdir(self.root / "held")
        r = self.v()
        self.assertFalse(r["ok"])
        self.assertEqual(set(r["files"].values()), {"missing"})

    def test_renamed(self):
        os.rename(self.root / "held" / "a.json", self.root / "held" / "z.json")
        r = self.v()
        self.assertFalse(r["ok"])
        self.assertEqual(r["files"]["held/a.json"], "missing")
        self.assertEqual(r["extra"], ["held/z.json"])

    def test_symlink_at_verify(self):
        os.unlink(self.root / "held" / "a.json")
        os.symlink(self.root / "held" / "b.csv", self.root / "held" / "a.json")
        self.refused(self.v, match="symlink")

    def test_symlinked_parent_dir(self):
        (self.root / "real").mkdir()
        (self.root / "real" / "f.txt").write_bytes(b"f")
        os.symlink(self.root / "real", self.root / "link")
        self.refused(s.seal, ["link/f.txt"], "c", str(self.root), NOW, match="symlink")

    def test_symlink_at_seal(self):
        os.symlink(self.root / "held" / "b.csv", self.root / "held" / "l.csv")
        self.refused(s.seal, ["held/l.csv"], "c", str(self.root), NOW, match="symlink")

    def test_traversal_and_absolute(self):
        for bad in ("../x", "held/../../x", "/etc/passwd", "held//a.json", "./held/a.json", "held\\a.json", ""):
            with self.subTest(bad=bad):
                self.refused(s.seal, [bad], "c", str(self.root), NOW)

    def test_outside_root_via_manifest(self):
        files = [{**self.m["files"][0], "path": "../x"}]
        self.refused(self.v, reseal(self.m, files=files))

    def test_seal_missing_and_directory(self):
        self.refused(s.seal, ["held/nope"], "c", str(self.root), NOW)
        self.refused(s.seal, ["held"], "c", str(self.root), NOW)

    def test_duplicate_paths(self):
        self.refused(s.seal, ["held/a.json", "held/a.json"], "c", str(self.root), NOW, match="duplicate")
        files = [self.m["files"][0], self.m["files"][0]]
        self.refused(self.v, reseal(self.m, files=files), match="duplicate")

    def test_empty_inputs(self):
        for c in ("", "   ", None, 5):
            with self.subTest(c=c):
                self.refused(s.seal, self.paths, c, str(self.root), NOW, match="custodian")
        self.refused(s.seal, [], "c", str(self.root), NOW)
        self.refused(self.v, reseal(self.m, custodian=""), match="custodian")
        self.refused(self.v, reseal(self.m, files=[]))

    def test_non_utc_time(self):
        self.refused(s.seal, self.paths, "c", str(self.root), "2026-12-01T12:00:00+02:00")
        self.refused(s.seal, self.paths, "c", str(self.root), "2026-12-01T12:00:00")
        self.refused(self.v, reseal(self.m, sealed_utc="junk"))

    def test_wrong_manifest_digest(self):
        for edit in ({"custodian": "someone-else"}, {"sealed_utc": "2026-12-02T00:00:00Z"},
                     {"files": [{**self.m["files"][0], "sha256": sha(b"evil")}, self.m["files"][1]]}):
            with self.subTest(edit=list(edit)):
                self.refused(self.v, {**self.m, **edit}, match="manifest sha256")
        self.refused(self.v, {**self.m, "manifest_sha256": "0" * 64}, match="manifest sha256")
        self.refused(self.v, {k: v for k, v in self.m.items() if k != "manifest_sha256"}, match="keys")
        self.refused(self.v, {**self.m, "extra": 1}, match="keys")
        self.refused(s.verify, [], str(self.root), match="keys")

    def test_bad_entry_fields(self):
        f0 = self.m["files"][0]
        for bad in ({"sha256": "ABC"}, {"sha256": 5}, {"size": -1}, {"size": True}, {"size": "5"}, {"kind": ""}):
            with self.subTest(bad=bad):
                self.refused(self.v, reseal(self.m, files=[{**f0, **bad}]))
        self.refused(self.v, reseal(self.m, files=[{**f0, "x": 1}]))
        self.refused(self.v, reseal(self.m, files=["a"]))

    # gate integration
    def test_gate_accepts_freeze_with_protected_inputs(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))

        def git(*a):
            return subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
        (root / "proto.md").write_bytes(b"protocol")
        git("add", "."); git("commit", "-qm", "floor")
        floor = git("rev-parse", "HEAD")
        (root / "held").mkdir()
        (root / "held" / "a.json").write_bytes(b"alpha")
        git("add", "."); git("commit", "-qm", "pin")
        pin = git("rev-parse", "HEAD")
        old = g.FLOOR_COMMIT
        g.FLOOR_COMMIT = floor
        self.addCleanup(setattr, g, "FLOOR_COMMIT", old)
        m = s.seal(["held/a.json"], "cust-1", str(root), NOW)
        pins = s.to_protected_inputs(m)
        self.assertEqual(pins, [{"path": "held/a.json", "sha256": sha(b"alpha"), "custodian": "cust-1"}])
        freeze = {"batch": "L3-C-R2", "protocol_path": "proto.md", "protocol_sha256": sha(b"protocol"),
                  "commit": pin, "tree": git("rev-parse", pin + "^{tree}"), "protected_inputs": pins,
                  "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
                  **{k: f"value-{k}" for k in PRESENCE}}
        fp, ap = root / "freeze.json", root / "adm.json"

        def run(fr):
            fp.write_text(json.dumps(fr))
            ap.write_text(json.dumps({
                "batch": "L3-C-R2", "one_use": True, "used": False,
                "valid_from_utc": "2026-12-01T00:00:00Z", "valid_until_utc": "2026-12-02T00:00:00Z",
                "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
                "owner_words": WORDS, "freeze_record_sha256": sha(fp.read_bytes())}))
            return g.check(str(fp), str(ap), NOW, str(root), hosted_cap=15, gpu_cap=10,
                           max_window_hours=48, owner_words=WORDS)
        self.assertTrue(run(freeze))
        (root / "held" / "a.json").write_bytes(b"tampered")
        with self.assertRaises(g.AdmissionRefused):
            run(freeze)

    def test_to_protected_inputs_refuses_bad_manifest(self):
        self.refused(s.to_protected_inputs, {**self.m, "custodian": "x"}, match="manifest sha256")

    # overlap
    def test_no_overlap_disjoint(self):
        (self.root / "vis").mkdir()
        (self.root / "vis" / "v.json").write_bytes(b"visible")
        vis = s.seal(["vis/v.json"], "c", str(self.root), NOW)
        self.assertTrue(s.no_overlap(vis, self.m))

    def test_overlap_by_path(self):
        self.refused(s.no_overlap, self.m, self.m, match="paths ['held/a.json'")

    def test_overlap_by_hash_under_other_path(self):
        (self.root / "vis").mkdir()
        (self.root / "vis" / "copy.json").write_bytes(b"alpha")
        vis = s.seal(["vis/copy.json"], "c", str(self.root), NOW)
        self.refused(s.no_overlap, vis, self.m, match="hashes")
        self.refused(s.no_overlap, self.m, vis, match="hashes")

    def test_overlap_same_path_different_content(self):
        other = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (other / "held").mkdir()
        (other / "held" / "a.json").write_bytes(b"different")
        vis = s.seal(["held/a.json"], "c", str(other), NOW)
        self.refused(s.no_overlap, vis, self.m, match="paths ['held/a.json']")

    def test_protected_inputs_refuses_unsafe_path_without_filesystem(self):
        files = [{**self.m["files"][0], "path": "/abs/x"}]
        self.refused(s.to_protected_inputs, reseal(self.m, files=files))

    # MAJOR 1: chunked hashing
    def test_large_file_hashed_in_chunks_equal_digest(self):
        data = bytes(range(256)) * (3 * 1024 * 4)  # 3 MiB, over the 256 KiB digest chunk
        (self.root / "held" / "big.bin").write_bytes(data)
        with mock.patch.object(g, "_read", side_effect=AssertionError("whole-file read")):
            m = s.seal(["held/big.bin"], "c", str(self.root), NOW)
            self.assertEqual(m["files"][0]["sha256"], sha(data))
            self.assertEqual(m["files"][0]["size"], len(data))
            self.assertEqual(g._input_sha(str(self.root), "held/big.bin"), sha(data))

    def test_hash_goes_through_file_digest(self):
        with mock.patch.object(hashlib, "file_digest", wraps=hashlib.file_digest) as fd:
            s.seal(self.paths, "c", str(self.root), NOW)
            self.assertEqual(fd.call_count, 2)
            g._input_sha(str(self.root), "held/a.json")
            self.assertEqual(fd.call_count, 3)

    def test_missing_file_under_symlinked_subdir_of_a_real_root_refused(self):
        (self.root / "held" / "real").mkdir()
        os.symlink(self.root / "held" / "real", self.root / "held" / "sub")
        f = {**self.m["files"][0], "path": "held/sub/gone.txt"}
        self.refused(s.verify, reseal(self.m, files=[f]), str(self.root), match="symlink")

    def test_duplicate_sealed_roots_refused(self):
        self.refused(self.v, reseal(self.m, sealed_roots=["held", "held"]), match="duplicate sealed root")

    def swap_parent_for_symlink(self):
        """The reviewer's attack: after the path checks, before the open, held/ becomes a symlink."""
        outside = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (outside / "a.json").write_bytes(b"OUTSIDE")
        real = g._open_regular

        def attack(path, root=None):
            os.rename(self.root / "held", self.root / "held_bak")
            os.symlink(outside, self.root / "held")
            return real(path, root)
        return mock.patch.object(g, "_open_regular", attack)

    def test_parent_swapped_for_symlink_refused_by_seal(self):
        with self.swap_parent_for_symlink():
            self.refused(s.seal, ["held/a.json"], "c", str(self.root), NOW)

    def test_parent_swapped_for_symlink_refused_by_verify(self):
        with self.swap_parent_for_symlink():
            self.refused(self.v)

    def test_parent_swapped_for_symlink_refused_by_gate_input_sha(self):
        with self.swap_parent_for_symlink():
            with self.assertRaises(g.AdmissionRefused):
                g._input_sha(str(self.root), "held/a.json")

    def test_open_regular_rooted_checks(self):
        root = os.path.realpath(self.root)
        with g._open_regular(f"{root}/held/a.json", root) as f:
            self.assertEqual(f.read(), b"alpha")
        for bad in (f"{root}/../x", os.path.dirname(root) + "/zzz", root):
            with self.assertRaises(g.AdmissionRefused):
                g._open_regular(bad, root)

    def test_rooted_open_refuses_without_proc(self):
        root = os.path.realpath(self.root)
        with mock.patch.object(os.path, "isdir", lambda p: False if p == "/proc/self/fd" else True):
            with self.assertRaises(g.AdmissionRefused):
                g._open_regular(f"{root}/held/a.json", root)

    def test_proc_fd_mismatch_refused(self):
        root = os.path.realpath(self.root)
        with mock.patch.object(os, "readlink", lambda p: "/somewhere/else"):
            with self.assertRaises(g.AdmissionRefused):
                g._open_regular(f"{root}/held/a.json", root)

    def test_root_with_similar_prefix_is_not_under(self):
        f = {**self.m["files"][0], "path": "held/sub2/x"}
        self.refused(s._check_shape, reseal(self.m, files=[f], sealed_roots=["held/sub"]),
                     match="not under a sealed root")
        f["path"] = "held/sub/x"
        s._check_shape(reseal(self.m, files=[f], sealed_roots=["held/sub"]))

    # MAJOR 2: load
    def test_load_roundtrip_text_and_path(self):
        txt = json.dumps(self.m)
        self.assertEqual(s.load(txt), self.m)
        pth = self.root / "m.json"
        pth.write_text(txt)
        self.assertEqual(s.load(str(pth)), self.m)
        self.assertEqual(s.load(pth), self.m)
        self.refused(s.load, str(self.root / "nope.json"))
        self.refused(s.load, "{not json")
        self.refused(s.load, "[1]")

    def test_load_duplicate_zeroed_sha_key(self):
        txt = json.dumps(self.m)
        real = self.m["files"][0]["sha256"]
        dup = txt.replace(f'"sha256": "{real}"', f'"sha256": "{real}", "sha256": "{"0" * 64}"', 1)
        self.assertNotEqual(dup, txt)
        self.refused(s.load, dup, match="duplicate key")
        top = txt[:-1] + ', "custodian": "x"}'
        self.refused(s.load, top, match="duplicate key")

    def test_load_nan_and_infinity(self):
        for c in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(c=c):
                txt = json.dumps(self.m).replace('"size": 5', f'"size": {c}', 1)
                self.refused(s.load, txt, match="non-finite")

    def test_load_checks_self_digest(self):
        self.refused(s.load, json.dumps({**self.m, "custodian": "x"}), match="manifest sha256")

    # MAJOR 3: docstrings state the limits
    def test_docstrings_state_contract_and_limits(self):
        for phrase in ("RUNNER CONTRACT", "ONLY the manifest's listed paths", "self-consistency",
                       "authenticates the custodian", "stale", "trivially edited copy", "hiding"):
            self.assertIn(phrase, s.__doc__)
        self.assertIn("not disks", s.no_overlap.__doc__)

    # MAJOR 4: descriptor identity and O_NOFOLLOW
    def test_inode_mismatch_after_open_refused(self):
        real = os.lstat

        def fake(path, *a, **k):
            r = real(path, *a, **k)
            return os.stat_result((r.st_mode, r.st_ino + 1, r.st_dev, r.st_nlink, r.st_uid, r.st_gid,
                                   r.st_size, 0, 0, 0))
        with mock.patch.object(os, "lstat", fake):
            self.refused(s.verify, self.m, str(self.root), match="changed between check and open")
            with self.assertRaises(g.AdmissionRefused):
                g._input_sha(str(self.root), "held/a.json")

    def test_o_nofollow_on_last_component_when_lstat_is_fooled(self):
        os.symlink(self.root / "held" / "b.csv", self.root / "held" / "l.csv")
        real = os.lstat
        with mock.patch.object(os, "lstat", lambda p, *a, **k: os.stat(p)):
            with self.assertRaises(g.AdmissionRefused):
                g._open_regular(str(self.root / "held" / "l.csv"))
        self.assertTrue(real)

    def test_hardcoded_manifest_digest(self):
        body = {"custodian": "c1", "sealed_utc": "2026-12-01T12:00:00Z", "sealed_roots": ["d"],
                "files": [{"path": "d/a.txt", "sha256": "a" * 64, "size": 3, "kind": "txt"}]}
        want = "73a03a4e506fe9421abe250b0295fe1a2467bdeec7723e83cbae5293d18ccaca"
        self.assertEqual(s._digest(body), want)
        s._check_shape({**body, "manifest_sha256": want})

    # MINOR
    def test_nfc_casefold_collisions(self):
        (self.root / "held" / "\u00e9.txt").write_bytes(b"1")
        (self.root / "held" / "e\u0301.txt").write_bytes(b"2")
        (self.root / "held" / "Q.txt").write_bytes(b"3")
        (self.root / "held" / "q.txt").write_bytes(b"4")
        self.refused(s.seal, ["held/\u00e9.txt", "held/e\u0301.txt"], "c", str(self.root), NOW, match="collide")
        self.refused(s.seal, ["held/Q.txt", "held/q.txt"], "c", str(self.root), NOW, match="collide")
        f0 = self.m["files"][0]
        files = [f0, {**f0, "path": "held/A.JSON"}]
        self.refused(self.v, reseal(self.m, files=files), match="collide")

    def test_overlap_by_path_after_nfc_casefold(self):
        other = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (other / "held").mkdir()
        (other / "held" / "A.JSON").write_bytes(b"different")
        vis = s.seal(["held/A.JSON"], "c", str(other), NOW)
        self.refused(s.no_overlap, vis, self.m, match="paths")

    def test_missing_file_under_symlinked_parent_refused(self):
        (self.root / "real").mkdir()
        os.symlink(self.root / "real", self.root / "link")
        f = {**self.m["files"][0], "path": "link/gone.txt"}
        self.refused(s.verify, reseal(self.m, files=[f], sealed_roots=["link"]), str(self.root),
                     match="symlink")

    def test_dangling_symlink_listed_refused_not_missing(self):
        os.unlink(self.root / "held" / "a.json")
        os.symlink(self.root / "nowhere", self.root / "held" / "a.json")
        self.refused(self.v, match="symlink")

    def test_hard_link_refused(self):
        os.link(self.root / "held" / "a.json", self.root / "held" / "hl.json")
        self.refused(s.seal, ["held/a.json"], "c", str(self.root), NOW, match="hard link")
        self.refused(self.v, match="hard link")

    def test_datetime_inside_manifest_raises_seal_error(self):
        from datetime import datetime, timezone
        self.refused(self.v, {**self.m, "sealed_utc": datetime(2026, 12, 1, 12, tzinfo=timezone.utc)})
        self.refused(self.v, {**self.m, "extra": datetime(2026, 12, 1)}, match="keys")
        self.refused(s._digest, {"t": datetime(2026, 12, 1)})

    def test_bare_string_paths_refused(self):
        self.refused(s.seal, "held/a.json", "c", str(self.root), NOW, match="not a string")

    def test_overlap_refuses_tampered_manifest(self):
        self.refused(s.no_overlap, {**self.m, "custodian": "x"}, self.m, match="manifest sha256")
        self.refused(s.no_overlap, self.m, {**self.m, "custodian": "x"}, match="manifest sha256")


if __name__ == "__main__":
    unittest.main()
