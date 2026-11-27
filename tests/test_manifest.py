import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor import manifest, stats  # noqa: E402


class T(unittest.TestCase):
    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "a.py")
            open(f, "wb").write(b"x=1\n")
            h = manifest.tree_hash([d])
            self.assertEqual(h, manifest.tree_hash([d]))
            open(f, "wb").write(b"x=2\n")
            self.assertNotEqual(h, manifest.tree_hash([d]))

    def _tree(self, root, body=b"x=1\n", name="a.py"):
        os.makedirs(os.path.join(root, "sub"))
        open(os.path.join(root, "sub", name), "wb").write(body)

    def test_hash_location_and_spelling_independent(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            self._tree(os.path.join(d1, "one"))
            self._tree(os.path.join(d2, "other", "deeper"))
            h = manifest.tree_hash([os.path.join(d1, "one")])
            self.assertEqual(h, manifest.tree_hash([os.path.join(d2, "other", "deeper")]))
            self.assertEqual(h, manifest.tree_hash([os.path.join(d1, "one", "sub", "..")]))
            cwd = os.getcwd()
            os.chdir(d1)
            try:
                self.assertEqual(h, manifest.tree_hash(["one"]))
            finally:
                os.chdir(cwd)

    def test_check_prereg_passes_elsewhere_fails_on_edit(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            self._tree(d1 + "/t")
            self._tree(d2 + "/u")
            frozen = manifest.tree_hash([d1 + "/t"])
            stats.check_prereg(frozen, [d2 + "/u"])
            open(d2 + "/u/sub/a.py", "wb").write(b"x=2\n")
            with self.assertRaises(ValueError):
                stats.check_prereg(frozen, [d2 + "/u"])

    def test_rename_and_one_byte_edit_change_hash(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2, \
                tempfile.TemporaryDirectory() as d3:
            self._tree(d1 + "/t")
            self._tree(d2 + "/t", name="b.py")
            self._tree(d3 + "/t", body=b"x=2\n")
            h = manifest.tree_hash([d1 + "/t"])
            self.assertNotEqual(h, manifest.tree_hash([d2 + "/t"]))
            self.assertNotEqual(h, manifest.tree_hash([d3 + "/t"]))

    def test_move_changes_hash_same_content_other_checkout_does_not(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            for base in (d1, d2):
                os.makedirs(base + "/proj/train")
                os.makedirs(base + "/proj/src")
                open(base + "/proj/train/t7_edit.py", "wb").write(b"x=1\n")
            h1 = manifest.tree_hash([d1 + "/proj/train", d1 + "/proj/src"], root=d1 + "/proj")
            self.assertEqual(h1, manifest.tree_hash([d2 + "/proj/train", d2 + "/proj/src"], root=d2 + "/proj"))
            os.rename(d1 + "/proj/train/t7_edit.py", d1 + "/proj/src/t7_edit.py")
            self.assertNotEqual(h1, manifest.tree_hash([d1 + "/proj/train", d1 + "/proj/src"], root=d1 + "/proj"))

    def test_identical_bytes_at_distinct_paths_not_deduped(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("a.py", "b.py"):
                open(os.path.join(d, n), "wb").write(b"x=1\n")
            two = manifest.tree_hash([d], root=d)
            os.remove(os.path.join(d, "b.py"))
            self.assertNotEqual(two, manifest.tree_hash([d], root=d))

    def test_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self._tree(d + "/t")
            os.symlink(d + "/t/sub/a.py", d + "/t/l.py")
            with self.assertRaisesRegex(ValueError, "symlink"):
                manifest.tree_hash([d + "/t"])
            os.remove(d + "/t/l.py")
            os.symlink(d + "/t/sub", d + "/t/ldir")
            with self.assertRaisesRegex(ValueError, "symlink"):
                manifest.tree_hash([d + "/t"])
            os.remove(d + "/t/ldir")
            os.symlink(d + "/t", d + "/top")
            with self.assertRaisesRegex(ValueError, "symlink"):
                manifest.tree_hash([d + "/top"])

    def test_build(self):
        m = manifest.build({"a": 1}, 7, root="/nonexistent-dir")
        self.assertIsNone(m["git_sha"])
        self.assertIsNone(m["price_sheet_source"])
        self.assertEqual(m["seed"], 7)
        self.assertEqual(m["config_hash"], manifest.build({"a": 1}, 8)["config_hash"])
        self.assertNotEqual(m["config_hash"], manifest.build({"a": 2}, 7)["config_hash"])


if __name__ == "__main__":
    unittest.main()
