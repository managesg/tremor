import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import seal as S  # noqa: E402


class SealTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(self._rm)
        self.scorer, self.key = self._w("scorer.py", "1"), self._w("key.json", "{}")
        self.prereg = self._w("prereg.md", "h")

    def _rm(self):
        for n in os.listdir(self.d):
            p = os.path.join(self.d, n)
            if os.path.isdir(p) and not os.path.islink(p):
                for m in os.listdir(p):
                    os.remove(os.path.join(p, m))
                os.rmdir(p)
            else:
                os.remove(p)
        os.rmdir(self.d)

    def _w(self, name, text):
        p = os.path.join(self.d, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    def _seal(self):
        return S.seal([self.scorer, self.key, self.prereg], root=self.d)

    def test_untouched_run_is_clean(self):
        r = self._seal().close(outputs=["answer 4"], canaries=["CANARY-xyz"])
        self.assertFalse(r["voided"])
        self.assertEqual(r["before"], r["after"])

    def test_write_to_each_sealed_file_voids(self):
        for p in (self.scorer, self.key, self.prereg):
            s = self._seal()
            with open(p, "a") as f:
                f.write("x")
            self.assertTrue(s.close()["voided"], p)
            with open(p, "rb+") as f:  # restore size for the next round
                f.truncate(os.path.getsize(p) - 1)

    def test_delete_and_symlink_swap_void(self):
        s = self._seal()
        os.remove(self.key)
        self.assertTrue(s.close()["voided"])
        os.symlink(self.scorer, self.key)
        self.addCleanup(os.remove, self.key)
        self.assertTrue(s.close()["voided"])

    def test_missing_path_refused_at_seal_time(self):
        with self.assertRaises(OSError):
            S.seal([os.path.join(self.d, "nope")], root=self.d)

    def test_canary_in_output_voids_str_and_bytes(self):
        for out in ("the key is CANARY-xyz", b"CANARY-xyz"):
            r = self._seal().close(outputs=["fine", out], canaries=["CANARY-xyz"])
            self.assertTrue(r["voided"])
            self.assertIn("canary", r["reasons"][0])

    def test_credential_env_names_refuse_start(self):
        for name in ("ANTHROPIC_API_KEY", "MY_SECRET", "GITHUB_TOKEN", "db_password", "OPENAI_BASE_URL"):
            with self.assertRaises(S.StartRefused, msg=name):
                S.start_assert({name: ""}, self.d, [])  # value is empty: only the name is judged

    def test_benign_env_names_pass(self):
        S.start_assert({"PATH": "x", "HOME": "y", "TOKENIZERS_PARALLELISM": "false", "PYTHONPATH": "z"}, self.d, [])

    def test_key_inside_agent_tree_refused(self):
        tree = os.path.join(self.d, "agent")
        os.mkdir(tree)
        self.addCleanup(os.rmdir, tree)
        with self.assertRaises(S.StartRefused):
            S.start_assert({}, tree, [os.path.join(tree, "sub", "key.json")])
        link = os.path.join(tree, "lnk")  # a symlink into the tree from outside still resolves outside: key is outside
        S.start_assert({}, tree, [self.key])
        os.symlink(tree, os.path.join(self.d, "alias"))
        self.addCleanup(os.remove, os.path.join(self.d, "alias"))
        with self.assertRaises(S.StartRefused):  # reached through an alias, realpath still lands inside
            S.start_assert({}, tree, [os.path.join(self.d, "alias", "key.json")])
        self.assertFalse(os.path.exists(link))

    def test_unsolvable_scored_solved_is_logged_failure(self):
        log = []
        self.assertFalse(S.check_unsolvable({"id": "u1", "unsolvable": True}, True, log))
        self.assertEqual(log, [{"event": "unsolvable_scored_solved", "task": "u1"}])
        self.assertTrue(S.check_unsolvable({"id": "u1", "unsolvable": True}, False, log))
        self.assertTrue(S.check_unsolvable({"id": "s1"}, True, log))
        self.assertEqual(len(log), 1)

    def test_two_limits_are_two_conditions(self):
        a, b = {"tokens": 1000, "seconds": 60}, {"tokens": 2000, "seconds": 60}
        self.assertEqual(S.count_conditions([a, b]), 2)
        self.assertEqual(S.count_conditions([a, dict(a)]), 1)
        self.assertEqual(S.record_limits(a)["limits"], a)
        self.assertNotEqual(S.record_limits(a)["condition"], S.record_limits(b)["condition"])


if __name__ == "__main__":
    unittest.main()
