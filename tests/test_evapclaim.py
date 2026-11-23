import unittest

from murmuration import evapclaim as E


class EvaporatingClaims(unittest.TestCase):
    def test_worked_example_dead_worker_claim_fades(self):
        # Round 0: worker on "a" renews, "b" is held by a dead worker at 1.0, "c" is open.
        marks = {"a": 1.0, "b": 1.0}
        # Two rounds with retain 0.5 and only "a" renewed: b = 1.0 * 0.5 * 0.5 = 0.25.
        for _ in range(2):
            marks = E.evaporate(marks, renewed={"a"}, retain=0.5)
        self.assertEqual(marks, {"a": 1.0, "b": 0.25})
        # "c" is unmarked (0) so it is weakest; once "c" is done, the faded "b" (0.25) beats "a" (1.0).
        self.assertEqual(E.choose(marks, {"a", "b", "c"}, agent_rank=0), "c")
        self.assertEqual(E.choose(marks, {"a", "b"}, agent_rank=0), "b")

    def test_tie_break_spreads_agents(self):
        # Three unmarked tasks tie at 0; ranks 0, 1, 2 take x, y, z; rank 3 wraps to x.
        picks = [E.choose({}, {"z", "x", "y"}, r) for r in range(4)]
        self.assertEqual(picks, ["x", "y", "z", "x"])

    def test_renewal_of_new_task_and_no_open_task(self):
        self.assertEqual(E.evaporate({}, renewed={"n"}, retain=0.9), {"n": 1.0})
        self.assertIsNone(E.choose({"a": 0.1}, set(), agent_rank=0))

    def test_malformed_inputs_raise(self):
        for retain in (0, 1, 1.5, -0.1, True, "0.5"):
            with self.assertRaises(ValueError):
                E.evaporate({"a": 1.0}, (), retain)
        with self.assertRaises(ValueError):
            E.evaporate({"a": 2.0}, (), 0.5)
        with self.assertRaises(ValueError):
            E.choose({"a": -1}, {"a"}, 0)
        with self.assertRaises(ValueError):
            E.choose({}, {"a"}, -1)


if __name__ == "__main__":
    unittest.main()
