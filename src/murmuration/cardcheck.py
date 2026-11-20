"""Card ban check and byte-match report for EP-1 (stdlib only).

LIMIT: a word list cannot rule on paraphrase. Card A's "pick a different task" paraphrases the scorer's
distinctness and passes any word list. So for play cards `ok` also needs a recorded review by someone other
than the author, and `paraphrase_review_required` is always true.
"""
import hashlib
import os
import re

# Predicate words and phrases the scorer applies (trapbench/alloc.py). Matching is on tokens: a card token
# hits a word when it equals it or starts with it ("duplicates", "uniquely"); phrases match token runs.
BANNED = [
    "distinct", "distinct passing", "passing", "surviving", "surviving passing", "survive", "duplicate",
    "duplicates", "collision", "name collisions", "clobber", "unique", "expect", "answer", "rejected",
    "distinct_passing", "surviving_passing", "name_collisions", "slots", "name rule", "same name", "last writer", "last accepted", "accepted work", "heldout", "check",
    "score", "scored", "pass", "correct", "slot", "point", "grade",  # named by prereg/EP1.md; its "Y" is not listed: as a prefix it hits "you" in card A
    "extra_work_events", "valid",  # scorer field names (alloc.py)
    "unknown_task_events",  # added with the alloc.py no-op fix; scorer field names are banned like the others
]
# Field names that are also everyday words (every card says "task" or "agent"). Listed so drift is caught,
# but not banned: banning them would ban card A.
CONTEXT = [
    "agent", "action", "claim", "work", "task", "tasks", "name", "id", "split", "seed", "n_agents",
    "name_rule", "train",
]
TOLERANCE_BYTES = 20


def scorer_vocabulary():
    return {"banned": list(BANNED), "context": list(CONTEXT)}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def body(card_text):
    """The card text after the `---` header, as practice.load splits it; whole text if no header."""
    head, sep, text = card_text.partition("\n---\n")
    return text if sep else card_text


def _hits(tokens, vocab):
    found = []
    for entry in vocab["banned"]:
        parts = _tokens(entry)
        n = len(parts)
        if any(all(tokens[i + j].startswith(p) for j, p in enumerate(parts)) for i in range(len(tokens) - n + 1)):
            found.append(entry)
    return found


def check_card(card_text, vocab=None, kind="play", reviewer=None, reviewed_sha256=None):
    """-> {ok, hits, reasons, paraphrase_review_required, sha256}. The ban is checked on the body only.

    kind="play": ok also needs `reviewer` (path of a recorded review file by someone other than the author)
    whose text contains `reviewed_sha256`, which must equal the sha256 of the card bytes.
    """
    vocab = vocab or scorer_vocabulary()
    sha = hashlib.sha256(card_text.encode("utf-8")).hexdigest()
    hits = _hits(_tokens(body(card_text)), vocab)
    reasons = [f"banned scorer word: {h}" for h in hits]
    if kind == "play":
        if not reviewer or not reviewed_sha256:
            reasons.append("paraphrase review not recorded (reviewer path and reviewed_sha256 required)")
        elif reviewed_sha256 != sha:
            reasons.append("reviewed_sha256 does not match this card")
        elif not os.path.isfile(reviewer) or sha not in open(reviewer, encoding="utf-8").read():
            reasons.append("review file missing or does not record this card's sha256")
    return {"ok": not reasons, "hits": hits, "reasons": reasons,
            "paraphrase_review_required": kind == "play", "sha256": sha}


def match_report(cards, tolerance=TOLERANCE_BYTES):
    """cards: {name: text}. Bytes are a conservative token upper bound (tokens <= UTF-8 bytes, G0-2R)."""
    lengths = {k: len(v.encode("utf-8")) for k, v in cards.items()}
    spread = max(lengths.values()) - min(lengths.values()) if lengths else 0
    return {"bytes": lengths, "token_upper_bound": dict(lengths), "spread": spread, "tolerance": tolerance,
            "ok": spread <= tolerance,
            "note": "bytes do not equal tokens; real tokens are measured in the pilot"}
