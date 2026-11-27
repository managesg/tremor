"""Practice cards: load, neutral twin, attach to a prompt, leak check. stdlib only.

A card is practices/<ID>.md: `key: value` header lines, a `---` line, then the card text.
"""
import hashlib
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "practices")
FIELDS = ("id", "version", "enforcer", "measures")
MAX_CARD = 600
# shortcut: substring match, so a neutral word can never contain one of these; widen with the cards.
KEYWORDS = ("claim", "own", "verif", "check", "name", "uniq", "write", "writer", "read", "source",
            "supersede", "expir", "consolidat", "dream", "board", "task", "release", "agent", "note",
            "done", "intent", "page", "memory", "stale", "hold", "report", "lead", "instruction", "copy")
_VOCAB = ("quiet river stone lamp garden window morning cloud harbor field silver bridge candle "
          "meadow winter forest sparrow lantern valley orchard breeze").split()


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def load(card_id, root=None):
    if not re.fullmatch(r"[A-GHLS]", str(card_id)):
        raise ValueError(f"bad card id {card_id!r}")
    with open(os.path.join(root or ROOT, f"{card_id}.md"), "rb") as f:
        raw = f.read()
    head, sep, text = raw.decode("utf-8").partition("\n---\n")
    if not sep:
        raise ValueError(f"card {card_id}: no --- separator")
    card = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    missing = [k for k in FIELDS if not card.get(k)]
    if missing or not text.strip():
        raise ValueError(f"card {card_id}: missing {missing or ['text']}")
    if card["id"] != card_id:
        raise ValueError(f"card {card_id}: id field says {card['id']}")
    if len(raw) > MAX_CARD:
        raise ValueError(f"card {card_id}: {len(raw)} bytes > {MAX_CARD}")
    return {**{k: card[k] for k in FIELDS}, "text": text.rstrip("\n"), "sha256": _sha(raw)}


def neutral(card):
    """Same text byte length as `card`, no practice keyword, enforcer none."""
    n = len(card["text"].encode("utf-8"))
    off = sum(card["text"].encode("utf-8")) % len(_VOCAB)  # shortcut: deterministic filler, not prose
    words = [_VOCAB[(off + i) % len(_VOCAB)] for i in range(n // 4 + 1)]
    text = " ".join(words)[:n].rstrip()
    text += "." * (n - len(text))  # rstrip may drop a trailing space; pad back to exact length
    low = text.lower()
    assert not any(k in low for k in KEYWORDS) and len(text) == n
    return {"id": "N" + card["id"], "version": card["version"], "enforcer": "none",
            "measures": card["measures"], "text": text,
            "sha256": _sha(f"neutral:{card['id']}:{card['version']}\n{text}".encode("utf-8"))}


def attach(prompt, card):
    return prompt.rstrip("\n") + "\n\n" + card["text"] + "\n", card["sha256"]


def leak_check(card, texts):
    """Return the task answers (texts) that appear in the card text, case-insensitive."""
    low = card["text"].lower()
    return [t for t in texts if t and str(t).lower() in low]


def lead_cards(lead_card, agents, lead):
    """Card per agent for practice L: `lead` gets the real card, the others its neutral twin."""
    if lead not in agents:
        raise ValueError(f"lead {lead!r} not in agents")
    return {a: lead_card if a == lead else neutral(lead_card) for a in agents}
