import os
import pkgutil
import subprocess
import sys
import unittest

import tremor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ShimTests(unittest.TestCase):
    def test_every_submodule_is_the_same_object(self):
        import importlib
        names = [m.name for m in pkgutil.walk_packages(tremor.__path__, "tremor.") if not m.name.endswith(".__main__")]
        self.assertGreater(len(names), 40)
        for name in names:
            old = "murmuration." + name[len("tremor."):]
            self.assertIs(importlib.import_module(old), importlib.import_module(name), old)

    def test_from_import_and_nested_package(self):
        from murmuration import spend
        from murmuration.trapbench import alloc
        from tremor.trapbench import alloc as alloc2
        self.assertIs(spend, tremor.spend)
        self.assertIs(alloc, alloc2)

    def test_fresh_process_identity(self):
        code = ("import murmuration.trapbench.alloc as a, murmuration.spend as s, tremor.spend, tremor.trapbench.alloc;"
                "print(a is tremor.trapbench.alloc and s is tremor.spend)")
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
        out = subprocess.run([sys.executable, "-B", "-c", code], env=env, cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout.strip(), "True", out.stderr)

    def test_unknown_submodule_still_fails(self):
        with self.assertRaises(ImportError):
            __import__("murmuration.no_such_module")

    def _run(self, *args):
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
        return subprocess.run([sys.executable, "-B", "-W", "ignore", "-m", *args], env=env, cwd=ROOT,
                              capture_output=True, text=True, timeout=60)

    def test_python_dash_m_murmuration_help_still_works(self):
        old, new = self._run("murmuration", "--help"), self._run("tremor", "--help")
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertEqual(old.stdout, new.stdout)
        self.assertIn("usage: tremor", old.stdout)

    def test_help_names_the_new_key_variable(self):
        out = self._run("murmuration", "ep1", "--help").stdout
        self.assertIn("TREMOR_EP1_KEY", out)


if __name__ == "__main__":
    unittest.main()
