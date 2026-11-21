import unittest

from lab import r1_quiet_evidence


SAMPLE = b"""2026-11-21T15:11:13Z
 10:11:13 up 4 days,  5 users,  load average: 2.26, 2.07, 1.83
MemAvailable:   74926980 kB
SwapFree:        9603668 kB
procs -----------memory---------- ---swap-- -----io---- -system-- -------cpu-------
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st gu
 0  0 7173544 4579984 3068564 68711852   31   45  1485  3598 21806   13  5  3 92  0  0  0
 0  0 7173544 4562324 3068564 68711876  136    0   136   172 23641 29161  3  2 95  0  0  0
tremor-r1-candidate-test-2 Up About a minute
"""


class R1QuietEvidenceTests(unittest.TestCase):
    def test_vmstat_uses_interval_and_retains_swap_activity(self):
        sample, = r1_quiet_evidence._samples(SAMPLE)
        self.assertEqual(sample["observed_container_name"], "tremor-r1-candidate-test-2")
        self.assertEqual(sample["vmstat_interval"], {
            "idle_percent": 95, "io_wait_percent": 0, "swap_in": 136, "swap_out": 0,
        })

    def test_missing_sample_fields_fail_closed(self):
        invalid = SAMPLE.replace(b"MemAvailable:   74926980 kB\n", b"")
        with self.assertRaisesRegex(ValueError, "lacks load, memory or swap"):
            r1_quiet_evidence._samples(invalid)

    def test_boundary_snapshot_does_not_fill_missing_cpu_measurement_with_zero(self):
        time_and_memory = SAMPLE.split(b"procs ---", 1)[0]
        sample, = r1_quiet_evidence._samples(time_and_memory)
        self.assertIsNone(sample["vmstat_interval"])
