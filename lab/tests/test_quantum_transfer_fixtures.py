import json
import unittest
from fractions import Fraction

from lab.quantum import transfer, transfer_fixtures


class QuantumTransferFixtureTests(unittest.TestCase):
    def test_complementary_shards_together_reach_threshold(self):
        for seed, expected in ((9, (1, Fraction(1))), (0, None)):
            with self.subTest(seed=seed):
                fixture = transfer_fixtures.development_fixture("complementary", seed)
                a, b, c = (fixture.question_for(worker)["questions"][0] for worker in "abc")
                self.assertEqual(c, {"task": "join", "qubits": 4, "iteration_cap": 4,
                                     "mark_sources": ["a", "b"], "target": "1"})
                self.assertEqual(set(a), {"task", "qubits", "marked_indices"})
                self.assertEqual(set(b), set(a))
                self.assertTrue(set(a["marked_indices"]).isdisjoint(b["marked_indices"]))
                for shard in (a, b):
                    task = transfer.ThresholdTask(4, tuple(shard["marked_indices"]), 4, Fraction(1))
                    self.assertTrue(transfer.verify(task, None))
                other_answer = None if expected else (1, Fraction(1))
                self.assertTrue(fixture.score("join", "c", expected, {}))
                self.assertFalse(fixture.score("join", "c", other_answer, {}))
                self.assertFalse(fixture.score("join", "a", expected, {}))

    def test_redundant_workers_share_one_task_id_and_outcome(self):
        fixture = transfer_fixtures.development_fixture("redundant", 0)
        a, b, c = (fixture.question_for(worker)["questions"][0] for worker in "abc")
        self.assertEqual(a, b)
        self.assertEqual({a["task"], b["task"], c["task"]}, {"common", "separate"})
        self.assertNotEqual(a["marked_indices"], c["marked_indices"])
        for worker in "ab":
            self.assertTrue(fixture.score("common", worker, (2, Fraction(121, 128)), {}))
            self.assertFalse(fixture.score("common", worker, (3, Fraction(169, 512)), {}))
        self.assertTrue(fixture.score("separate", "c", None, {}))
        self.assertFalse(fixture.score("unknown", "c", None, {}))

    def test_sequential_stages_use_verified_hit_or_explicit_no_hit(self):
        for seed, scout, confirmation, final in (
            (0, (2, Fraction(121, 128)), None, (2, Fraction(121, 128))),
            (2, (1, Fraction(25, 32)), (1, Fraction(25, 32)), (1, Fraction(25, 32))),
        ):
            with self.subTest(seed=seed):
                fixture = transfer_fixtures.development_fixture("sequential", seed)
                result = {name: observed["first"] for name, observed in fixture.reference_results().items()}
                self.assertEqual(result, {"scout": scout, "confirm": confirmation, "final": final})
                b, c = (fixture.question_for(worker)["questions"][0] for worker in "bc")
                self.assertEqual(b["target_from_verified_task"], "scout")
                self.assertEqual(c["target_from_verified_task"], "confirm")
                self.assertNotIn("target", b)
                self.assertNotIn("target", c)
                self.assertEqual(c["target_if_predecessor_has_no_hit"], "4/5")
                self.assertTrue(fixture.score("scout", "a", scout, {}))
                self.assertFalse(fixture.score("confirm", "b", confirmation, {}))
                self.assertTrue(fixture.score("confirm", "b", confirmation, {"scout": scout}))
                self.assertFalse(fixture.score("final", "c", final, {"scout": scout}))
                self.assertTrue(fixture.score("final", "c", final, {"confirm": confirmation}))

    def test_worker_projection_is_deterministic_and_contains_only_public_fields(self):
        keys = {"task", "qubits", "marked_indices", "iteration_cap", "mark_sources", "target",
                "target_from_verified_task", "target_if_predecessor_has_no_hit"}
        for regime in transfer_fixtures.REGIMES:
            for worker in transfer_fixtures.WORKERS:
                with self.subTest(regime=regime, worker=worker):
                    build = transfer_fixtures.development_fixture
                    payload = build(regime, 42).question_for(worker)
                    self.assertEqual(json.dumps(payload), json.dumps(build(regime, 42).question_for(worker)))
                    self.assertEqual(set(payload), {"regime", "worker", "instruction", "questions"})
                    for question in payload["questions"]:
                        self.assertLessEqual(set(question), keys)
        with self.assertRaises(ValueError):
            transfer_fixtures.development_fixture("sequential", True)
        with self.assertRaises(ValueError):
            transfer_fixtures.development_fixture("unknown", 42)
        with self.assertRaises(ValueError):
            transfer_fixtures.development_fixture("redundant", 42).question_for("verifier")
