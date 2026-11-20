"""Fake Messages API on 127.0.0.1 (ephemeral port) for tests. Never talks to a real provider."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def start(responder):
    """responder(path, headers, body_dict, n) -> (status, dict). Returns (server, base_url, seen list)."""
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            seen.append({"path": self.path, "headers": dict(self.headers), "body": body})
            status, out, *extra = responder(self.path, self.headers, body, len(seen))
            data = json.dumps(out).encode()  # NaN/Infinity are emitted as-is, like a misbehaving server
            self.send_response(status)
            for k, v in (extra[0] if extra else {}).items():
                self.send_header(k, v)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}", seen


def ok(model, text="SELECT 1", usage=None):
    return 200, {"model": model, "stop_reason": "end_turn", "content": [{"type": "text", "text": text}],
                 "usage": usage or {"input_tokens": 100, "output_tokens": 10, "cache_read_input_tokens": 50,
                                    "cache_creation_input_tokens": 20,
                                    "cache_creation": {"ephemeral_5m_input_tokens": 5, "ephemeral_1h_input_tokens": 15}}}


def dry_run(task, arm, seed, ledger, price_sheet, responder=None, **kw):
    """Whole claude path against the fake server only: no key, no network beyond 127.0.0.1.
    Returns (run record, requests the fake server saw)."""
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from murmuration import runner
    srv, url, seen = start(responder or (lambda *a: ok("claude-sonnet-5-5")))
    try:
        rec = runner.run(task, arm, seed, "claude", allow_backend=True, spend_ledger=ledger, price_sheet=price_sheet,
                         base_url=url, dry_run=True, **kw)
    finally:
        srv.shutdown()
    return rec, seen
