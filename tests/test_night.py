import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from murmuration import night as N


def store(k=40, bad=10):
    s = []
    for i in range(k):
        s = N.add_note(s, f"a{i}", f"note number {i} says things", "w1", i // 5, [f"ev{i}"], false=i < bad)
    return s


def corrupt(n, rng):  # imperfect consolidator: turns true notes false 30% of the time
    return {"false": n.get("false") or rng.random() < 0.3}


perfect = lambda n: not n.get("false")


class Night(unittest.TestCase):
    def test_add_note_provenance_and_append_only(self):
        a = N.add_note([], "x", "t", "w", 0, ["e1", "e2"])
        b = N.add_note(a, "y", "u", "w", 1)
        self.assertEqual(len(a), 1)
        self.assertEqual(N.tokens(a), 1)
        self.assertEqual(N.tokens(N.add_note(a, "z", "a b c", "w", 0)), 4)
        self.assertEqual(b[0]["sources"], ["e1", "e2"])
        self.assertEqual((b[1]["author"], b[1]["episode"]), ("w", 1))
        with self.assertRaises(ValueError):
            N.add_note(b, "x", "dup", "w", 2)

    def test_s0_unchanged_and_old_kept(self):
        s = store()
        before = [dict(n) for n in s]
        r = N.consolidate(s, 0.0, 1, rewrite=corrupt, seed=1)
        self.assertEqual(r["store"], s)
        self.assertEqual(r["written"], [])
        self.assertEqual(s, before)

    def test_s1_rewrites_all_with_provenance_links(self):
        s = store()
        r = N.consolidate(s, 1.0, 3, seed=1)
        self.assertEqual(len(r["store"]), len(s))
        for old, new in zip(s, r["store"]):
            self.assertEqual(new["id"], "n3-" + old["id"])
            self.assertEqual(new["parents"], [old["id"]])
            self.assertEqual(new["sources"], old["sources"])
        self.assertEqual(N.lineage(r["store"] + s, "n3-a0"), {"a0"})
        self.assertEqual(r["tokens_read"], N.tokens(s))

    def test_partial_s_fraction_and_determinism(self):
        s = store(400, 0)
        r = N.consolidate(s, 0.25, 1, seed=7)
        self.assertAlmostEqual(len(r["written"]) / 400, 0.25, delta=0.06)
        self.assertEqual(r, N.consolidate(s, 0.25, 1, seed=7))
        self.assertNotEqual(r["written"], N.consolidate(s, 0.25, 1, seed=8)["written"])
        with self.assertRaises(ValueError):
            N.consolidate(s, 1.5, 1)

    def test_imperfect_consolidator_grows_false_share(self):  # control: the harm exists without a verifier
        s = store()
        r = N.consolidate(s, 1.0, 1, rewrite=corrupt, seed=2)
        self.assertGreater(N.false_share(r["store"]), N.false_share(s))

    def test_perfect_verifier_never_grows_false_share(self):
        for mode in ("direct", "gated"):
            cur = store()
            for night in range(1, 6):
                nxt = N.consolidate(cur, 0.8, night, verifier=perfect, mode=mode, rewrite=corrupt,
                                    seed=night)["store"]
                self.assertLessEqual(N.false_share(nxt), N.false_share(cur) + 1e-12, (mode, night))
                cur = nxt
        r = N.consolidate(store(), 1.0, 1, verifier=perfect, rewrite=corrupt, seed=3)
        self.assertEqual(N.false_share(r["store"]), 0.0)  # direct mode drops every false note it touches

    def test_gated_blocks_bad_write_keeps_original(self):
        s = store(20, 0)
        r = N.consolidate(s, 1.0, 1, verifier=perfect, mode="gated", rewrite=lambda n, g: {"false": True})
        self.assertEqual(r["store"], s)
        self.assertEqual(len(r["blocked"]), 20)
        with self.assertRaises(ValueError):
            N.consolidate(s, 1.0, 1, mode="gated")

    def test_placebo_changes_nothing_but_charges_tokens(self):
        s = store()
        p = N.placebo(s)
        self.assertEqual(p["store"], s)
        self.assertIsNot(p["store"][0], s[0])
        self.assertEqual(p["tokens_read"], N.consolidate(s, 1.0, 1)["tokens_read"])
        self.assertEqual((p["written"], p["dropped"]), ([], []))

    def test_rewrite_and_verifier_cannot_mutate_input_or_accepted_store(self):
        original = N.add_note([], "a", "three original words", "w", 1, ["source"])
        proposed_sources = ["source"]

        def rewrite(note, _rng):
            note["sources"].append("rewrite mutation")
            note["text"] = "mutation"
            return {"text": "two words", "sources": proposed_sources}

        def verify(note):
            note["sources"].append("verifier mutation")
            note["parents"].clear()
            return True

        for mode in ("direct", "gated"):
            with self.subTest(mode=mode):
                result = N.consolidate(original, 1, 2, verifier=verify, rewrite=rewrite, mode=mode)
                self.assertEqual(result["tokens_read"], 3)
                self.assertEqual(original[0]["text"], "three original words")
                self.assertEqual(original[0]["sources"], ["source"])
                self.assertEqual(result["store"][0]["text"], "two words")
                self.assertEqual(result["store"][0]["parents"], ["a"])
                self.assertEqual(result["store"][0]["sources"], ["source"])
                result["store"][0]["sources"].append("consumer mutation")
                self.assertEqual(proposed_sources, ["source"])

    def test_fresh_outputs_isolate_nested_state(self):
        original = N.add_note([], "a", "text", "w", 1, ["source"], extra={"tags": ["stable"]})
        for output in (
            N.add_note(original, "b", "other", "w", 1),
            N.placebo(original)["store"],
            N.consolidate(original, 0, 2)["store"],
            N.consolidate(original, 1, 2, mode="gated", verifier=lambda _note: False)["store"],
        ):
            output[0]["sources"].append("consumer mutation")
            output[0]["extra"]["tags"].append("external")
            self.assertEqual(original[0]["sources"], ["source"])
            self.assertEqual(original[0]["extra"]["tags"], ["stable"])

if __name__ == "__main__":
    unittest.main()
