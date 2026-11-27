import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tremor import practice  # noqa: E402

IDS = "ABCDEFGHLS"


class PracticeTest(unittest.TestCase):
    def test_sizes(self):
        cards = [practice.load(i) for i in IDS]
        sizes = [os.path.getsize(os.path.join(practice.ROOT, f"{i}.md")) for i in IDS]
        self.assertTrue(all(s <= 600 for s in sizes))
        self.assertLess(sum(sizes), 600 * len(IDS))
        self.assertEqual([c["id"] for c in cards], list(IDS))
        for c in cards:
            self.assertEqual(len(c["sha256"]), 64)

    def test_neutral_same_length_no_keyword(self):  # adversarial
        for i in IDS:
            c = practice.load(i)
            n = practice.neutral(c)
            self.assertEqual(len(n["text"].encode()), len(c["text"].encode()))
            self.assertFalse([k for k in practice.KEYWORDS if k in n["text"].lower()])
            self.assertEqual(n["enforcer"], "none")
            self.assertNotEqual(n["sha256"], c["sha256"])
            self.assertEqual(n, practice.neutral(c))

    def test_new_cards_and_lead_twin(self):
        for i in "HSL":
            c = practice.load(i)
            self.assertLessEqual(len(c["text"].encode()), 600)
            self.assertTrue(any(k in c["text"].lower() for k in ("hold", "instruction")))
        self.assertEqual(practice.load("D")["version"], "2")
        lead = practice.load("L")
        got = practice.lead_cards(lead, ["a0", "a1", "a2", "a3"], "a2")
        self.assertIs(got["a2"], lead)
        twins = [got[a] for a in ("a0", "a1", "a3")]
        for n in twins:
            self.assertEqual(n, practice.neutral(lead))
            self.assertEqual(len(n["text"].encode()), len(lead["text"].encode()))
        with self.assertRaises(ValueError):
            practice.lead_cards(lead, ["a0"], "zz")

    def test_one_byte_edit_changes_sha(self):
        with tempfile.TemporaryDirectory() as d:
            raw = open(os.path.join(practice.ROOT, "A.md"), "rb").read()
            p = os.path.join(d, "A.md")
            open(p, "wb").write(raw)
            a = practice.load("A", d)
            open(p, "wb").write(raw.replace(b"Claim", b"claim", 1))
            self.assertNotEqual(a["sha256"], practice.load("A", d)["sha256"])

    def test_missing_field_raises(self):
        with tempfile.TemporaryDirectory() as d:
            raw = open(os.path.join(practice.ROOT, "A.md")).read()
            for bad in (raw.replace("enforcer: router.claim_unique\n", ""),
                        raw.replace("\n---\n", "\n"), raw.split("---\n")[0] + "---\n"):
                open(os.path.join(d, "A.md"), "w").write(bad)
                with self.assertRaises(ValueError):
                    practice.load("A", d)
        with self.assertRaises(ValueError):
            practice.load("../A")

    def test_oversize_raises(self):
        with tempfile.TemporaryDirectory() as d:
            raw = open(os.path.join(practice.ROOT, "A.md")).read()
            open(os.path.join(d, "A.md"), "w").write(raw + "x" * 600)
            with self.assertRaises(ValueError):
                practice.load("A", d)

    def test_attach(self):
        c = practice.load("C")
        p, sha = practice.attach("Do the thing.\n", c)
        self.assertEqual(sha, c["sha256"])
        self.assertTrue(p.startswith("Do the thing.") and c["text"] in p)

    def test_leak_check_catches_planted_answer(self):  # adversarial
        c = practice.load("A")
        self.assertEqual(practice.leak_check(c, ["k7q2", "42"]), [])
        planted = {**c, "text": c["text"] + " Task K7Q2 is easy."}
        self.assertEqual(practice.leak_check(planted, ["k7q2", "42", ""]), ["k7q2"])


if __name__ == "__main__":
    unittest.main()
