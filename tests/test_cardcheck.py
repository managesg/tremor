import ast
import hashlib
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from tremor import cardcheck  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


A = read("practices", "A.md")
STATES = read("practices", "pilot", "states_the_check.md")
STUFFED = read("practices", "pilot", "keyword_stuffed.md")


def reviewed(card):
    sha = hashlib.sha256(card.encode()).hexdigest()
    d = tempfile.mkdtemp()
    path = os.path.join(d, "review.txt")
    with open(path, "w") as f:
        f.write(f"reviewed {sha} by other agent\n")
    return path, sha


class CardCheck(unittest.TestCase):
    def test_card_a_needs_recorded_review(self):
        r = cardcheck.check_card(A)
        self.assertFalse(r["ok"])
        self.assertEqual(r["hits"], [])
        self.assertTrue(r["paraphrase_review_required"])
        path, sha = reviewed(A)
        self.assertTrue(cardcheck.check_card(A, reviewer=path, reviewed_sha256=sha)["ok"])
        self.assertFalse(cardcheck.check_card(A, reviewer=path, reviewed_sha256="0" * 64)["ok"])
        self.assertFalse(cardcheck.check_card(A + " x", reviewer=path, reviewed_sha256=sha)["ok"])

    def test_pilot_cards_fail_the_word_list(self):
        for card in (STATES, STUFFED):
            r = cardcheck.check_card(card, kind="pilot")
            self.assertFalse(r["ok"])
            self.assertGreaterEqual(len(r["hits"]), 3)
        self.assertIn("PILOT-ONLY", STATES.split("\n---\n")[0])
        self.assertIn("PILOT-ONLY", STUFFED.split("\n---\n")[0])

    def test_paraphrase_passes_list_but_is_flagged(self):
        text = "id: X\n---\nTake a job nobody else has taken. Never repeat what a teammate is doing."
        r = cardcheck.check_card(text)
        self.assertEqual(r["hits"], [])
        self.assertTrue(r["paraphrase_review_required"])
        self.assertFalse(r["ok"])
        path, sha = reviewed(text)
        self.assertTrue(cardcheck.check_card(text, reviewer=path, reviewed_sha256=sha)["ok"])

    def test_variants_and_phrases(self):
        for t in ("Duplicates are bad.", "be uniquely placed", "the Last   Writer wins", "NAME-RULE applies"):
            self.assertTrue(cardcheck.check_card("---\n" + t, kind="pilot")["hits"], t)

    def test_vocabulary_drift(self):
        src = read("src", "tremor", "trapbench", "alloc.py")
        tree = ast.parse(src)
        skip = {id(tree.body[0].value)}  # module docstring
        for n in ast.walk(tree):
            if isinstance(n, ast.JoinedStr):
                skip.update(id(c) for c in ast.walk(n))
        found = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and id(n) not in skip and n.value.replace("_", "").isalnum() and n.value.islower()}
        v = cardcheck.scorer_vocabulary()
        known = set(v["banned"]) | set(v["context"])
        known |= {w for e in v["banned"] for w in e.split()}
        # "sum" appears only inside an f-string check template; "heldout" is listed.
        self.assertEqual(sorted(found - known), [], "alloc.py has string keys missing from cardcheck vocabulary")
        self.assertIn("work", found)

    def test_prereg_ban_list_is_subset_and_scorer_fields_banned(self):
        banned = set(cardcheck.BANNED)
        self.assertLessEqual({"score", "scored", "pass", "correct", "slot", "point", "grade"}, banned)
        self.assertLessEqual({"extra_work_events", "valid"}, banned)  # alloc.py scorer fields
        self.assertEqual(cardcheck.check_card(A, kind="pilot")["hits"], [])

    def test_byte_match(self):
        r = cardcheck.match_report({"A": A, "states": STATES, "stuffed": STUFFED})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["bytes"]["A"], len(A.encode()))
        self.assertEqual(r["token_upper_bound"], r["bytes"])
        bad = cardcheck.match_report({"A": A, "long": A + "x" * 50})
        self.assertFalse(bad["ok"])

    def test_deterministic(self):
        self.assertEqual(cardcheck.check_card(STATES, kind="pilot"), cardcheck.check_card(STATES, kind="pilot"))


if __name__ == "__main__":
    unittest.main()
