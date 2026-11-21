from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab.quantum import custody, release_audit, topology_transfer


class GroverReleaseTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.paths = {name: self.root / name for name in ("trace", "scope", "witness")}
        self.trace = topology_transfer.compare((("sequential", 0), ("sequential", 2), ("complementary", 9)))
        self.trace_pin = self.write("trace", self.trace)

    def write(self, role, value):
        raw = custody.canonical(value)
        self.paths[role].write_bytes(raw)
        return sha256(raw).hexdigest()

    def rehearsal(self, *, regime="sequential", seed=0, access="shared", mode="peers"):
        self.scope = {
            "schema": release_audit.SCOPE, "trace_sha256": self.trace_pin, "run_id": "synthetic-run",
            "block_id": "synthetic-block", "regime": regime, "seed": seed, "mode": mode, "access": access,
        }
        self.scope_pin = self.write("scope", self.scope)
        case = next(row for row in self.trace["cases"] if (row["regime"], row["development_seed"]) == (regime, seed))
        arm = next(row for row in case["arms"] if (row["mode"], row["evidence_access"]) == (mode, access))
        events, _ = release_audit.project_events(arm, self.scope_pin)
        self.witness = {"schema": release_audit.WITNESS, "scope_sha256": self.scope_pin, "events": events}
        return self.verify()

    def verify(self):
        return release_audit.verify(**self.paths, scope_sha256=self.scope_pin,
                                    witness_sha256=self.write("witness", self.witness))

    def test_explicit_no_hit_and_exact_hit_release_different_branches(self):
        no_hit = self.rehearsal()
        self.assertEqual((no_hit["released_no_hits"], no_hit["fallback_uses"], no_hit["predecessor_hit_uses"]),
                         (1, 1, 1))
        hit = self.rehearsal(seed=2)
        self.assertEqual((hit["released_no_hits"], hit["fallback_uses"], hit["predecessor_hit_uses"]), (0, 0, 2))
        self.assertFalse(hit["observer_authenticated"])
        self.assertFalse(hit["native_delivery_verified"])

    def test_own_access_does_not_treat_absence_as_no_hit(self):
        own = self.rehearsal(access="own")
        self.assertEqual((own["verified_stage_count"], own["released_no_hits"], own["fallback_uses"]), (1, 0, 0))
        join = self.rehearsal(regime="complementary", seed=9)
        self.assertEqual((join["released_shards"], join["verified_stage_count"], join["fallback_uses"]), (2, 1, 0))

    def test_repinned_late_early_and_wrong_source_release_fails(self):
        self.rehearsal()
        original = deepcopy(self.witness)
        for field, value in (("available_round", 1), ("available_round", 3), ("owner", "a"),
                             ("status", "hit"), ("answer", [1, "25/32"]), ("receipt_id", "1" * 64)):
            with self.subTest(field=field, value=value):
                self.witness = deepcopy(original)
                release = next(row for row in self.witness["events"] if row.get("status") == "no_hit")
                release[field] = value
                with self.assertRaisesRegex(ValueError, "observed release does not match"):
                    self.verify()

    def test_fallback_requires_consumption_of_exact_predecessor_receipt(self):
        self.rehearsal()
        original = deepcopy(self.witness)
        for ids in ([], ["2" * 64]):
            with self.subTest(ids=ids):
                self.witness = deepcopy(original)
                final = next(row for row in self.witness["events"] if row["kind"] == "work" and row["task"] == "final")
                final["receipt_ids"] = ids
                with self.assertRaisesRegex(ValueError, "observed work does not match"):
                    self.verify()

    def test_crossed_block_and_run_remain_refused_when_header_is_repinned(self):
        self.rehearsal()
        for role in ("block_id", "run_id"):
            with self.subTest(role=role):
                prior = self.scope[role]
                self.scope[role] = "other-unit"
                self.scope_pin = self.write("scope", self.scope)
                self.witness["scope_sha256"] = self.scope_pin
                with self.assertRaisesRegex(ValueError, "observed read does not match"):
                    self.verify()
                self.scope[role] = prior

    def test_budget_stopped_prefix_withholds_complete_schedule_fallback_count(self):
        for budget, reads, no_hits in ((1, 0, 0), (21, 9, 1)):
            with self.subTest(budget=budget):
                self.trace = topology_transfer.compare((("sequential", 0),), budget=budget)
                self.trace_pin = self.write("trace", self.trace)
                report = self.rehearsal()
                self.assertTrue(report["budget_stopped"])
                self.assertEqual(report["coverage"], "budget_stopped_prefix")
                self.assertEqual((report["observed_read_slots"], report["released_no_hits"]), (reads, no_hits))
                self.assertEqual(report["fallback_uses"], 0)
                self.assertIsNone(report["complete_schedule_fallback_uses"])

    def test_missing_no_hit_release_does_not_become_a_successful_stop(self):
        self.rehearsal()
        self.witness["events"] = [row for row in self.witness["events"] if row.get("status") != "no_hit"]
        with self.assertRaisesRegex(ValueError, "misses scheduled events"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
