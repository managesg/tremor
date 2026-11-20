import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from train import power, t7_arms, t7_edit  # noqa: E402

CSV = ("timestamp, power.draw.instant [W], power.draw.average [W]\n"
       "2026/11/19 10:00:00.000, 5.00 W, 4.00 W\n"
       "2026/11/19 10:00:01.000, 15.00 W, 4.00 W\n"
       "2026/11/19 10:00:02.000, [N/A], 4.00 W\n"
       "2026/11/19 10:00:03.000, 15.00 W, 4.00 W\n")


class T7(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(power.parse_watts("5.07 W"), 5.07)
        self.assertIsNone(power.parse_watts("[N/A]"))
        s = power.parse_csv(CSV)
        self.assertEqual([x[1] for x in s], [5.0, 15.0, 15.0])
        self.assertEqual([x[1] for x in power.parse_csv(CSV, "power.draw.average")], [4.0] * 4)

    def test_energy(self):
        r = power.sample([(0, 10, 50), (1, 20, 50), (3, 20, 50)], baseline_w=10)
        self.assertAlmostEqual(r["joules_gpu"], 15 + 40)
        self.assertAlmostEqual(r["joules_gpu_net"], 55 - 10 * 3)
        self.assertEqual(r["seconds"], 3)
        self.assertEqual(r["idle_fraction"], 0.0)
        self.assertEqual(r["units"]["joules_gpu"], "J")
        self.assertIn("GPU-only", r["note"])
        self.assertIsNone(power.sample([(0, 5), (2, 5)])["joules_gpu_net"])

    def test_idle_is_utilization_not_power(self):
        # constant 100 W, fully busy: old code (power <= job minimum * 1.1) said idle_fraction 1.0
        r = power.sample([(0, 100, 90), (1, 100, 90), (2, 100, 90)])
        self.assertEqual(r["idle_fraction"], 0.0)
        # 1 s busy, 3 s at utilization 0 -> 0.75 of GPU-seconds idle
        r = power.sample([(0, 50, 80), (1, 30, 0), (2, 30, 0), (3, 30, 0), (4, 30, 0)])
        self.assertAlmostEqual(r["idle_fraction"], 0.75)
        self.assertIsNone(power.sample([(0, 5), (2, 5)])["idle_fraction"])  # util unknown
        self.assertIsNone(power.sample([(5, 5, 0), (5, 5, 0)])["idle_fraction"])  # zero seconds

    def test_baseline_watts(self):
        self.assertEqual(power.baseline_watts([(0, 4, 0), (60, 4, 0)]), 4.0)
        r = power.sample([(0, 104, 9), (10, 104, 9)], baseline_w=4.0)
        self.assertAlmostEqual(r["joules_gpu"], 1040)
        self.assertAlmostEqual(r["joules_gpu_net"], 1000)

    def test_baseline_is_mean_not_minimum(self):
        self.assertAlmostEqual(power.baseline_watts([(0, 2, 0), (10, 6, 0)]), 4.0)  # min would be 2

    def test_idle_means_utilization_exactly_zero(self):
        # low but nonzero utilization is busy: 'u < 5' would count it idle
        r = power.sample([(0, 9, 3), (1, 9, 3), (2, 9, 3)])
        self.assertEqual(r["idle_fraction"], 0.0)

    def test_plan_sampler_format(self):
        # PLAN/WORKPLAN sec 6: --format=csv,noheader,nounits, no header line (old code: bare StopIteration)
        txt = "2026/11/19 19:10:54.000, 4.80, 4\n2026/11/19 19:10:55.000, 90.5, 0\n2026/11/19 19:10:56.000, [N/A], 3\n"
        s = power.parse_csv(txt)
        self.assertEqual([(x[1], x[2]) for x in s], [(4.8, 4), (90.5, 0)])
        h = power.parse_csv("timestamp, power.draw.instant [W], utilization.gpu [%]\n"
                            "2026/11/19 19:10:54.162, 4.80 W, 4 %\n2026/11/19 19:10:55.162, 5.00 W, 0 %\n")
        self.assertEqual([(x[1], x[2]) for x in h], [(4.8, 4), (5.0, 0)])
        with self.assertRaises(ValueError):
            power.parse_csv("timestamp, foo\n2026/11/19 19:10:54.162, 1\n")
        with self.assertRaises(ValueError):
            power.parse_csv("")

    def test_truncation_sampling(self):
        recs = [{"correct": True, "tokens": 1000}, {"correct": True, "tokens": 5000},
                {"correct": True, "tokens": 30000}, {"correct": False, "tokens": 10}]
        self.assertEqual(t7_arms.accuracy_at_cap(recs, 2048), 0.25)
        self.assertEqual(t7_arms.accuracy_at_cap(recs, 8192), 0.5)
        a = t7_arms.sample_problems(range(500), 10, 7)
        self.assertEqual(a, t7_arms.sample_problems(range(500), 10, 7))
        self.assertNotEqual(a, t7_arms.sample_problems(range(500), 10, 8))

    def test_jsonl_partial(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.jsonl")
            t7_arms.write_result(p, {"id": 1, "arm": "B", "cap": 2048, "seed": None, "correct": True, "tokens": 5})
            with open(p, "a") as f:
                f.write('{"id": 2, "corr')  # torn line from a killed run
            self.assertEqual(len(t7_arms.read_results(p)), 1)
            calls = []
            t7_arms.run("B", [{"id": 1}, {"id": 3}], 2048, p,
                        lambda s, pr, c: calls.append(pr["id"]) or {"correct": False, "tokens": 1})
            self.assertEqual(calls, [3])

    def test_resume_key_includes_arm_cap_seed(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.jsonl")
            gen = lambda s, pr, c: {"correct": True, "tokens": 1}
            t7_arms.run("0", [{"id": 1}, {"id": 2}], 2048, p, gen)
            calls = []
            g2 = lambda s, pr, c: calls.append(pr["id"]) or gen(s, pr, c)
            t7_arms.run("B", [{"id": 1}, {"id": 2}], 2048, p, g2)  # old code: 0 calls, arm skipped
            self.assertEqual(calls, [1, 2])
            t7_arms.run("B", [{"id": 1}], 8192, p, g2)  # other cap runs
            t7_arms.run("B", [{"id": 1}], 8192, p, g2, seed=7)  # other seed runs
            t7_arms.run("B", [{"id": 1}], 8192, p, g2, seed=7)  # same key skips
            self.assertEqual(calls, [1, 2, 1, 1])

    def test_edit(self):
        w = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        base = t7_edit.checksum(w)
        out, rep = t7_edit.apply_column_edit(w, {"columns": [1], "values": [[9.0, 8.0]]}, base)
        self.assertEqual(out, [[1.0, 9.0, 3.0], [4.0, 8.0, 6.0]])
        self.assertEqual(t7_edit.checksum(w), base)
        self.assertEqual(rep["base_sha256"], base)
        self.assertNotEqual(rep["edited_sha256"], base)
        with self.assertRaises(IndexError):
            t7_edit.apply_column_edit(w, {"columns": [3], "values": [[0, 0]]}, base)
        with self.assertRaises(ValueError):
            t7_edit.apply_column_edit(w, {"columns": [0], "values": [[0]]}, base)
        spec = {"columns": [1], "values": [[9.0, 8.0]]}
        bad = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.5]]  # modified base must abort, not be compared with itself
        with self.assertRaises(ValueError):
            t7_edit.apply_column_edit(bad, spec, base)
        with self.assertRaises(ValueError):
            t7_edit.apply_column_edit(w, spec, "0" * 64)
        with self.assertRaises(ValueError):
            t7_edit.apply_column_edit([[1.0, 2.0], [3.0]], spec, t7_edit.checksum([[1.0, 2.0], [3.0]]))
        self.assertEqual(t7_edit.diff_of_means([[2, 0]], [[0, 0]]), [1.0, 0.0])


if __name__ == "__main__":
    unittest.main()
