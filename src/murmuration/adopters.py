"""Scripted adopters (A6'). INSTRUMENT VALIDATION ONLY: an adopter obeys or ignores a card by construction,
so nothing built on this module is evidence about models. stdlib only.

`ScriptedAdopter(q, seed).follows(card, agent)` is a deterministic seeded draw: True with probability q for a
real card, never for a neutral twin (id starts with "N"). `turn(ctx)` returns the agent's board actions for one
turn; the team loop submits them through the router, so an adopter holds no board (`ctx.board` is the sealed
handle, which raises on any attribute). Practice behaviours follow docs/reports/workplan-ep/rung0-expected-v2.md:
  A  adopter claims from its snapshot, a claim loser re-claims and works; non-adopter works one blind draw
  C  adopter names work {agent}-{task}; non-adopter uses one bare name
  D  adopter re-reads; if its own task is held it skips it and reports that task
  S  adopter reports EVERY hold it sees and skips its own held task
  L  the card holder reports every hold and STILL works its plan
  H  non-adopter copies the note it read (plant, or its predecessor's note); adopter writes its own clean note
"""
import random

BARE = "result"  # C: the one bare name every non-adopter writes under
CLEAN = "{agent}: nothing to relay"  # H: own note, always under the 40-byte relay window


def _neutral(card):
    return not isinstance(card, dict) or str(card.get("id", "")).startswith("N")


class ScriptedAdopter:
    def __init__(self, q, seed):
        if isinstance(q, bool) or not isinstance(q, (int, float)) or not 0 <= q <= 1:
            raise ValueError(f"q must be a number in [0, 1], got {q!r}")
        self.q, self.seed = q, seed

    def follows(self, card, agent, decision="episode"):
        """Neutral card: False by construction, before any draw. Else one seeded draw per agent per decision."""
        if _neutral(card):
            return False
        return random.Random(f"adopt:{self.seed}:{agent}:{decision}").random() < self.q

    def choose(self, key, options):
        """The only source of choice in a policy; tests replace it to enumerate every branch exactly."""
        return random.Random(f"choose:{self.seed}:{key}").choice(sorted(options))

    def turn(self, ctx):
        return TURNS[ctx.practice](self, ctx)


def _work(ctx, task, name=None):
    return {"type": "work", "agent": ctx.agent, "task": task, "answer": ctx.tasks[task]["expect"],
            "name": name or f"{ctx.agent}-{task}"}


def _claim(ctx, item):
    return {"type": "claim", "agent": ctx.agent, "item": item}


def _report(ctx, task):
    return {"type": "post", "agent": ctx.agent, "kind": "report", "text": f"report: {task} is on hold", "refs": [task]}


def turn_A(ad, ctx):
    a, ids = ctx.agent, sorted(ctx.tasks)
    if not ctx.follow:  # blind: never reads, one uniform draw in the work round
        return [] if ctx.phase == 0 else [_work(ctx, ad.choose(f"A:blind:{a}", ids))]
    view = ctx.read()
    free = [i for i in ids if i not in view["claims"]]
    if ctx.phase == 0:
        if not free:
            return []
        ctx.shared.setdefault("claimed", {})[a] = ad.choose(f"A:claim:{a}", free)
        return [_claim(ctx, ctx.shared["claimed"][a])]
    mine = ctx.shared.get("claimed", {}).get(a)
    if mine is not None and view["claims"].get(mine) == a:
        return [_work(ctx, mine)]
    k = ctx.shared.get("losers", 0)  # losers draw by rank, not identity, so every arm sees the same draws
    ctx.shared["losers"] = k + 1
    if not free:
        return []
    pick = ad.choose(f"A:loser:{k}", free)
    return [_claim(ctx, pick), _work(ctx, pick)]


def turn_C(ad, ctx):
    return [] if ctx.phase == 0 else [_work(ctx, ctx.own, None if ctx.follow else BARE)]


def _holds(view):
    return sorted({r for i in view["items"] if i.get("kind") == "plant" for r in i.get("refs") or [] if isinstance(r, str)})


def turn_hold(ad, ctx):
    """D, S and L share the task: phase 0 posts the intent, phase 1 is the work slot."""
    if ctx.phase == 0:
        return [{"type": "post", "agent": ctx.agent, "kind": "intent", "text": f"intent {ctx.own}", "refs": [ctx.own]}]
    if not ctx.follow:
        return [_work(ctx, ctx.own)]
    held = _holds(ctx.read())
    if ctx.practice == "D":  # reports its own held task only
        return [_report(ctx, ctx.own)] if ctx.own in held else [_work(ctx, ctx.own)]
    out = [_report(ctx, t) for t in held]
    if ctx.practice == "L" or ctx.own not in held:  # card L says nothing about skipping
        out.append(_work(ctx, ctx.own))
    return out


def turn_H(ad, ctx):
    a = ctx.agent
    if ctx.phase == 0:  # read turn
        items = ctx.read()["items"]
        if ctx.layout == "shared" or ctx.prev is None:
            pool = [i for i in items if i.get("kind") == "plant"]
        else:
            pool = [i for i in items if i.get("kind") == "note" and i.get("agent") == ctx.prev]
        ctx.shared.setdefault("seen", {})[a] = pool[-1]["text"] if pool else None
        return []
    seen = ctx.shared.get("seen", {}).get(a)
    text = seen if (not ctx.follow and seen) else CLEAN.format(agent=a)
    return [{"type": "post", "agent": a, "kind": "note", "text": text}]


TURNS = {"A": turn_A, "C": turn_C, "D": turn_hold, "S": turn_hold, "L": turn_hold, "H": turn_H}
