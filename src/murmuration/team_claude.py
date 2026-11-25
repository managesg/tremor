"""EP-1 model loop (B2, G1b fixes): the team.py episode structure with each agent turn as ONE model call. stdlib only.

`client` has the real ClaudeClient.call surface: `.call(episode, call_id, model, messages, max_tokens, temperature,
system=..., canary_input_tokens=None, batch=None)` returning the per-call record. Only an unmodified, constructed
ClaudeClient on api.anthropic.com yields `instrument_validation: false, evidence: "model"`; anything else is FAKE.
The record's `model` is the model the responses named, never the request.
The model sees prompt text only: the committed board view (replayed from the verified log, so one stale snapshot
per round), the tasks' check strings, its own id and a status line. Never `expect`, `shared` or the Board.

Round rules (prereg section 6; docs/reports/workplan-ep/G1b-fixes.md): a reply is one JSON array of actions, a bare
object counting as a list of one. Round 1: one claim, or pass. Round 2: claim, work, release, each optional and at
most once, in that order; or pass alone. Every task id must be one of the ids shown. Anything else is `malformed`:
the turn is lost, the reply is recorded with a reason, nothing is repaired. The harness sets `agent`.
Each round every agent is called once (read, then call); then the replies execute through router.act in the board's
seeded order (see `seeded`), each reply's actions in their order. A refused action is lost and counts as one refusal
of that agent (D3); its later actions are still sent and buy no extra call. A release of the task claimed in the same
reply runs after the round's claims are resolved (end_round), so a round-1 loser can claim, work and release.
"""
import hashlib
import json
import os
import random
import re
import tempfile
import urllib.parse

from murmuration import backend_claude as bc
from murmuration import board, cell, orders, router, spend, team
from murmuration import practice as practicemod
from murmuration.trapbench import alloc

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts", "ep1")
TEMPLATES = ("system.md", "turn.md")
FAKE_STAMP = "FAKE: loopback fake server or scripted responder; not evidence about any model"
REAL_LABEL = "model episode: real backend; evidence about the named model only"
CAPS = {"model": "claude-haiku-5-5", "input_tokens": 2000, "output_tokens": 300, "temperature": 1.0,
        "calls": 8, "episode_tokens": 18_400, "wall_seconds": 600, "budget": None, "id_tag": "",
        "max_reply_bytes": 600, "thinking": bc.THINKING_OFF, "task_order": "shared"}
# "shared": every agent sees the taskset order (default, unchanged). "per_agent": prereg change 14, not confirmed by the
# owner (herding may be the effect card A acts on), so it is opt-in only.
TASK_ORDERS = ("shared", "per_agent")
THINKING_BLOCKS = ("thinking", "redacted_thinking")  # any of these in a response voids the episode (pilot 2 stop)
USAGE_IN = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
ROUND_ORDER = (("claim",), ("claim", "work", "release"))  # prereg section 6; `pass` stands alone
ALLOWED_TEXT = ("This round send one action: claim one task, or pass.",
                "This round send, in this order and each optional: one claim, one work (task, integer answer, a name), "
                "one release; or pass alone.")
# pilot4 round 2 only: replaces turn.md's last line (turn.md's hash stays pinned); wording from lab/pilot3_prompt_replay.py array_only
TURN_BASELINE_LAST = "Reply with one JSON array."
PILOT4_ROUND2_WORDING = "Return exactly one JSON action array, starting with [ and ending with ]. Do not include any other text."
PILOT4_ROUND2_WORDING_SHA256 = hashlib.sha256(PILOT4_ROUND2_WORDING.encode()).hexdigest()
SPEC = {"claim": {"item": str}, "pass": {}, "release": {"item": str, "done": bool},
        "work": {"task": str, "answer": int, "name": str}}
OPTIONAL = {("release", "done")}
ID_FIELDS = ("item", "task")
ID_RE = re.compile(r"[A-Za-z0-9_-]{1,32}", re.ASCII)
MAX_STR, MAX_INT, MAX_REASON = 32, 10 ** 6, 40
STOP_MALFORMED = {"max_tokens": "truncated", "refusal": "declined"}  # any other non-end_turn: bad_stop_reason
RERUNNABLE = ("infrastructure_abort",)  # re-run from its first call with the same seeds and a NEW caps id_tag


class PromptTooLarge(ValueError):
    """The request would exceed the per-call input cap: a harness fault, never sent; the episode is aborted."""


def _templates():
    out = {}
    for n in TEMPLATES:
        with open(os.path.join(PROMPT_DIR, n), "rb") as f:
            out[n] = f.read()
    return out


def template_hashes(tpl=None):
    return {n: hashlib.sha256(b).hexdigest() for n, b in (tpl or _templates()).items()}


def _bad(c):
    raise ValueError("non-finite number")


def _pairs(pairs):
    d = dict(pairs)
    if len(d) != len(pairs):
        raise ValueError("duplicate key")
    return d


_DEC = json.JSONDecoder(parse_constant=_bad, object_pairs_hook=_pairs)


def _action(obj, ids):
    """One action object -> (action|None, reason). Task ids must be exactly one of `ids` (ASCII)."""
    if type(obj) is not dict:
        return None, "not_object"
    if any(type(key) is not str for key in obj):
        return None, "bad_key"
    kind = obj.get("type")
    if type(kind) is not str or kind not in SPEC:
        return None, "bad_type"
    if "agent" in obj:  # the harness is the only source of identity
        return None, "agent_field"
    spec = SPEC[kind]
    extra = sorted(set(obj) - set(spec) - {"type"})
    if extra:
        return None, f"extra_key:{extra[0][:MAX_STR]}"
    for k, t in spec.items():
        if k not in obj:
            if (kind, k) in OPTIONAL:
                continue
            return None, f"missing:{k}"
        v = obj[k]
        if isinstance(v, (dict, list)):
            return None, "nested_value"
        if type(v) is not t or (t is str and not 0 < len(v) <= MAX_STR) or (t is int and abs(v) > MAX_INT):
            return None, f"bad_field:{k}"
        if k in ID_FIELDS and not (ID_RE.fullmatch(v) and v in ids):
            return None, "unknown_task"
    return dict(obj), None


def _last_array(s):
    """The last top-level JSON list in `s` if only whitespace follows it, else None (prereg change 19)."""
    found, i = None, 0
    while i < len(s):
        if s[i] == "[":
            try:
                obj, n = _DEC.raw_decode(s, i)
            except (ValueError, RecursionError):
                obj, n = None, i + 1
            if type(obj) is list:
                found, i = (obj, n), n
                continue
        i += 1
    if found is None or s[found[1]:].strip():
        return None
    return found[0]


def parse(text, rnd, ids, max_bytes=CAPS["max_reply_bytes"]):
    """Strict first: the whole reply is one JSON value (a bare object is a list of one). Prereg change 19: if that
    fails, accept the LAST top-level JSON array when only whitespace follows it; prose before it is ignored.
    -> (list of actions | None, reason). `ids`: the task ids shown to this agent."""
    if not isinstance(text, str) or not text.strip():
        return None, "empty"
    if len(text.encode()) > max_bytes:
        return None, "oversize"
    s = text.strip()
    obj, why = None, None
    try:
        obj, end = _DEC.raw_decode(s)
        rest = s[end:].strip()
        if rest:
            try:
                _DEC.raw_decode(rest)
                why = "multiple_values"
            except (ValueError, RecursionError):
                why = "extra_text"
    except (ValueError, RecursionError):
        why = "not_json"
    if why:
        last = _last_array(s)  # shortcut: prose length before the array is not logged yet; add extra_text_bytes if needed
        if last is None:
            return None, why
        obj = last
    return _validate_actions(obj if type(obj) is list else [obj], rnd, ids)


def _validate_actions(objs, rnd, ids):
    if type(objs) is not list:
        return None, "not_list"
    if not objs:
        return None, "empty_list"
    acts = []
    for o in objs:
        a, why = _action(o, ids)
        if a is None:
            return None, why
        acts.append(a)
    kinds = [a["type"] for a in acts]
    if "pass" in kinds:
        return (acts, None) if len(acts) == 1 else (None, "pass_not_alone")
    order = ROUND_ORDER[min(rnd, 1)]
    if any(k not in order for k in kinds):
        return None, "type_not_allowed_in_round"
    if len(set(kinds)) != len(kinds):
        return None, "duplicate_type"
    if kinds != sorted(kinds, key=order.index):
        return None, "out_of_order"
    return acts, None


def _is_real(client):
    """Only a constructed, unmodified ClaudeClient (never a subclass, a duck type or a patched `call`) on the real host."""
    return (type(client) is bc.ClaudeClient and "call" not in vars(client) and isinstance(vars(client).get("_key"), str)
            and urllib.parse.urlsplit(client.base_url).hostname == bc.DEFAULT_HOST)


def model_matches(requested, returned):
    """The loop's own identity check (prereg section 12), whatever client answered: the returned id must map to the
    requested model's canonical family key (cell.model_key). A missing, non-string, unknown or ambiguous id fails."""
    try:
        return cell.model_key(returned) == cell.model_key(requested)
    except ValueError:
        return False


def _http_exception(e):
    return any(c.__module__ == "http.client" and c.__name__ == "HTTPException" for c in type(e).__mro__)


def _ledger(client):
    led = getattr(client, "ledger", None)
    return led if isinstance(led, spend.Ledger) else None


def _fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace(f"<<{k}>>", str(v))
    if "<<" in tpl.replace("<<card>>", ""):
        raise ValueError("unfilled template token")
    return tpl


class _NoAdopter:
    q = None

    def follows(self, card, agent, decision="episode"):
        return False  # `follow` is a scripted-adopter notion; it is not in the model path


class _ModelEpisode(team._Episode):
    def __init__(self, ts, arm, card, agents, seed, tmp, client, caps, batch, tpl, eid, before_request=None):
        super().__init__(ts, arm, card, agents, seed, caps["budget"], _NoAdopter(), None, None, [], tmp)
        self.client, self.caps, self.batch, self.eid, self.seed = client, caps, batch, eid, seed
        self.before_request = before_request
        self.ids = frozenset(t["id"] for t in ts["tasks"])
        self.system, self.turn_tpl = tpl["system.md"].decode().rstrip("\n"), tpl["turn.md"].decode().rstrip("\n")
        self.cep = bc.Episode(eid, caps["episode_tokens"], caps["wall_seconds"])
        self.turns, self.calls, self.void, self.abort = [], 0, None, None
        self.malformed, self.model_refusals, self.last, self.deferred = {}, 0, {}, []
        self.tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
        self.usd = 0.0

    def prompt(self, agent, rnd, view):
        head, tail = self.turn_tpl.split("<<card>>")
        order = self.ts["tasks"]
        if self.caps["task_order"] == "per_agent":  # no arm in the seed: identical across arms of a task set
            order = random.Random(f"ep1:view:{self.ts['split']}:{self.ts['seed']}:{agent}").sample(order, len(order))
        tasks = "\n".join(f"{t['id']}: {t['check']}" for t in order)  # never `expect`
        claims = json.dumps(view["claims"], sort_keys=True, separators=(",", ":"))
        user = _fill(head, round=rnd + 1, rounds=2, agent=agent, left=2 - rnd, allowed=ALLOWED_TEXT[min(rnd, 1)],
                     tasks=tasks)
        tail = _fill(tail.lstrip("\n"), claims=claims, status=self.last.get(agent, "none yet"))
        if self.batch == "pilot4" and rnd == 1:
            if not tail.endswith(TURN_BASELINE_LAST):
                raise ValueError("turn template last line is not the expected instruction")
            tail = tail[:-len(TURN_BASELINE_LAST)] + PILOT4_ROUND2_WORDING
        user = practicemod.attach(user, self.cards[agent])[0] + tail
        return self.system, user

    def calling(self, rnd):
        """Call order of a round. The outcome does not depend on it: replies execute in `seeded` order."""
        return list(self.agents)

    def seeded(self, rnd, replies):
        """Execution order of a round's replies. For every task claimed this round, the claimant that the board's own
        seeded draw picks (Board.end_round: Random(f"{seed}:{round}:{item}").choice(sorted claimants)) goes first, so
        under a claim lock the agents refused are the ones the unenforced board resolves against. Others: agent order.
        Each agent sends at most one claim per round, so one order serves every task."""
        by = {}
        for a, (acts, _t, _held) in replies.items():
            for x in acts:
                if x["type"] == "claim":
                    by.setdefault(x["item"], set()).add(a)
        first = {random.Random(f"{self.seed}:{rnd}:{i}").choice(sorted(c)) for i, c in by.items()}
        return sorted(replies, key=lambda a: (a not in first, self.agents.index(a)))

    def run(self):
        ended = "complete"
        try:
            for rnd in (0, 1):
                self.rnd, replies = rnd, {}
                for a in self.calling(rnd):
                    if a in self.stopped:
                        continue
                    try:
                        r = self.ask(a, rnd)
                    except team._AgentStop:
                        self._out(a)
                        continue
                    if r is not None:
                        replies[a] = r
                for a in self.seeded(rnd, replies):
                    self.execute(a, *replies[a])
                router.end_round(self.handle)
                deferred, self.deferred = self.deferred, []
                for a, x, t, i in deferred:  # releases of same-reply claims, now resolved; still in seeded order
                    if a not in self.stopped:
                        ok, why = self.send(a, x)
                        self._result(t, i, ("accepted" if ok else f"refused: {str(why)[:MAX_REASON]}") + " (after round end)")
        except team._Stop as e:
            ended = str(e)
        return ended

    def _out(self, agent):
        self.stopped.add(agent)
        if len(self.stopped) == len(self.agents):
            raise team._Stop("episode_stopped")

    def _result(self, t, i, s):
        t["results"][i] = s
        t["status"] = "refused" if any(r.startswith("refused") for r in t["results"]) else "accepted"
        self.last[t["agent"]] = "; ".join(t["results"])

    def send(self, agent, x):
        """One action through submit/router.act; then the router's stop state is read, since act reports a stop only
        on the next action. -> (executed, refusal reason)."""
        n = len(self.reasons)
        try:
            ok = self.submit(agent, dict(x, agent=agent))
        except team._AgentStop:  # the router answered agent_stopped: not a new refusal
            ok = False
        if self.enforced and self.violations:
            self.void = "enforcement_violation"
            raise team._Stop("void")
        why = self.reasons[-1][1] if not ok and len(self.reasons) > n else ("agent_stopped" if not ok else None)
        ep_stop, out = router.stops(self.handle)
        self.stopped.update(a for a in out if a in self.agents)
        if ep_stop or len(self.stopped) == len(self.agents):
            raise team._Stop("episode_stopped")
        return ok, why

    def execute(self, agent, acts, t, held):
        """Send one reply's actions in order. A refused action is lost; the rest are still sent (D3: each counts)."""
        t["results"] = ["not sent"] * len(acts)
        claimed = None
        for i, x in enumerate(acts):
            if agent in self.stopped:
                break
            if x["type"] == "release" and x["item"] == claimed and held.get(claimed) != agent:
                self.deferred.append((agent, x, t, i))  # held only once end_round resolves the claim
                self._result(t, i, "deferred")
                continue
            self._result(t, i, "sending")
            ok, why = self.send(agent, x)
            if ok and x["type"] == "claim":
                claimed = x["item"]
            self._result(t, i, "accepted" if ok else f"refused: {str(why)[:MAX_REASON]}")

    def ask(self, agent, rnd):
        """Read, prompt, one call, strict parse. -> (actions, turn record, claims seen) or None for a lost turn."""
        self.charge("cards", len(self.cards[agent]["text"].encode()))
        view = self.read(agent)  # one routed read per call; the committed log only, so same-round claims are hidden
        if self.calls >= self.caps["calls"]:
            raise team._Stop("call_cap")
        system, user = self.prompt(agent, rnd, view)
        messages = [{"role": "user", "content": user}]
        body = json.dumps({"model": self.caps["model"], "max_tokens": self.caps["output_tokens"],
                           "temperature": self.caps["temperature"], "messages": messages, "system": system,
                           "thinking": self.caps["thinking"]},
                          sort_keys=True).encode()
        t = {"agent": agent, "round": rnd, "call_id": f"{self.eid}:r{rnd}:{agent}", "status": None,
             "reason": None, "request_bytes": len(body), "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest()}
        self.turns.append(t)
        if len(body) > self.caps["input_tokens"]:  # bytes >= tokens, so this refuses before the client would
            self.abort = str(PromptTooLarge(f"request {len(body)} bytes > cap {self.caps['input_tokens']}"))
            t["status"], t["reason"] = "prompt_too_large", self.abort
            raise team._Stop("prompt_too_large")
        self.calls += 1
        guard = {} if self.before_request is None else {"before_request": self.before_request}
        try:
            rec = self.client.call(self.cep, t["call_id"], self.caps["model"], messages, self.caps["output_tokens"],
                                   self.caps["temperature"], system=system, batch=self.batch, **guard)
        except bc.InputIntegrityError:
            self.void = "input_integrity"
            t["status"], t["reason"] = "void", self.void
            raise team._Stop("void") from None
        except bc.EpisodeVoided:
            t["status"] = "void"
            raise team._Stop("void") from None
        except bc.EpisodeCapExceeded:
            t["status"] = "episode_cap"
            raise team._Stop("episode_cap") from None
        except spend.SpendError as e:
            t["status"] = "spend_stop"
            raise team._Stop(f"spend_stop:{type(e).__name__}") from None
        except RuntimeError as e:  # ClaudeClient: no usable response after its one retry
            msg = str(e)[:200]
            if re.search(r"failed: HTTP 200\b", msg):  # a 200 naming no model: void, never a re-run (G1b-5)
                self.void = "HTTP 200 without a model field"
                t["status"], t["reason"] = "void", msg
                raise team._Stop("void") from None
            t["status"], t["reason"] = "infrastructure_abort", msg
            raise team._Stop("infrastructure_abort") from None
        except Exception as e:  # noqa: BLE001 - http.client.HTTPException (cut-short body, bad status line) escapes the client
            if not _http_exception(e):  # matched by class, since the egress scan forbids importing http.client here
                raise
            led = _ledger(self.client)
            if led is not None:  # its reserve stays open at the worst case in the ledger; count it here too
                self.cep.unbilled_usd += led.worst_case(self.caps["model"], len(body), self.caps["output_tokens"])
            t["status"], t["reason"] = "infrastructure_abort", type(e).__name__
            raise team._Stop("infrastructure_abort") from None
        u = rec.get("usage") or {}
        for k, f in (("input", "input_tokens"), ("output", "output_tokens"), ("cache_read", "cache_read_input_tokens"),
                     ("cache_creation", "cache_creation_input_tokens")):
            self.tokens[k] += u.get(f) or 0
        self.usd += rec.get("usd") or 0.0
        stop = rec.get("stop_reason")
        ret = rec.get("returned_model")
        t.update(returned_model=ret if ret is None or isinstance(ret, str) else repr(ret)[:80], usage=u,
                 usd=rec.get("usd"), stop_reason=stop, block_types=list(rec.get("block_types") or [])[:16])
        for key in ("provider_response_id", "provider_input_truncated"):
            if key in rec:
                t[key] = rec[key]
        t["retries"] = int(str(rec.get("id") or "").endswith("#r1"))  # the client's one retry has its own `#r1` id
        used = sum(u.get(k) or 0 for k in USAGE_IN)
        if not ret:
            self.void = "response names no model"
        elif not model_matches(self.caps["model"], ret):  # checked here on every call, not left to the client
            self.void = f"returned model {t['returned_model']!r} != requested {self.caps['model']!r}"
        elif any(b in THINKING_BLOCKS for b in t["block_types"]):
            self.void = "thinking block in response: the request asked for thinking off"
        elif rec.get("void") or used > self.caps["input_tokens"]:
            self.void = rec.get("void") or f"reported input usage {used} > cap {self.caps['input_tokens']}"
        if self.void:
            t["status"] = "void"
            raise team._Stop("void")
        self.model_refusals += stop == "refusal"
        text = rec.get("text")
        t["reply"] = str(text)[:1200]  # model text for hand review; never reaches another agent's prompt
        if stop != "end_turn":  # truncated or declined: never accepted as a reply
            acts, why = None, STOP_MALFORMED.get(stop, "bad_stop_reason")
        else:
            acts, why = parse(text, rnd, self.ids, self.caps["max_reply_bytes"])
        if acts is None:  # costs the turn; recorded, not repaired
            t["status"], t["reason"] = "malformed", why
            self.malformed[why.split(":")[0]] = self.malformed.get(why.split(":")[0], 0) + 1
            self.last[agent] = "no-op"
            self.charge("refused", len(str(text).encode()))
            return None
        # Keep an invalid parser result out of the scheduler and router in every arm.
        acts, _ = _validate_actions(acts, rnd, self.ids)
        if acts is None:
            self.void = "action_boundary"
            t["status"], t["reason"] = "void", self.void
            raise team._Stop("void")
        t["actions"] = [x["type"] for x in acts]
        if t["actions"] == ["pass"]:
            t["status"], self.last[agent] = "pass", "no-op"
            return None
        return acts, t, view["claims"]


def _check_caps(caps):
    for k in ("input_tokens", "output_tokens", "calls", "episode_tokens", "wall_seconds", "max_reply_bytes"):
        if isinstance(caps[k], bool) or not isinstance(caps[k], int) or caps[k] <= 0:
            raise ValueError(f"caps.{k} must be a positive int")
    t = caps["temperature"]
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 <= t <= 1:
        raise ValueError("caps.temperature must be a number in [0, 1]")
    if caps["task_order"] not in TASK_ORDERS:
        raise ValueError(f"caps.task_order must be one of {TASK_ORDERS}")
    if caps["thinking"] != bc.THINKING_OFF:  # the client always sends THINKING_OFF; the size probe must match it
        raise ValueError("caps.thinking must be {'type': 'disabled'}")
    if not isinstance(caps["model"], str) or not caps["model"]:
        raise ValueError("caps.model must be a string")
    if not isinstance(caps["id_tag"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{0,16}", caps["id_tag"]):
        raise ValueError("caps.id_tag must be up to 16 ASCII letters, digits, '-' or '_'")


def run_episode_model(taskset, arm, practice, client, seed=0, batch=None, n_agents=4, rounds=2, caps=None, *,
                      before_request=None):
    """One model episode of practice A on `taskset`; returns the record (see module doc). Every outcome returns a
    record: `ended` is complete, void, infrastructure_abort (`rerunnable`: same seeds, NEW caps id_tag),
    prompt_too_large (`abort_reason`), episode_cap, call_cap, budget_exhausted, episode_stopped or spend_stop:*."""
    if arm not in team.ARMS:
        raise ValueError(f"arm must be one of {team.ARMS}, got {arm!r}")
    card = practicemod.load(practice) if isinstance(practice, str) else practice
    if not isinstance(card, dict) or card.get("id") != "A":
        raise ValueError("the EP-1 model loop covers practice A only")
    if rounds != 2:
        raise ValueError("EP-1 runs 2 rounds")
    if n_agents != taskset.get("n_agents") or not 1 <= n_agents <= len(taskset["tasks"]):
        raise ValueError("n_agents does not match the taskset")
    caps = {**CAPS, **(caps or {})}
    unknown = set(caps) - set(CAPS)
    if unknown:
        raise ValueError(f"unknown caps {sorted(unknown)}")
    _check_caps(caps)
    agents = [f"a{i}" for i in range(n_agents)]
    real = _is_real(client)
    tpl = _templates()
    eid = f"ep1{caps['id_tag']}-{arm}-{taskset['split'][0]}{taskset['seed']}-s{seed}"
    led = _ledger(client)
    used = set().union(*(led._sum(led._read(f))["reserved_ids"] for f in led._files())) if led is not None else ()
    if any(i.startswith(eid + ":") for i in used):  # every ledger file of the directory, not only this one
        raise ValueError(f"episode id {eid!r} already used in this ledger directory: a re-run needs a new caps id_tag")
    with tempfile.TemporaryDirectory() as tmp:
        ep = _ModelEpisode(taskset, arm, card, agents, seed, tmp, client, caps, batch, tpl, eid, before_request)
        ended = ep.run()
        if ep.void == "action_boundary":
            outcome, y, scores = "distinct_passing/slots", None, {"valid": False}
            lines = board.read_log(ep.blog)
        else:
            outcome, y, scores, lines = team._score(ep)
    mal = sum(ep.malformed.values())
    expect = {t["id"]: t["expect"] for t in taskset["tasks"]}
    returned = sorted({t["returned_model"] for t in ep.turns if t.get("returned_model")})
    return {"instrument_validation": not real, "evidence": "model" if real else "fake",
            "label": REAL_LABEL if real else FAKE_STAMP, "seed": seed, "arm": arm, "practice": "A",
            "n_agents": n_agents, "rounds": rounds, "model": returned[0] if len(returned) == 1 else None,
            "requested_model": caps["model"], "temperature": caps["temperature"], "task_order": caps["task_order"],
            "caps": {k: caps[k] for k in ("input_tokens", "output_tokens", "calls", "episode_tokens")},
            "episode_id": eid, "id_tag": caps["id_tag"], "batch": batch,
            "outcome": outcome, "Y": y, "scores": scores, "log": ep.log, "ended": ended,
            "valid": scores.get("valid", True), "extra_work_events": scores.get("extra_work_events", 0),
            "status": "ok" if scores.get("valid", True) else "void:invalid_log",
            "void": ep.void or (None if scores.get("valid", True) else "invalid_log"),
            "rerunnable": ended in RERUNNABLE, "abort_reason": ep.abort,
            "calls": ep.calls, "turns": ep.turns, "returned_models": returned,
            "tokens": dict(ep.tokens), "usd": ep.usd, "usd_unbilled": getattr(ep.cep, "unbilled_usd", 0.0),
            "malformed": mal, "malformed_by_reason": dict(ep.malformed), "model_refusals": ep.model_refusals,
            "refused": len(ep.reasons), "refusals": list(ep.reasons), "stopped_agents": sorted(ep.stopped),
            "violations_executed": ep.violations, "card_sha256": ep.card_sha, "template_sha256": template_hashes(tpl),
            **({"round2_wording_sha256": PILOT4_ROUND2_WORDING_SHA256} if batch == "pilot4" else {}),
            "taskset_sha256": hashlib.sha256(alloc.dumps(taskset).encode()).hexdigest(),
            "taskset_id": f"{taskset['split']}:{taskset['seed']}",
            "agent_answers": [{"agent": e["agent"], "task": e["task"], "answer": e["answer"],
                               "pass": not e["rejected"] and e["answer"] == expect.get(e["task"])}
                              for e in ep.log if e["action"] == "work"],
            "spent": {**ep.spent, "total": sum(ep.spent.values())}, "trace": ep.trace,
            "orders": {k: v["value"] for k, v in orders.compute(lines, trace=ep.trace).items()},
            "board_head": lines[-1]["hash"] if lines else None, "board_events": len(lines)}
