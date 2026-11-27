import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tremor import cell  # noqa: E402

POL = {"allow": ["read"], "deny": [], "max_tokens": 1000, "max_seconds": 10}
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")


def procs(code, n, *args):
    """n real processes running code (sys.argv[1:] = args, sys.argv[-1] = worker index); all start when go exists."""
    go = os.path.join(args[0], "go")
    head = (f"import os, sys, time; sys.path.insert(0, {SRC!r})\n"
            f"while not os.path.exists({go!r}): time.sleep(0.001)\n")
    ps = [subprocess.Popen([sys.executable, "-B", "-I", "-c", head + code, *args, str(i)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(n)]
    open(go, "w").close()
    return [p.communicate(timeout=120) + (p.returncode,) for p in ps]


class CellTests(unittest.TestCase):
    def test_create_load_and_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = cell.create(os.path.join(d, "a"), "a", "stub", "scripted-m0", POL)
            c, pol = cell.load(p)
            self.assertEqual((c["kind"], c["model"], pol["allow"]), ("stub", "scripted-m0", ["read"]))

    def test_same_answer_strong_costs_more(self):
        spec = {"id": "t", "class": "extract", "payload": {"text": "b a b c"}}
        s = cell.work({"kind": "stub"}, spec)
        g = cell.work({"kind": "scripted_strong"}, spec)
        self.assertEqual(s["answer"], g["answer"])
        self.assertEqual(s["answer"], ["a", "b", "c"])
        self.assertGreater(g["tokens"]["input"], s["tokens"]["input"])

    def test_unknown_kind_and_class(self):
        with self.assertRaises(ValueError):
            cell.work({"kind": "x"}, {"class": "extract", "payload": {"text": ""}})
        with self.assertRaises(ValueError):
            cell.work({"kind": "stub"}, {"class": "nope", "payload": {}})

    def test_log_chain_detects_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                cell.append_log(d, {"i": i})
            self.assertTrue(cell.verify_log(d))
            p = os.path.join(d, "log.jsonl")
            lines = open(p).read().splitlines()
            lines[1] = lines[1].replace('"i": 1', '"i": 9')
            open(p, "w").write("\n".join(lines) + "\n")
            self.assertFalse(cell.verify_log(d))

    def _log(self, d, n=3):
        for i in range(n):
            head = cell.append_log(d, {"i": i})
        return head, os.path.join(d, "log.jsonl")

    def test_log_last_line_edit_truncation_deletion_malformed(self):
        for how in ("last", "truncate", "delete", "malformed", "head_file_removed"):
            with tempfile.TemporaryDirectory() as d:
                head, p = self._log(d)
                self.assertTrue(cell.verify_log(d, head))
                lines = open(p).read().splitlines()
                if how == "last":
                    lines[-1] = lines[-1].replace('"i": 2', '"i": 9')
                elif how == "truncate":
                    lines = lines[:-1]
                elif how == "malformed":
                    lines[-1] = "{not json"
                if how == "delete":
                    os.remove(p)
                elif how == "head_file_removed":
                    os.remove(os.path.join(d, "log.head"))
                else:
                    open(p, "w").write("\n".join(lines) + "\n")
                self.assertFalse(cell.verify_log(d), how)

    def test_log_expected_head_must_be_in_chain(self):
        with tempfile.TemporaryDirectory() as d:
            head, _ = self._log(d)
            self.assertFalse(cell.verify_log(d, "0" * 63 + "1"))
            self.assertTrue(cell.verify_log(d, head))
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(cell.verify_log(d))  # nothing logged, nothing recorded

    def test_verify_handler_recomputes_the_answer(self):
        pay = {"text": "b a"}
        ok = {"id": "v", "class": "verify", "payload": {"id": "t", "class": "extract", "payload": pay, "result": ["a", "b"]}}
        bad = {"id": "v", "class": "verify", "payload": {"id": "t", "class": "extract", "payload": pay, "result": ["x"]}}
        self.assertIs(cell.work({"kind": "stub"}, ok)["answer"], True)
        self.assertIs(cell.work({"kind": "stub"}, bad)["answer"], False)

    def test_policy_without_limits_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ({"allow": []}, dict(POL, max_tokens=None), dict(POL, max_seconds=0), dict(POL, max_tokens=True)):
                with self.assertRaises(ValueError):
                    cell.create(os.path.join(d, "x"), "x", "stub", "scripted", bad)
            p = cell.create(os.path.join(d, "ok"), "ok", "stub", "scripted", POL)
            with open(os.path.join(p, "policy.json"), "w") as f:
                json.dump({"allow": ["read"]}, f)  # tampered/loaded without limits
            with self.assertRaises(ValueError):
                cell.load(p)

    def test_cell_id_must_be_a_safe_name(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("../x", "a/b", "", "..", "a..b", "/abs", "x\n", "\nx", "x\r"):
                with self.assertRaises(ValueError):
                    cell.create(os.path.join(d, "x"), bad, "stub", "scripted", POL)

    def test_plan_ids_include_plan_id_and_negative_extra_seconds_refused(self):
        a = cell.work({"kind": "stub"}, {"id": "p1", "class": "plan", "payload": {"goal": "g h", "steps": ["a"]}})
        b = cell.work({"kind": "stub"}, {"id": "p2", "class": "plan", "payload": {"goal": "g h", "steps": ["a"]}})
        self.assertNotEqual(a["answer"][0]["id"], b["answer"][0]["id"])
        self.assertTrue(cell.valid_name(a["answer"][0]["id"]))
        with self.assertRaises(ValueError):  # negative extra_seconds would hide time: refused, not floored
            cell.work({"kind": "scripted_strong"}, {"class": "extract", "payload": {"text": "a"}, "extra_seconds": -100})


class ConcurrencyTests(unittest.TestCase):
    def test_four_processes_appending_keep_one_valid_chain(self):
        """kills: append_log without the cell lock (read-prev-then-append forks the chain)."""
        with tempfile.TemporaryDirectory() as d:
            res = procs("from tremor import cell\n"
                        "for j in range(200): cell.append_log(sys.argv[1], {'w': sys.argv[2], 'j': j})\n", 4, d)
            self.assertEqual([r[2] for r in res], [0] * 4, [r[1][-300:] for r in res])
            self.assertEqual(cell.log_count(d), 800)
            self.assertTrue(cell.verify_log(d))
            rows = [json.loads(x)["entry"] for x in open(os.path.join(d, "log.jsonl"))]
            for w in "0123":  # every writer's lines are all there, in its own order
                self.assertEqual([r["j"] for r in rows if r["w"] == w], list(range(200)))

    def test_lock_timeout_fails_closed(self):
        """A cell held by another writer past LOCK_TIMEOUT: append raises, verify_log is False, nothing written."""
        with tempfile.TemporaryDirectory() as d:
            cell.append_log(d, {"i": 0})
            old, cell.LOCK_TIMEOUT = cell.LOCK_TIMEOUT, 0.05
            self.addCleanup(setattr, cell, "LOCK_TIMEOUT", old)
            with cell.locked(d):  # flock is per open file, so this blocks the calls below like another process
                with self.assertRaises(TimeoutError):
                    cell.append_log(d, {"i": 1})
                self.assertIs(cell.verify_log(d), False)
            self.assertEqual(cell.log_count(d), 1)
            self.assertTrue(cell.verify_log(d))

    def test_append_refuses_a_broken_chain(self):
        with tempfile.TemporaryDirectory() as d:
            cell.append_log(d, {"i": 0})
            with open(os.path.join(d, "log.jsonl"), "a") as f:
                f.write("{}\n")
            with self.assertRaises(ValueError):
                cell.append_log(d, {"i": 1})

    def test_open_never_follows_a_swapped_component(self):
        """kills: plain open with O_NOFOLLOW on the last component only. A directory on the way is swapped for a
        symlink after join(): the write fails closed and nothing is created or truncated outside."""
        with tempfile.TemporaryDirectory() as d:
            c = cell.create(os.path.join(d, "c"), "c", "stub", "scripted", POL)
            os.mkdir(os.path.join(c, "outbox"))
            out = os.path.join(d, "outside")
            os.mkdir(out)
            open(os.path.join(out, "t.json"), "w").write("keep")
            p = cell.join(c, "outbox", "t.json")
            os.rename(os.path.join(c, "outbox"), os.path.join(d, "moved"))
            os.symlink(out, os.path.join(c, "outbox"))
            for kw in ({}, {"append": True}, {"exclusive": True}):
                with self.assertRaises(ValueError, msg=kw):
                    cell._write(p, "x", **kw)
                # the swap lands after the path was resolved: modelled by a resolver that no longer sees it
                with mock.patch.object(cell.os.path, "realpath", lambda q: q), self.assertRaises(ValueError, msg=kw):
                    cell._write(p, "x", **kw)
            self.assertEqual(sorted(os.listdir(out)), ["t.json"])
            self.assertEqual(open(os.path.join(out, "t.json")).read(), "keep")

    def test_open_refuses_a_file_replaced_between_open_and_check(self):
        """kills: _open without the dev/ino re-check (the open file must be the one at the path)."""
        with tempfile.TemporaryDirectory() as d:
            c = cell.create(os.path.join(d, "c"), "c", "stub", "scripted", POL)
            p = cell.join(c, "cell.json")
            real = os.stat

            def swapped(q, *a, **k):
                st = real(q, *a, **k)
                return os.stat_result((st[0], st[1] + 1) + tuple(st)[2:]) if q == p else st
            with mock.patch.object(cell.os, "stat", swapped), self.assertRaises(ValueError):
                cell._read(p)
            self.assertTrue(cell._read(p))  # control: unswapped, it reads


if __name__ == "__main__":
    unittest.main()
