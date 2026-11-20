import ast
import glob
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import backend_claude, manifest, router  # noqa: E402

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
FILES = sorted(glob.glob(os.path.join(SRC, "**", "*.py"), recursive=True))
NET = {"socket", "ssl", "http", "urllib.request", "ftplib", "smtplib", "telnetlib", "poplib", "imaplib", "xmlrpc",
       "requests", "httpx", "aiohttp", "websocket", "websockets", "asyncio", "socketserver", "selectors"}
SHELL = {"system", "popen", "popen2", "popen3", "spawnl", "spawnv", "startfile"}


def _parse(p):
    with open(p) as f:
        return ast.parse(f.read(), p)


def _imports(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            yield from (a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            yield n.module
            yield from (f"{n.module}.{a.name}" for a in n.names)


def _is_net(name):
    return any(name == m or name.startswith(m + ".") for m in NET)


class EgressScan(unittest.TestCase):
    def test_sources_found(self):
        self.assertTrue(any(p.endswith("backend_claude.py") for p in FILES))

    def test_only_backend_claude_opens_a_connection(self):
        for p in FILES:
            names = [n for n in _imports(_parse(p)) if _is_net(n)]
            if os.path.basename(p) != "backend_claude.py":
                self.assertEqual(names, [], f"{p} imports a network module")

    def test_no_dynamic_import_anywhere(self):
        for p in FILES:
            for n in ast.walk(_parse(p)):
                if isinstance(n, ast.Call):
                    f = n.func
                    self.assertFalse(isinstance(f, ast.Name) and f.id == "__import__", p)
                    self.assertFalse(isinstance(f, ast.Attribute) and f.attr == "import_module", p)

    def test_no_eval_exec_or_shell(self):
        for p in FILES:
            for n in ast.walk(_parse(p)):
                if not isinstance(n, ast.Call):
                    continue
                f = n.func
                self.assertFalse(isinstance(f, ast.Name) and f.id in ("eval", "exec", "compile"), f"{p}:{n.lineno}")
                self.assertFalse(isinstance(f, ast.Attribute) and f.attr in SHELL, f"{p}:{n.lineno}")
                for k in n.keywords:
                    if k.arg == "shell":
                        self.assertIsInstance(k.value, ast.Constant)
                        self.assertIs(k.value.value, False, f"{p}:{n.lineno} shell=True")

    def test_subprocess_gets_a_list_never_a_string(self):
        for p in FILES:
            for n in ast.walk(_parse(p)):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                        and n.func.value.id == "subprocess" and n.func.attr in ("run", "Popen", "call", "check_output", "check_call")):
                    self.assertNotIsInstance(n.args[0], (ast.Constant, ast.JoinedStr, ast.Call), f"{p}:{n.lineno}")


class DestinationPinned(unittest.TestCase):
    def test_backend_reads_no_environment(self):
        tree = _parse(os.path.join(SRC, "murmuration", "backend_claude.py"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute):
                self.assertNotIn(n.attr, ("environ", "getenv", "environb"))
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"[A-Za-z_]+", n.value):
                self.assertNotRegex(n.value.upper(), r"(^|_)PROXY$|BASE_URL")

    def test_env_does_not_change_destination(self):
        env = {"ANTHROPIC_BASE_URL": "http://evil.example", "HTTPS_PROXY": "http://evil.example:3128",
               "HTTP_PROXY": "http://evil.example:3128", "ALL_PROXY": "http://evil.example:3128"}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v) for k, v in old.items()])
        c = backend_claude.ClaudeClient("k" * 20, ledger=None, base_url="http://127.0.0.1:9", allow_host="127.0.0.1")
        self.assertEqual(c.base_url, "http://127.0.0.1:9")
        # ProxyHandler({}) registers nothing, so no proxy handler may be present: the default one would read the env
        self.assertEqual([h for h in backend_claude._build_opener().handlers if isinstance(h, urllib.request.ProxyHandler)], [])

    def test_other_hosts_and_non_loopback_refused(self):
        for url, allow in (("https://evil.example", None), ("https://evil.example", "evil.example"),
                           ("http://api.anthropic.com", None)):
            with self.assertRaises(ValueError, msg=url):
                backend_claude.ClaudeClient("k" * 20, ledger=None, base_url=url, allow_host=allow)

    def test_redirect_is_refused(self):
        handlers = backend_claude._build_opener().handlers
        self.assertTrue(any(isinstance(h, backend_claude._NoRedirect) for h in handlers))
        self.assertFalse(any(type(h) is urllib.request.HTTPRedirectHandler for h in handlers))
        req = urllib.request.Request("http://127.0.0.1:9/v1/messages", data=b"{}", method="POST")
        self.assertIsNone(backend_claude._NoRedirect().redirect_request(req, None, 302, "Found", {}, "http://evil.example/"))


class SymlinkEscape(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(self._rm)
        self.outside = os.path.join(self.d, "outside")
        self.run = os.path.join(self.d, "run")
        os.makedirs(self.outside)
        os.makedirs(os.path.join(self.run, "cells"))
        os.makedirs(os.path.join(self.run, "tasks"))
        with open(os.path.join(self.outside, "secret.txt"), "w") as f:
            f.write("s")

    def _rm(self):
        shutil.rmtree(self.d)  # rmtree never follows symlinks

    def test_manifest_rejects_symlinked_file_and_dir(self):
        os.symlink(os.path.join(self.outside, "secret.txt"), os.path.join(self.run, "f"))
        with self.assertRaises(ValueError):
            manifest.tree_hash([self.run], root=self.d)
        os.remove(os.path.join(self.run, "f"))
        os.symlink(self.outside, os.path.join(self.run, "d"))
        with self.assertRaises(ValueError):
            manifest.tree_hash([self.run], root=self.d)

    def test_router_rejects_cell_symlinked_out_of_run_dir(self):
        os.symlink(self.outside, os.path.join(self.run, "cells", "c1"))
        with open(os.path.join(self.run, "tasks", "t1.json"), "w") as f:
            json.dump({"id": "t1", "class": "x", "payload": {}, "cell": "c1"}, f)
        with self.assertRaisesRegex(ValueError, "escapes"):
            router.run_dir(os.path.join(self.run, "tasks"), os.path.join(self.run, "cells"))
        self.assertEqual(os.listdir(self.outside), ["secret.txt"])  # nothing was written outside


if __name__ == "__main__":
    unittest.main()
