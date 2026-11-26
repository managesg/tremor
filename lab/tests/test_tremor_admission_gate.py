import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab import tremor_admission_gate as g

NOW = "2026-12-01T12:00:00Z"
WORDS = "I admit batch L3-C-R2 once"
CAPS = dict(hosted_cap=15, gpu_cap=10, max_window_hours=48, owner_words=WORDS)
PRESENCE = ["config_hash", "model_snapshot", "task_family_revision", "scorer_ids", "contrasts",
            "stopping_rules", "expected_and_max_resources", "approval_review_evidence",
            "d1_basis", "inherited_pins"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


class GateTests(unittest.TestCase):
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
        self.pin = self.git("rev-parse", "HEAD")
        old = g.FLOOR_COMMIT
        g.FLOOR_COMMIT = self.floor
        self.addCleanup(setattr, g, "FLOOR_COMMIT", old)
        self.freeze = {
            "batch": "L3-C-R2", "protocol_path": "proto.md", "protocol_sha256": sha(b"protocol"),
            "commit": self.pin, "tree": self.git("rev-parse", self.pin + "^{tree}"),
            "protected_inputs": [{"path": "input.txt", "sha256": sha(b"input"), "custodian": "alice"}],
            "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
            **{k: f"value-{k}" for k in PRESENCE},
        }
        self.adm = {
            "batch": "L3-C-R2", "one_use": True, "used": False,
            "valid_from_utc": "2026-12-01T00:00:00Z", "valid_until_utc": "2026-12-02T00:00:00Z",
            "reserved_gpu_hours": 10, "hosted_usd_plan": 9, "hosted_usd_stop": 15,
            "owner_words": WORDS, "freeze_record_sha256": "",
        }
        self.fp = str(self.root / "freeze.json")
        self.ap = str(self.root / "adm.json")

    def write(self, freeze=None, adm=None, raw_freeze=None):
        Path(self.fp).write_text(raw_freeze if raw_freeze is not None else json.dumps(freeze or self.freeze))
        a = dict(adm or self.adm)
        if "freeze_record_sha256" in a and a["freeze_record_sha256"] == "":
            a["freeze_record_sha256"] = sha(Path(self.fp).read_bytes())
        Path(self.ap).write_text(json.dumps(a))

    def run_check(self, freeze=None, adm=None, now=NOW, fn=None, raw_freeze=None, **caps):
        self.write(freeze, adm, raw_freeze)
        return (fn or g.check)(self.fp, self.ap, now, str(self.root), **{**CAPS, **caps})

    def refused(self, match=None, **kw):
        with self.assertRaises(g.AdmissionRefused) as cm:
            self.run_check(**kw)
        if match:
            self.assertIn(match, str(cm.exception))

    def fz(self, **kv):
        return {**self.freeze, **kv}

    def ad(self, **kv):
        return {**self.adm, **kv}

    def commit_info(self, rev):
        return dict(commit=self.git("rev-parse", rev), tree=self.git("rev-parse", rev + "^{tree}"))

    # accepted
    def test_accepted(self):
        self.assertTrue(self.run_check())

    def test_accepted_at_window_start_below_limits(self):
        self.assertTrue(self.run_check(adm=self.ad(reserved_gpu_hours=0, hosted_usd_plan=1.5),
                                       now="2026-12-01T00:00:00Z"))

    def test_datetime_now_utc_accepted(self):
        from datetime import datetime, timezone
        self.assertTrue(self.run_check(now=datetime(2026, 12, 1, 12, tzinfo=timezone.utc)))

    # protocol at pinned commit
    def test_protocol_sha_mismatch(self):
        self.refused("protocol sha256", freeze=self.fz(protocol_sha256=sha(b"x")))

    def test_protocol_working_tree_edit_is_ignored_commit_content_is_hashed(self):
        (self.root / "proto.md").write_bytes(b"edited")
        self.assertTrue(self.run_check())
        self.refused("protocol sha256", freeze=self.fz(protocol_sha256=sha(b"edited")))

    def test_protocol_not_in_commit(self):
        (self.root / "new.md").write_bytes(b"n")
        self.refused("not in pinned commit", freeze=self.fz(protocol_path="new.md", protocol_sha256=sha(b"n")))

    def test_protocol_path_absolute_or_dotdot(self):
        for p in ("/etc/passwd", "../x", "a/../proto.md", ""):
            self.refused("relative", freeze=self.fz(protocol_path=p))

    # commit
    def test_commit_before_floor(self):
        g.FLOOR_COMMIT = self.pin
        self.refused("before", freeze=self.fz(**self.commit_info(self.floor)))

    def test_commit_equal_floor_ok(self):
        self.assertTrue(self.run_check(freeze=self.fz(**self.commit_info(self.floor))))

    def test_commit_not_ancestor_of_head(self):
        self.git("checkout", "-q", "-b", "side", self.floor)
        (self.root / "side.txt").write_text("s")
        self.git("add", "."); self.git("commit", "-qm", "side")
        info = self.commit_info("HEAD")
        self.git("checkout", "-q", self.pin)
        self.refused("ancestor", freeze=self.fz(**info))

    def test_commit_must_be_full_hex_not_ref_or_abbrev(self):
        for c in ("HEAD", "side", self.pin[:12], self.pin.upper(), "deadbeef" * 5, "", None, 5):
            self.refused("commit", freeze=self.fz(commit=c))

    def test_unknown_floor(self):
        g.FLOOR_COMMIT = "deadbeef" * 5
        self.refused("floor")

    def test_wrong_tree(self):
        self.refused("tree", freeze=self.fz(tree=self.git("rev-parse", self.floor + "^{tree}")))

    # protected inputs
    def test_protected_input_changed(self):
        (self.root / "input.txt").write_bytes(b"changed")
        self.refused("protected input changed")

    def test_protected_input_missing_empty_malformed(self):
        pin = lambda **kv: [{"path": "input.txt", "sha256": sha(b"input"), "custodian": "a", **kv}]
        self.refused("cannot read", freeze=self.fz(protected_inputs=pin(path="nope")))
        self.refused("protected_inputs", freeze=self.fz(protected_inputs=[]))
        self.refused("malformed", freeze=self.fz(protected_inputs=["input.txt"]))
        self.refused("malformed", freeze=self.fz(protected_inputs=pin(extra=1)))
        self.refused("custodian", freeze=self.fz(protected_inputs=pin(custodian="")))

    def test_protected_input_absolute_and_dotdot(self):
        for p in (str(self.root / "input.txt"), "../input.txt", "sub/../input.txt"):
            self.refused("relative", freeze=self.fz(protected_inputs=[
                {"path": p, "sha256": sha(b"input"), "custodian": "a"}]))

    def test_protected_input_symlink_file_refused(self):
        os.symlink(self.root / "input.txt", self.root / "link.txt")
        self.refused("symlink", freeze=self.fz(protected_inputs=[
            {"path": "link.txt", "sha256": sha(b"input"), "custodian": "a"}]))

    def test_protected_input_symlinked_dir_and_escape_refused(self):
        with tempfile.TemporaryDirectory() as out:
            Path(out, "secret").write_bytes(b"input")
            os.symlink(out, self.root / "dirlink")
            self.refused("escapes", freeze=self.fz(protected_inputs=[
                {"path": "dirlink/secret", "sha256": sha(b"input"), "custodian": "a"}]))
        (self.root / "real").mkdir()
        (self.root / "real" / "f").write_bytes(b"input")
        os.symlink(self.root / "real", self.root / "inroot")
        self.refused("symlink", freeze=self.fz(protected_inputs=[
            {"path": "inroot/f", "sha256": sha(b"input"), "custodian": "a"}]))

    # schema
    def test_unknown_keys_refused(self):
        self.refused("keys", freeze=self.fz(extra=1))
        self.refused("keys", adm=self.ad(extra=1))

    def test_missing_keys_refused(self):
        self.refused("keys", freeze={k: v for k, v in self.freeze.items() if k != "batch"})
        self.refused("keys", adm={k: v for k, v in self.adm.items() if k != "used"})

    def test_adm47_fields_required_nonempty(self):
        for k in PRESENCE:
            for bad in ("", "  ", None, [], {}, 0, False, True):
                self.refused(k, freeze=self.fz(**{k: bad}))

    def test_duplicate_key_refused(self):
        raw = json.dumps(self.freeze)[:-1] + ', "batch": "other"}'
        self.refused("duplicate", raw_freeze=raw)
        Path(self.fp).write_text(json.dumps(self.freeze))
        Path(self.ap).write_text('{"used": true, "used": false}')
        with self.assertRaises(g.AdmissionRefused) as cm:
            g.check(self.fp, self.ap, NOW, str(self.root), **CAPS)
        self.assertIn("duplicate", str(cm.exception))

    def test_nan_constant_refused(self):
        self.refused("non-finite", raw_freeze=json.dumps(self.freeze).replace('"reserved_gpu_hours": 10', '"reserved_gpu_hours": NaN'))

    def test_unreadable_records(self):
        with self.assertRaises(g.AdmissionRefused):
            g.check(str(self.root / "none.json"), self.ap, NOW, str(self.root), **CAPS)
        Path(self.fp).write_text("[]"); Path(self.ap).write_text("{")
        with self.assertRaises(g.AdmissionRefused):
            g.check(self.fp, self.ap, NOW, str(self.root), **CAPS)

    # admission binding
    def test_wrong_batch(self):
        self.refused("batch", adm=self.ad(batch="L2-C-R2"))
        self.refused("batch", freeze=self.fz(batch=""), adm=self.ad(batch=""))

    def test_freeze_record_sha_binding(self):
        self.refused("freeze_record_sha256", adm=self.ad(freeze_record_sha256="0" * 64))

    def test_freeze_file_changed_after_admission(self):
        self.write()
        Path(self.fp).write_text(json.dumps(self.fz(config_hash="other")))
        with self.assertRaises(g.AdmissionRefused):
            g.check(self.fp, self.ap, NOW, str(self.root), **CAPS)

    def test_one_use_not_true(self):
        for v in (False, "true", 1):
            self.refused("one_use", adm=self.ad(one_use=v))

    def test_used_already(self):
        for v in (True, "false", None, 0):
            self.refused("used", adm=self.ad(used=v))

    # window
    def test_window(self):
        self.refused("window", now="2026-11-30T23:59:59Z")
        self.refused("window", now="2026-12-02T00:00:00Z")
        self.refused("window", now="2026-12-03T00:00:00Z")

    def test_timestamps_must_be_utc(self):
        from datetime import datetime, timezone, timedelta
        self.refused("UTC", adm=self.ad(valid_from_utc="2026-12-01T00:00:00"))
        self.refused("UTC", adm=self.ad(valid_until_utc="2026-12-02T01:00:00+01:00"))
        self.refused("UTC", now="not a time")
        self.refused("UTC", now=datetime(2026, 12, 1, 12))
        self.refused("UTC", now=datetime(2026, 12, 1, 13, tzinfo=timezone(timedelta(hours=1))))
        self.refused("UTC", now=None)

    def test_window_too_long(self):
        self.refused("max_window_hours", max_window_hours=23.9)
        self.assertTrue(self.run_check(max_window_hours=24))

    def test_max_window_hours_invalid(self):
        for v in (0, -1, True, float("nan"), None, "24", float("inf"), 10 ** 400):
            self.refused("max_window_hours", max_window_hours=v)

    # numbers and caps
    def test_limit_above_freeze(self):
        for k, v in (("reserved_gpu_hours", 10.5), ("hosted_usd_plan", 9.01), ("hosted_usd_stop", 15.01)):
            self.refused(k, adm=self.ad(**{k: v}), hosted_cap=100, gpu_cap=100)

    def test_hosted_plan_and_stop_each_checked_against_cap(self):
        self.refused("hosted_usd_stop", hosted_cap=14)
        self.refused("hosted_usd_plan", hosted_cap=8, adm=self.ad(hosted_usd_stop=0))

    def test_gpu_above_gpu_cap(self):
        self.refused("gpu_cap", gpu_cap=9)

    def test_caps_required_no_default(self):
        self.write()
        for drop in ("hosted_cap", "gpu_cap", "max_window_hours", "owner_words"):
            with self.assertRaises(TypeError):
                g.check(self.fp, self.ap, NOW, str(self.root), **{k: v for k, v in CAPS.items() if k != drop})

    def test_cap_invalid(self):
        for name in ("hosted_cap", "gpu_cap"):
            for cap in (True, float("nan"), -1, "5", None, float("inf"), 10 ** 400):
                self.refused(name.replace("_cap", ""), **{name: cap})

    def test_bad_numbers_in_records(self):
        for bad in (True, False, float("nan"), -1, "5", None, float("inf"), 10 ** 400):
            for k in ("reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop"):
                try:
                    self.run_check(freeze=self.fz(**{k: bad}))
                    self.fail(f"accepted freeze {k}={bad!r}")
                except g.AdmissionRefused:
                    pass
                try:
                    self.run_check(adm=self.ad(**{k: bad}))
                    self.fail(f"accepted admission {k}={bad!r}")
                except g.AdmissionRefused:
                    pass

    # owner words exact
    def test_owner_words_exact_equality(self):
        self.refused("owner words", adm=self.ad(owner_words="Owner: " + WORDS + "."))  # superset
        self.refused("owner words", adm=self.ad(owner_words=WORDS + " "))
        self.refused("owner words", adm=self.ad(owner_words=" " + WORDS))
        self.refused("owner words", adm=self.ad(owner_words=WORDS[:-1] + "x"))
        self.refused("owner words", owner_words=WORDS + " ")
        self.refused("owner words", adm=self.ad(owner_words=""), owner_words="")
        self.refused("owner words", adm=self.ad(owner_words="  "), owner_words="  ")
        self.refused("owner words", owner_words=None)

    # admit
    def test_admit_claims_once(self):
        self.assertTrue(self.run_check(fn=g.admit))
        self.assertIs(json.loads(Path(self.ap).read_text())["used"], True)
        self.assertEqual(len(self.claims()), 1)
        self.assertEqual(self.claims(), ["L3-C-R2"])
        info = json.loads((self.cdir() / "L3-C-R2").read_text())
        self.assertEqual(info["admission_record"], os.path.abspath(self.ap))
        self.assertEqual(info["freeze_record_sha256"], sha(Path(self.fp).read_bytes()))
        self.assertFalse((self.root / ".admission-claims").exists())
        self.assertTrue(__import__("datetime").datetime.fromisoformat(info["claimed_utc"]).utcoffset() is not None)
        self.assertEqual(oct(os.stat(self.cdir()).st_mode & 0o777), "0o700")
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if p.name.startswith(".admit-")), [])
        with self.assertRaises(g.AdmissionRefused):
            g.admit(self.fp, self.ap, NOW, str(self.root), **CAPS)

    def claims(self):
        d = self.cdir()
        return sorted(os.listdir(d)) if d.exists() else []

    def cdir(self):
        return self.root / ".git" / "tremor-admission-claims"

    def test_copied_admission_cannot_admit_twice(self):
        self.run_check(fn=g.admit)
        copy = str(self.root / "adm_copy.json")
        Path(copy).write_text(json.dumps(self.ad(freeze_record_sha256=sha(Path(self.fp).read_bytes()))))
        with self.assertRaises(g.AdmissionRefused) as cm:
            g.admit(self.fp, copy, NOW, str(self.root), **CAPS)
        self.assertIn("claimed", str(cm.exception))
        self.assertIs(json.loads(Path(copy).read_text())["used"], False)

    def test_precreated_claim_refuses(self):
        self.write()
        d = self.cdir()
        d.mkdir(mode=0o700)
        (d / "L3-C-R2").write_text("x")
        with self.assertRaises(g.AdmissionRefused):
            g.admit(self.fp, self.ap, NOW, str(self.root), **CAPS)
        self.assertIs(json.loads(Path(self.ap).read_text())["used"], False)

    def test_resaved_freeze_does_not_reopen_batch(self):
        self.run_check(fn=g.admit)
        with self.assertRaises(g.AdmissionRefused) as cm:
            self.run_check(fn=g.admit, freeze=self.fz(config_hash="different"))
        self.assertIn("claimed", str(cm.exception))
        self.assertEqual(self.claims(), ["L3-C-R2"])

    def test_other_worktree_shares_claims(self):
        wt_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        wt = wt_dir / "wt"
        self.git("worktree", "add", "-q", "--detach", str(wt), self.pin)
        self.run_check(fn=g.admit)
        Path(self.ap + ".wt").write_text(json.dumps(self.ad(freeze_record_sha256=sha(Path(self.fp).read_bytes()))))
        with self.assertRaises(g.AdmissionRefused) as cm:
            g.admit(self.fp, self.ap + ".wt", NOW, str(wt), **CAPS)
        self.assertIn("claimed", str(cm.exception))
        self.assertEqual(self.claims(), ["L3-C-R2"])
        self.assertFalse((wt / ".admission-claims").exists())

    def test_first_admit_in_second_worktree_then_main_refused(self):
        wt_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        wt = wt_dir / "wt"
        self.git("worktree", "add", "-q", "--detach", str(wt), self.pin)
        self.write()
        self.assertTrue(g.admit(self.fp, self.ap, NOW, str(wt), **CAPS))
        Path(self.ap + ".c").write_text(json.dumps(self.ad(freeze_record_sha256=sha(Path(self.fp).read_bytes()))))
        with self.assertRaises(g.AdmissionRefused):
            g.admit(self.fp, self.ap + ".c", NOW, str(self.root), **CAPS)

    def test_claim_dir_symlink_refused(self):
        self.write()
        with tempfile.TemporaryDirectory() as out:
            os.symlink(out, self.cdir())
            with self.assertRaises(g.AdmissionRefused) as cm:
                g.admit(self.fp, self.ap, NOW, str(self.root), **CAPS)
            self.assertIn("symlink", str(cm.exception))
            self.assertEqual(os.listdir(out), [])
        self.assertIs(json.loads(Path(self.ap).read_text())["used"], False)

    def test_claim_dir_not_owner_only_refused(self):
        self.write()
        self.cdir().mkdir()
        os.chmod(self.cdir(), 0o750)
        with self.assertRaises(g.AdmissionRefused) as cm:
            g.admit(self.fp, self.ap, NOW, str(self.root), **CAPS)
        self.assertIn("owner-only", str(cm.exception))
        self.assertEqual(self.claims(), [])

    def test_claim_uses_batch_validated_by_check_not_a_reread(self):
        real = g._check
        def tamper(*a, **k):
            r = real(*a, **k)
            Path(self.ap).write_text(Path(self.ap).read_text().replace("L3-C-R2", "EVIL"))
            return r
        g._check = tamper
        try:
            with self.assertRaises(g.AdmissionRefused):
                self.run_check(fn=g.admit)
        finally:
            g._check = real
        self.assertEqual(self.claims(), ["L3-C-R2"])

    def test_batch_must_be_filename_safe(self):
        for b in ("../x", "a/b", ".hidden", "", "a b"):
            self.refused("batch", freeze=self.fz(batch=b), adm=self.ad(batch=b))

    def test_admission_changed_during_claim(self):
        real = os.open
        def tamper(path, flags, *a, **k):
            fd = real(path, flags, *a, **k)
            if "tremor-admission-claims" in str(path):
                Path(self.ap).write_text(Path(self.ap).read_text() + " ")
            return fd
        os.open = tamper
        try:
            with self.assertRaises(g.AdmissionRefused) as cm:
                self.run_check(fn=g.admit)
        finally:
            os.open = real
        self.assertIn("changed", str(cm.exception))
        self.assertIs(json.loads(Path(self.ap).read_text())["used"], False)

    def test_symlinked_record_files_refused(self):
        self.write()
        os.rename(self.ap, self.ap + ".real")
        os.symlink(self.ap + ".real", self.ap)
        with self.assertRaises(g.AdmissionRefused):
            g.check(self.fp, self.ap, NOW, str(self.root), **CAPS)

    def test_fifo_input_refused(self):
        os.mkfifo(self.root / "fifo")
        with self.assertRaises(g.AdmissionRefused):
            g._read(str(self.root / "fifo"))

    def decoy(self):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        return d

    def with_env(self, **env):
        saved = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        def restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return restore

    def test_git_env_cannot_redirect_check(self):
        d = self.decoy()
        for var, val in (("GIT_DIR", str(d / ".git")), ("GIT_WORK_TREE", str(d)),
                         ("GIT_COMMON_DIR", str(d / ".git")), ("GIT_CEILING_DIRECTORIES", str(self.root.parent)),
                         ("GIT_NAMESPACE", "x"), ("GIT_OBJECT_DIRECTORY", str(d / ".git" / "objects"))):
            restore = self.with_env(**{var: val})
            try:
                self.assertTrue(self.run_check(), var)
            finally:
                restore()

    def test_git_dir_cannot_redirect_admit_or_claim_location(self):
        d = self.decoy()
        restore = self.with_env(GIT_DIR=str(d / ".git"), GIT_COMMON_DIR=str(d / ".git"))
        try:
            self.assertTrue(self.run_check(fn=g.admit))
        finally:
            restore()
        self.assertEqual(self.claims(), ["L3-C-R2"])
        self.assertFalse((d / ".git" / "tremor-admission-claims").exists())

    def test_git_config_env_scrubbed(self):
        d = self.decoy()
        restore = self.with_env(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.worktree", GIT_CONFIG_VALUE_0=str(d))
        try:
            self.assertTrue(self.run_check(fn=g.admit))
        finally:
            restore()
        self.assertEqual(self.claims(), ["L3-C-R2"])

    def test_second_admit_refused_even_if_used_flag_reset(self):
        g.FLOOR_COMMIT = self.floor
        self.run_check(fn=g.admit)
        Path(self.ap).write_text(json.dumps(self.ad(freeze_record_sha256=sha(Path(self.fp).read_bytes()))))
        with self.assertRaises(g.AdmissionRefused) as cm:
            g.admit(self.fp, self.ap, NOW, str(self.root), **CAPS)
        self.assertIn("claimed", str(cm.exception))

    def test_check_never_claims_or_mutates(self):
        self.run_check()
        self.run_check()
        self.assertEqual(self.claims(), [])
        self.assertIs(json.loads(Path(self.ap).read_text())["used"], False)

    def test_failed_check_does_not_claim(self):
        self.refused(adm=self.ad(used=True), fn=g.admit)
        self.assertEqual(self.claims(), [])

    def test_admit_uses_replace_with_mkstemp_in_same_dir(self):
        calls = []
        real = os.replace
        os.replace = lambda a, b: (calls.append((a, b)), real(a, b))[1]
        try:
            self.run_check(fn=g.admit)
        finally:
            os.replace = real
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], self.ap)
        self.assertEqual(os.path.dirname(calls[0][0]), os.path.dirname(self.ap))
        self.assertNotEqual(calls[0][0], self.ap + ".tmp")

    def test_plan_starts_nothing(self):
        self.write()
        self.assertIn("launches nothing", g.plan(self.fp, self.ap))
        self.assertIs(json.loads(Path(self.ap).read_text())["used"], False)

    def test_cli(self):
        self.write()
        base = [self.fp, self.ap, "--now", NOW, "--hosted-cap", "15", "--gpu-cap", "10",
                "--max-window-hours", "48", "--owner-words", WORDS, "--repo-root", str(self.root)]
        self.assertEqual(g.main(["check", *base]), 0)
        base[base.index("15")] = "4"
        self.assertEqual(g.main(["check", *base]), 2)
        self.assertEqual(self.claims(), [])
        base[base.index("4")] = "15"
        self.assertEqual(g.main(["admit", *base]), 0)
        self.assertEqual(g.main(["admit", *base]), 2)
        self.assertEqual(len(self.claims()), 1)

    # chunked input hash and descriptor identity
    def test_input_sha_large_file_chunked_equal_digest(self):
        data = bytes(range(256)) * (3 * 1024 * 4)  # 3 MiB, over the digest chunk
        (self.root / "big.bin").write_bytes(data)
        with mock.patch.object(g, "_read", side_effect=AssertionError("whole-file read")):
            self.assertEqual(g._input_sha(str(self.root), "big.bin"), sha(data))

    def test_input_sha_refuses_inode_swap_between_lstat_and_open(self):
        real = os.lstat

        def fake(path, *a, **k):
            r = real(path, *a, **k)
            return os.stat_result((r.st_mode, r.st_ino + 1, r.st_dev, r.st_nlink, r.st_uid, r.st_gid,
                                   r.st_size, 0, 0, 0))
        with mock.patch.object(os, "lstat", fake):
            with self.assertRaises(g.AdmissionRefused):
                g._input_sha(str(self.root), "input.txt")

    def test_open_regular_nofollow_last_component_when_lstat_is_fooled(self):
        os.symlink(self.root / "input.txt", self.root / "ln.txt")
        with mock.patch.object(os, "lstat", lambda p, *a, **k: os.stat(p)):
            with self.assertRaises(g.AdmissionRefused):
                g._open_regular(str(self.root / "ln.txt"))

    def test_open_regular_refuses_directory_and_symlink(self):
        with self.assertRaises(g.AdmissionRefused):
            g._open_regular(str(self.root))
        os.symlink(self.root / "input.txt", self.root / "ln2.txt")
        with self.assertRaises(g.AdmissionRefused):
            g._open_regular(str(self.root / "ln2.txt"))


if __name__ == "__main__":
    unittest.main()
