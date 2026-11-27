"""Night loop (PROPOSAL-RESIDENCY-V3 section 3, item 6): day episodes append notes, a night pass writes a
NEW store and keeps the old one. Stdlib only, deterministic under `seed`.

Note: {"id","text","author","episode","sources":[evidence ids],"parents":[note ids], optional "false"}.
`false` is ground truth for scripted benches only; the verifier callback is the only thing a pass may use.
A store is a list of notes and is never mutated: every function returns a new list.
shortcut: tokens are whitespace words; upgrade if a real tokenizer budget is needed.
"""
from copy import deepcopy
import random


def add_note(store, id, text, author, episode, sources=(), **extra):
    """Day-episode write. Returns a new store with the note appended (provenance required)."""
    if any(n["id"] == id for n in store):
        raise ValueError(f"duplicate note id {id!r}")
    note = {"id": id, "text": text, "author": author, "episode": episode,
            "sources": list(sources), "parents": [], **extra}
    return deepcopy([*store, note])


def tokens(store):
    return sum(len(n["text"].split()) for n in store)


def consolidate(store, s, night, verifier=None, mode="direct", rewrite=None, seed=0):
    """One night pass. Each note is chosen with probability s (s=0: store unchanged, s=1: all).
    A chosen note is rewritten by `rewrite(note, rng) -> note-fields dict` (default: identity) into a new
    note `n<night>-<id>` whose "parents" link to the source note.
    mode "direct": rewrite replaces the original. With a verifier, a chosen original that fails it is dropped
                   and a rewrite that fails it is blocked (original kept).
    mode "gated":  rewrite replaces the original only if verifier(rewrite) passes, else the original stays;
                   originals are never dropped.
    Returns {"store": new list, "tokens_read": int, "written": [ids], "blocked": [ids], "dropped": [ids]}."""
    if not 0 <= s <= 1:
        raise ValueError("s must be in [0,1]")
    if mode not in ("direct", "gated"):
        raise ValueError(f"unknown mode {mode!r}")
    if mode == "gated" and verifier is None:
        raise ValueError("gated mode needs a verifier")
    tokens_read = tokens(store)
    rng = random.Random(seed)
    out, written, blocked, dropped = [], [], [], []
    for source in store:
        n = deepcopy(source)
        if rng.random() >= s:
            out.append(n)
            continue
        fields = deepcopy(rewrite(deepcopy(n), rng)) if rewrite else {}
        new = {**n, **fields, "id": f"n{night}-{n['id']}", "parents": [n["id"]]}
        if mode == "gated":
            ok = verifier(deepcopy(new))
            out.append(new if ok else n)
            (written if ok else blocked).append(n["id"])
        elif verifier is not None and not verifier(deepcopy(n)):
            dropped.append(n["id"])
        elif verifier is not None and not verifier(deepcopy(new)):
            out.append(n)
            blocked.append(n["id"])
        else:
            out.append(new)
            written.append(n["id"])
    return {"store": out, "tokens_read": tokens_read, "written": written, "blocked": blocked,
            "dropped": dropped}


def placebo(store, night=0):
    """Placebo dream: reads the same tokens as a real pass, changes no content."""
    return {"store": deepcopy(list(store)), "tokens_read": tokens(store), "written": [], "blocked": [],
            "dropped": []}


def false_share(store):
    return sum(bool(n.get("false")) for n in store) / len(store) if store else 0.0


def lineage(store, note_id):
    """All ancestors of a note through "parents" (provenance walk)."""
    by = {n["id"]: n for n in store}
    seen, todo = set(), list(by[note_id]["parents"])
    while todo:
        p = todo.pop()
        if p not in seen:
            seen.add(p)
            todo.extend(by[p]["parents"] if p in by else [])
    return seen
