"""End-to-end rehearsal of lab/tremor_admission_gate.py on a throwaway git repo (synthetic records only).

No network, no secrets, no model call, no real run. The repo lives in a mkdtemp directory under
the scratch base; cleanup removes only that directory after an ownership check.
"""
import contextlib
import io
import json
import os
import shutil
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab import tremor_admission_gate as g
from lab.tests import test_tremor_admission_gate as base

# Scratch base: TREMOR_TEST_SCRATCH if set, else the platform temp dir (never a hardcoded path).
SCRATCH = os.path.realpath(os.environ.get("TREMOR_TEST_SCRATCH") or tempfile.gettempdir())
PREFIX = "gate-rehearsal-"
# WORDS, PRESENCE and sha come from test_tremor_admission_gate (shared fixtures, not redefined here).
WORDS, PRESENCE, sha = base.WORDS, base.PRESENCE, base.sha
NOW = "2026-12-01T06:00:00Z"
CORE = ["batch", "protocol_path", "protocol_sha256", "commit", "tree", "protected_inputs",
        "reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop"]
ADM_KEYS = sorted(g._ADMISSION_KEYS)
LIMITS = ("reserved_gpu_hours", "hosted_usd_plan", "hosted_usd_stop")
EMPTY = ("", "   ", None, [], {}, 0, False)


def _rmtree_owned(path):
    real = os.path.realpath(path)
    if not os.path.lexists(real):
        return
    st = os.lstat(real)
    if real.startswith(SCRATCH + "/" + PREFIX) and st.st_uid == os.getuid() and not os.path.islink(path):
        shutil.rmtree(real)


class Rehearsal(unittest.TestCase):
    def git(self, *a):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        return subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True,
                              text=True, env=env).stdout.strip()

    def setUp(self):
        os.makedirs(SCRATCH, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix=PREFIX, dir=SCRATCH))
        self.addCleanup(_rmtree_owned, str(self.root))
        self.git("init", "-q")
        for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
            self.git("config", k, v)
        (self.root / "proto.md").write_bytes(b"protocol")
        self.git("add", "."); self.git("commit", "-qm", "floor")
        self.floor = self.git("rev-parse", "HEAD")
        (self.root / "in1.txt").write_bytes(b"one")
        (self.root / "in2.txt").write_bytes(b"two")
        self.git("add", "."); self.git("commit", "-qm", "pin")
        self.pin = self.git("rev-parse", "HEAD")
        self.addCleanup(setattr, g, "FLOOR_COMMIT", g.FLOOR_COMMIT)
        g.FLOOR_COMMIT = self.floor
        self.freeze = {
            "batch": "L2-R2-REH", "protocol_path": "proto.md", "protocol_sha256": sha(b"protocol"),
            "commit": self.pin, "tree": self.git("rev-parse", self.pin + "^{tree}"),
            "protected_inputs": [{"path": "in1.txt", "sha256": sha(b"one"), "custodian": "synthetic-a"},
                                 {"path": "in2.txt", "sha256": sha(b"two"), "custodian": "synthetic-b"}],
            "reserved_gpu_hours": 4, "hosted_usd_plan": 2.5, "hosted_usd_stop": 5,
            **{k: f"synthetic-{k}" for k in PRESENCE},
        }
        self.adm = {
            "batch": "L2-R2-REH", "one_use": True, "used": False,
            "valid_from_utc": "2026-12-01T00:00:00Z", "valid_until_utc": "2026-12-01T12:00:00Z",
            "reserved_gpu_hours": 4, "hosted_usd_plan": 2.5, "hosted_usd_stop": 5,
            "owner_words": WORDS, "freeze_record_sha256": "",
        }
        self.fp, self.ap = str(self.root / "freeze.json"), str(self.root / "adm.json")

    def fz(self, **kv):
        return {**self.freeze, **kv}

    def ad(self, **kv):
        return {**self.adm, **kv}

    def write(self, freeze=None, adm=None, ap=None):
        Path(self.fp).write_text(json.dumps(self.freeze if freeze is None else freeze))
        a = dict(self.adm if adm is None else adm)
        if a.get("freeze_record_sha256") == "":
            a["freeze_record_sha256"] = sha(Path(self.fp).read_bytes())
        Path(ap or self.ap).write_text(json.dumps(a))

    def cli(self, cmd="check", ap=None, now=NOW, words=WORDS, hosted=15, gpu=10, hours=48):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = g.main([cmd, self.fp, ap or self.ap, "--now", now, "--hosted-cap", str(hosted),
                         "--gpu-cap", str(gpu), "--max-window-hours", str(hours),
                         "--owner-words", words, "--repo-root", str(self.root)])
        return rc, out.getvalue().strip()

    def refused(self, why, **kw):
        self.write(kw.pop("freeze", None), kw.pop("adm", None))
        rc, out = self.cli(**kw)
        self.assertEqual(rc, 2, out)
        self.assertTrue(out.startswith("REFUSED:"), out)
        self.assertIn(why, out)

    def claims(self):
        d = self.root / ".git" / "tremor-admission-claims"
        return sorted(os.listdir(d)) if d.exists() else []

    def used(self, ap=None):
        return json.loads(Path(ap or self.ap).read_text())["used"]

    # valid pair, admitted once
    def test_valid_pair_admitted_once_then_second_claim_refused(self):
        self.write()
        self.assertEqual(self.cli("admit"), (0, "OK"))
        self.assertIs(self.used(), True)
        self.assertEqual(self.claims(), ["L2-R2-REH"])
        claim = json.loads((self.root / ".git/tremor-admission-claims/L2-R2-REH").read_text())
        self.assertEqual(claim["freeze_record_sha256"], sha(Path(self.fp).read_bytes()))
        self.assertEqual(set(json.loads(Path(self.ap).read_text())), g._ADMISSION_KEYS)
        # a fresh, unused-looking admission for the same batch and freeze
        copy = str(self.root / "adm2.json")
        self.write(ap=copy)
        rc, out = self.cli("admit", ap=copy)
        self.assertEqual(rc, 2)
        self.assertIn("batch already claimed", out)
        self.assertIs(self.used(copy), False)
        self.assertEqual(self.claims(), ["L2-R2-REH"])

    def test_claim_is_per_batch_not_global_and_not_per_freeze(self):
        self.write()
        self.assertEqual(self.cli("admit")[0], 0)
        other = self.fz(batch="L2-R2-OTHER")
        self.write(freeze=other, adm=self.ad(batch="L2-R2-OTHER"))
        self.assertEqual(self.cli("admit")[0], 0)
        self.assertEqual(self.claims(), ["L2-R2-OTHER", "L2-R2-REH"])
        # the first batch with a re-saved (different) freeze is still spent
        self.write(freeze=self.fz(config_hash="resaved"))
        rc, out = self.cli("admit")
        self.assertEqual(rc, 2)
        self.assertIn("batch already claimed", out)
        self.assertEqual(len(self.claims()), 2)

    def test_check_is_dry_and_refusal_claims_nothing(self):
        self.write()
        before = Path(self.ap).read_bytes()
        self.assertEqual(self.cli("check"), (0, "OK"))
        self.assertEqual((self.claims(), Path(self.ap).read_bytes()), ([], before))
        self.write(adm=self.ad(owner_words="nope"))
        self.assertEqual(self.cli("admit")[0], 2)
        self.assertEqual(self.claims(), [])
        self.assertIs(self.used(), False)

    def test_plan_names_the_batch_and_starts_nothing(self):
        self.write()
        text = g.plan(self.fp, self.ap)
        self.assertIn("L2-R2-REH", text)
        self.assertIn("launches nothing", text)
        self.assertEqual(self.claims(), [])

    # required fields
    def test_each_freeze_key_missing_refused(self):
        for k in CORE + PRESENCE:
            with self.subTest(key=k):
                fr = dict(self.freeze); del fr[k]
                self.refused(k, freeze=fr)

    def test_each_admission_key_missing_refused(self):
        for k in ADM_KEYS:
            with self.subTest(key=k):
                ad = dict(self.adm); del ad[k]
                self.refused(k, adm=ad)

    def test_each_presence_field_empty_refused(self):
        for k in PRESENCE:
            for v in EMPTY:
                with self.subTest(key=k, value=v):
                    self.refused(f"freeze {k} missing or empty", freeze=self.fz(**{k: v}))

    def test_extra_key_in_either_record_refused(self):
        self.refused("unknown", freeze=self.fz(extra=1))
        self.refused("unknown", adm=self.ad(extra=1))

    def test_each_freeze_record_tamper_after_admission_refused(self):
        self.write()
        fr = json.loads(Path(self.fp).read_text()); fr["config_hash"] = "tampered"
        Path(self.fp).write_text(json.dumps(fr))
        rc, out = self.cli()
        self.assertEqual(rc, 2)
        self.assertIn("freeze_record_sha256", out)

    def test_admission_scalar_tampers_refused(self):
        cases = [("one_use", False, "one_use"), ("one_use", 1, "one_use"), ("used", True, "already used"),
                 ("used", 0, "used"), ("used", None, "used"), ("batch", "L2-R2-XXX", "batch"),
                 ("owner_words", "I admit something else", "owner words"),
                 ("freeze_record_sha256", "0" * 64, "freeze_record_sha256")]
        for k, v, why in cases:
            with self.subTest(key=k, value=v):
                self.refused(why, adm=self.ad(**{k: v}))

    # protocol and commit
    def test_changed_protocol_sha_refused_every_way(self):
        self.refused("protocol sha256", freeze=self.fz(protocol_sha256=sha(b"other")))
        self.refused("protocol sha256", freeze=self.fz(protocol_sha256=sha(b"protocol").upper()))
        self.refused("protocol sha256", freeze=self.fz(protocol_sha256=sha(b"protocol")[:-1] + "0"
                                                       if not sha(b"protocol").endswith("0")
                                                       else sha(b"protocol")[:-1] + "1"))

    def test_protocol_changed_in_later_commit_pinned_bytes_still_rule(self):
        (self.root / "proto.md").write_bytes(b"protocol v2")
        self.git("add", "."); self.git("commit", "-qm", "later")
        self.write()
        self.assertEqual(self.cli("check"), (0, "OK"))
        self.refused("protocol sha256", freeze=self.fz(protocol_sha256=sha(b"protocol v2")))

    def test_tree_and_commit_tamper_refused(self):
        self.refused("tree", freeze=self.fz(tree="0" * 40))
        self.refused("40", freeze=self.fz(commit=self.pin[:7]))
        self.refused("not found", freeze=self.fz(commit="1" * 40))

    # limits and window
    def test_admission_above_each_freeze_limit_refused_and_equal_admitted(self):
        self.write()
        self.assertEqual(self.cli("check")[0], 0)
        for k in LIMITS:
            with self.subTest(key=k):
                self.refused(f"{k} above freeze limit", adm=self.ad(**{k: self.freeze[k] + 0.5}))
        for k in LIMITS:
            with self.subTest(key=k, low=True):
                self.write(adm=self.ad(**{k: 0}))
                self.assertEqual(self.cli("check")[0], 0)

    def test_caller_caps_bind_each_limit(self):
        self.write()
        self.refused("gpu_cap", gpu=3)
        self.refused("hosted cap", hosted=2)  # plan 2.5 above 2
        self.refused("hosted cap", hosted=4)  # stop 5 above 4, plan below
        self.refused("max_window_hours", hours=11)
        self.assertEqual(self.cli("check", gpu=4, hosted=5, hours=12), (0, "OK"))

    def test_window_edges(self):
        self.write()
        self.assertEqual(self.cli("check", now="2026-12-01T00:00:00Z")[0], 0)
        self.assertEqual(self.cli("check", now="2026-12-01T11:59:59Z")[0], 0)
        for now in ("2026-12-01T12:00:00Z", "2026-11-30T23:59:59Z", "2026-12-01T05:00:00+02:00"):
            with self.subTest(now=now):
                self.refused("window" if "+02" not in now else "UTC", now=now)

    # protected inputs
    def test_every_protected_input_is_checked_not_just_the_first(self):
        for i in (0, 1):
            with self.subTest(i=i):
                pins = [dict(p) for p in self.freeze["protected_inputs"]]
                pins[i]["sha256"] = "0" * 64
                self.refused("protected input changed", freeze=self.fz(protected_inputs=pins))
        (self.root / "in2.txt").write_bytes(b"edited")
        self.refused("protected input changed")

    def test_empty_custodian_refused_for_every_entry(self):
        for i in (0, 1):
            for v in ("", "  ", None, [], 0):
                with self.subTest(i=i, value=v):
                    pins = [dict(p) for p in self.freeze["protected_inputs"]]
                    pins[i]["custodian"] = v
                    self.refused("custodian", freeze=self.fz(protected_inputs=pins))
        pins = [dict(p) for p in self.freeze["protected_inputs"]]
        del pins[1]["custodian"]
        self.refused("malformed", freeze=self.fz(protected_inputs=pins))
        self.refused("protected_inputs", freeze=self.fz(protected_inputs=[]))

    # no network, no secrets, read-only git only
    def test_no_network_no_secrets_only_readonly_git(self):
        calls = []
        real_run = subprocess.run

        def spy(cmd, *a, **k):
            calls.append((list(cmd), dict(k.get("env") or {})))
            return real_run(cmd, *a, **k)

        def no_net(*a, **k):
            raise AssertionError("network used")

        self.write()
        with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent", "GIT_WORK_TREE": "/nonexistent",
                                          "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.bare",
                                          "GIT_CONFIG_VALUE_0": "true"}), \
                mock.patch.object(subprocess, "run", spy), \
                mock.patch.object(socket.socket, "connect", no_net), \
                mock.patch.object(socket, "create_connection", no_net), \
                mock.patch.object(socket, "getaddrinfo", no_net):
            self.assertEqual(self.cli("admit"), (0, "OK"))
        self.assertTrue(calls)
        for cmd, env in calls:
            self.assertEqual(cmd[0], "git")
            self.assertIn(cmd[3], {"rev-parse", "merge-base", "cat-file"}, cmd)
            self.assertEqual(sorted(k for k in env if k.startswith("GIT_")),
                             ["GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"])
        self.assertEqual(self.claims(), ["L2-R2-REH"])

    def test_records_and_claim_hold_no_secret_shaped_values(self):
        self.write()
        self.cli("admit")
        text = (Path(self.ap).read_text() + Path(self.fp).read_text()
                + (self.root / ".git/tremor-admission-claims/L2-R2-REH").read_text()).lower()
        for needle in ("api_key", "secret", "password", "token", "bearer", "sk-"):
            self.assertNotIn(needle, text)

    def test_scratch_repo_is_under_scratch_and_cleaned(self):
        self.assertTrue(str(self.root).startswith(SCRATCH + "/" + PREFIX))
        self.assertEqual(self.git("config", "--local", "user.name"), "t")
        marker = self.root / "marker.txt"
        marker.write_text("x")
        _rmtree_owned(str(self.root))
        self.assertFalse(self.root.exists())
        self.assertFalse(marker.exists())
        # a path outside the scratch prefix is never removed
        other = Path(tempfile.mkdtemp(prefix="keep-", dir=SCRATCH))
        try:
            _rmtree_owned(str(other))
            self.assertTrue(other.exists())
        finally:
            shutil.rmtree(other)

    # floor, ancestry
    def test_pinned_commit_before_floor_refused(self):
        g.FLOOR_COMMIT = self.pin
        self.refused("before", freeze=self.fz(commit=self.floor,
                                              tree=self.git("rev-parse", self.floor + "^{tree}")))

    def test_pinned_commit_not_ancestor_of_head_refused(self):
        self.git("checkout", "-q", "-b", "side", self.floor)
        (self.root / "side.txt").write_text("s")
        self.git("add", "."); self.git("commit", "-qm", "side")
        side = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", self.pin)
        self.refused("ancestor", freeze=self.fz(commit=side, tree=self.git("rev-parse", side + "^{tree}")))

    # claim directory, hard link, recheck after write
    def test_claim_dir_is_owner_only_and_loose_dir_refused(self):
        self.write()
        self.assertEqual(self.cli("admit")[0], 0)
        cdir = self.root / ".git" / "tremor-admission-claims"
        self.assertEqual(os.stat(cdir).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(cdir / "L2-R2-REH").st_mode & 0o777, 0o600)
        # a pre-existing group/world-accessible claim dir is refused for a new batch
        os.chmod(cdir, 0o750)
        self.write(freeze=self.fz(batch="L2-R2-LOOSE"), adm=self.ad(batch="L2-R2-LOOSE"))
        rc, out = self.cli("admit")
        self.assertEqual((rc, "owner-only" in out), (2, True), out)
        self.assertEqual(sorted(os.listdir(cdir)), ["L2-R2-REH"])
        os.chmod(cdir, 0o700)

    def test_hard_linked_protected_input_refused(self):
        os.link(self.root / "in2.txt", self.root / "in2-link.txt")
        self.refused("hard link")

    def test_record_changed_while_being_claimed_refused(self):
        self.write()
        real = os.open

        def tamper(path, flags, *a, **k):
            fd = real(path, flags, *a, **k)
            if "tremor-admission-claims" in str(path):
                Path(self.ap).write_text(Path(self.ap).read_text() + " ")
            return fd

        with mock.patch.object(os, "open", tamper):
            rc, out = self.cli("admit")
        self.assertEqual(rc, 2)
        self.assertIn("changed while being claimed", out)
        self.assertIs(self.used(), False)


if __name__ == "__main__":
    unittest.main()
