"""Direct Messages API client for the Claude backend. Stdlib only.

Safety shape: base URL is an argument (ANTHROPIC_BASE_URL and proxy variables are never read, so a local
proxy cannot answer with another provider's model); the key is an argument and never read from a file;
headers and the key are never logged or put in an exception; a returned model other than the requested
one (or an alias the price sheet documents) VOIDS the episode; spend is reserved before every request.
The base URL host must be api.anthropic.com, or (tests) an explicit allow_host that is loopback; redirects are
never followed; everything written to the ledger or returned is scrubbed of the key.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from murmuration import spend

DEFAULT_HOST = "api.anthropic.com"
DEFAULT_BASE_URL = "https://" + DEFAULT_HOST
ANTHROPIC_VERSION = "2023-06-01"
# Haiku 5.5 thinks when the field is absent; off keeps hidden thinking out of max_tokens (prereg change 13)
THINKING_OFF = {"type": "disabled"}
LOOPBACK = ("127.0.0.1", "localhost", "::1")


class EpisodeCapExceeded(Exception):
    pass


class EpisodeVoided(Exception):
    pass


class InputIntegrityError(Exception):
    """The batch's input check refused this request."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):  # a redirect could carry the key to another host
        return None


def _build_opener():  # ProxyHandler({}) = no proxies, whatever HTTP(S)_PROXY says
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


_OPENER = _build_opener()


def _check_pilot_ledger(ledger):
    """The real host may only use ledgers in the one pinned directory: the USD 10 cap counts that directory."""
    pilot, path = spend.PILOT_LEDGER_DIR, os.path.abspath(ledger.path)
    name = os.path.basename(path)
    if os.path.dirname(path) != pilot or os.path.realpath(pilot) != pilot or os.path.islink(pilot):
        raise ValueError("a ledger for api.anthropic.com must be a direct, non-symlinked file in the pilot ledger directory")
    if not name.endswith(".jsonl") or name != name.lower() or name.startswith("."):
        raise ValueError("a ledger for api.anthropic.com must have a lower-case .jsonl name")
    if os.path.islink(path) or (os.path.exists(path) and not os.path.isfile(path)):
        raise ValueError("the ledger file must not be a symlink or a non-regular file")


class Episode:
    def __init__(self, episode_id, token_cap, wall_seconds):
        self.id, self.token_cap, self.wall_seconds = episode_id, token_cap, wall_seconds
        self.tokens, self.t0, self.void = 0, time.monotonic(), None
        self.records = []
        self.unbilled_usd = 0.0  # worst case kept in the ledger for attempts that returned no usage (retries)

    @property
    def usd(self):
        """Ledger spend for this episode: every charge plus the worst case of every failed attempt."""
        return sum(r["usd"] for r in self.records) + self.unbilled_usd


class ClaudeClient:
    def __init__(self, api_key, ledger, base_url=DEFAULT_BASE_URL, timeout=120, version=ANTHROPIC_VERSION,
                 allow_host=None):
        if not api_key or not isinstance(api_key, str):
            raise ValueError("api_key must be passed explicitly by the caller")
        u = urllib.parse.urlsplit(base_url)
        try:
            port = u.port
        except ValueError:
            raise ValueError("base_url has a bad port") from None
        if u.username is not None or u.password is not None or u.query or u.fragment or u.path not in ("", "/"):
            raise ValueError("base_url must be a bare scheme://host[:port]")
        if u.hostname == DEFAULT_HOST:
            if u.scheme != "https" or port not in (None, 443):
                raise ValueError("api.anthropic.com must be https on port 443")
            _check_pilot_ledger(ledger)
        else:
            # any other host needs an explicit allow_host, and a key is only ever sent to loopback (tests)
            if allow_host is None or u.hostname != allow_host:
                raise ValueError(f"base_url host {u.hostname!r} is not api.anthropic.com and not allow_host")
            if u.hostname not in LOOPBACK:
                raise ValueError("a key is never sent to a non-loopback host other than api.anthropic.com")
            if u.scheme not in ("http", "https"):
                raise ValueError("base_url scheme must be http or https")
        self._key, self.ledger, self.base_url, self.timeout, self.version = api_key, ledger, base_url.rstrip("/"), timeout, version

    def _scrub(self, s):
        s = str(s)
        for part in {self._key, self._key[:10], self._key[-10:]}:  # a server may echo only a piece
            s = s.replace(part, "[redacted]")
        return s

    def _post(self, body, timeout):
        req = urllib.request.Request(
            self.base_url + "/v1/messages", data=body, method="POST",
            headers={"x-api-key": self._key, "anthropic-version": self.version, "content-type": "application/json"})
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read(65536))
            except ValueError:
                return e.code, {}

    def call(self, episode, call_id, model, messages, max_tokens, temperature=0.0, system=None, canary_input_tokens=None,
             batch=None, before_request=None):
        """One /v1/messages request. Returns the per-call record (also written to the ledger).

        Retries at most once, only when the first attempt produced no usable response (network error,
        429, 5xx); the retry has its own reserve entry under f"{call_id}#r1" so it is counted and capped.
        """
        if episode.void:
            raise EpisodeVoided(episode.void)
        if batch != self.ledger.batch and batch is not None:  # the ledger's batch is authoritative; a mismatch fails closed
            raise spend.SpendError(f"call batch {batch!r} does not match the ledger's batch {self.ledger.batch!r}")
        if not spend._pos_int(max_tokens, spend.MAX_TOKENS_LIMIT):
            raise spend.SpendError(f"max_tokens must be a positive int <= {spend.MAX_TOKENS_LIMIT}")
        for m in messages:  # image/document blocks break the bytes >= tokens bound
            c = m.get("content") if isinstance(m, dict) else None
            if not (isinstance(c, str) or (isinstance(c, list) and all(isinstance(b, dict) and b.get("type") == "text" for b in c))):
                raise ValueError("only text messages are allowed (token bound needs bytes >= tokens)")
        payload = {"model": model, "max_tokens": max_tokens, "temperature": temperature, "messages": messages,
                   "thinking": dict(THINKING_OFF)}
        if system:
            payload["system"] = system
        body = json.dumps(payload, sort_keys=True).encode()
        with self.ledger.exclusive_request():
            return self._request(episode, call_id, model, body, max_tokens, canary_input_tokens, before_request)

    def _request(self, episode, call_id, model, body, max_tokens, canary_input_tokens, before_request):
        ub = len(body)  # bytes >= tokens, so a strict input upper bound
        req_sha = hashlib.sha256(body).hexdigest()
        err = None
        for attempt in (0, 1):
            cid = call_id if attempt == 0 else f"{call_id}#r1"
            if before_request is not None:
                before_request()
            left = episode.wall_seconds - (time.monotonic() - episode.t0)
            if left <= 0:
                raise EpisodeCapExceeded("episode wall-second cap reached")
            if episode.tokens + ub + max_tokens > episode.token_cap:
                raise EpisodeCapExceeded("episode token cap would be crossed by this call")
            worst = self.ledger.reserve(cid, model, ub, max_tokens, canary_input_tokens)
            t0 = time.monotonic()
            try:
                status, resp = self._post(body, min(self.timeout, left))
            except (OSError, ValueError) as e:  # URLError/timeout are OSError
                status, resp, err = None, {}, self._scrub(f"{type(e).__name__}: {e}")[:200]
            wall = time.monotonic() - t0
            usage = resp.get("usage") if isinstance(resp, dict) else None
            if status == 200 and isinstance(resp, dict) and resp.get("model"):  # usage checked (fail closed) in charge
                return self._record(episode, cid, model, resp, usage, wall, req_sha, ub)
            if status is not None:
                err = f"HTTP {status} {self._scrub(json.dumps(resp.get('error', {})) if isinstance(resp, dict) else '')[:200]}"
            self.ledger.void_unknown(cid, error=err, wall_seconds=wall, requested_model=model)
            episode.unbilled_usd += worst
            if attempt == 0 and (status is None or status == 429 or status >= 500):
                continue
            break
        raise RuntimeError(f"claude call {call_id} failed: {err}")

    def _record(self, episode, cid, model, resp, usage, wall, req_sha, request_bytes):
        s = self._scrub
        returned = s(resp["model"]) if isinstance(resp["model"], str) else "[non-string model]"
        stop = s(resp.get("stop_reason")) if resp.get("stop_reason") is not None else None
        blocks = resp.get("content") if isinstance(resp.get("content"), list) else []
        types = [s(str(b.get("type")))[:32] if isinstance(b, dict) else "?" for b in blocks][:16]  # scrub before cut (G0-2R4)
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))
        void = None if self.ledger.sheet.accepts(model, returned) else f"returned model {returned!r} != requested {model!r}"
        response_id = resp.get("id")
        metadata = {"request_bytes": request_bytes, "provider_input_truncated": None}
        if (isinstance(response_id, str) and 0 < len(response_id) <= 128
                and s(response_id) == response_id and re.fullmatch(r"msg_[A-Za-z0-9]+", response_id)):
            metadata["provider_response_id"] = response_id
        usd = self.ledger.charge(
            cid, model, usage, requested_model=model, returned_model=returned, void=void,
            stop_reason=stop, wall_seconds=wall, request_sha256=req_sha,
            response_sha256=hashlib.sha256(text.encode()).hexdigest(), episode=episode.id, **metadata)
        u = spend.clean_usage(usage)  # charge() already accepted it
        episode.tokens += sum(u.get(k) or 0 for k in spend.USAGE_FIELDS)
        rec = {"id": cid, "requested_model": model, "returned_model": returned, "usage": u, "usd": usd,
               "void": void, "text": s(text), "stop_reason": stop, "wall_seconds": wall, "block_types": types, **metadata}
        episode.records.append(rec)
        if void:
            episode.void = void
        return rec
