from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l5_matrix, l5_matrix_delivery_audit as audit, l5_shard_cpu_worker


class L5MatrixDeliveryAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(cls.enterClassContext(TemporaryDirectory()))
        cls.matrix = cls.root / "matrix"
        cls.sidecar = cls.root / "delivery-evidence.json"
        worker = cls.root / "worker.py"
        worker.write_bytes(Path(l5_shard_cpu_worker.__file__).read_bytes())
        cls.worker_sha256 = cls.sha(worker)
        witnesses = []

        def scripted_worker(frame, guide):
            acknowledged = hashlib.sha256(guide.encode()).hexdigest() if guide is not None else None
            observations = {"own": acknowledged, "foreign": None, "unknown": None, "bulk": None, "forged": None}
            session = {"condition": frame["condition"], "phase": frame["phase"], "observations": observations}
            receipt = {"sessions": [session], "worker_mount_readonly": True}
            witnesses.append({"frame": dict(frame), "worker_receipt": receipt,
                              "container_id": f"{len(witnesses) + 1:064x}", "removed": True})
            return acknowledged

        l5_matrix.run(cls.matrix, seed=86, contended=True, verify_delivery=scripted_worker)
        cls.summary_sha256 = cls.sha(cls.matrix / "summary.json")
        cls.index = {"evidence": "scripted_cpu_matrix_delivery", "summary_sha256": cls.summary_sha256,
                     "worker_sha256": cls.worker_sha256, "rows": witnesses}
        cls.sidecar_sha256 = cls.write_index(cls.sidecar, cls.index)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @classmethod
    def write_index(cls, path, index):
        path.write_text(json.dumps(index, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        return cls.sha(path)

    def verify(self, *, sidecar=None, sidecar_sha256=None, summary_sha256=None):
        return audit.verify(self.matrix, summary_sha256=self.summary_sha256 if summary_sha256 is None else summary_sha256,
                            sidecar=self.sidecar if sidecar is None else sidecar,
                            sidecar_sha256=self.sidecar_sha256 if sidecar_sha256 is None else sidecar_sha256)

    def test_full_offline_matrix_replays_all_worker_receipts(self):
        report = self.verify()
        self.assertEqual((report["arms"], report["work_attempts"], report["named_reads"]), (20, 120, 96))
        self.assertEqual(report["delivery_witnesses"], 96)
        self.assertEqual(report["worker_sha256"], self.worker_sha256)
        self.assertEqual(report["sidecar_sha256"], self.sidecar_sha256)
        counts = Counter((row["frame"]["block_id"], row["frame"]["condition"].split(":")[0])
                         for row in self.index["rows"])
        self.assertEqual(counts, Counter({(f"team-{size}", carrier): 4 * size
                                         for size in (4, 8) for carrier in ("environment", "neutral")}))

    def test_wrong_independent_summary_and_sidecar_pins_are_rejected(self):
        for field, file in (("summary_sha256", "summary.json"), ("sidecar_sha256", "delivery-evidence.json")):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, file):
                self.verify(**{field: "0" * 64})

    def test_stale_board_prefix_cannot_acknowledge_post_release_delivery_even_when_repinned(self):
        index = deepcopy(self.index)
        stale = next(row["frame"] for row in index["rows"] if row["frame"]["condition"] == "environment:disrupted"
                     and row["frame"]["worker"] == "a1" and row["frame"]["phase"] == "post")
        earlier = next(row["frame"] for row in index["rows"] if row["frame"]["arm_id"] == stale["arm_id"]
                       and row["frame"]["worker"] == "a1" and row["frame"]["phase"] == "pre")
        for field in ("board_head", "board_event_count"):
            self.assertNotEqual(stale[field], earlier[field])
            stale[field] = earlier[field]
        sidecar = self.root / "stale.json"
        pin = self.write_index(sidecar, index)
        with self.assertRaisesRegex(ValueError, "isolated receipt does not bind the archived delivery frame"):
            self.verify(sidecar=sidecar, sidecar_sha256=pin)

    def test_reordered_receipts_are_rejected_even_when_repinned(self):
        index = deepcopy(self.index)
        index["rows"][0], index["rows"][1] = index["rows"][1], index["rows"][0]
        sidecar = self.root / "reordered.json"
        pin = self.write_index(sidecar, index)
        with self.assertRaisesRegex(ValueError, "isolated receipt does not bind the archived delivery frame"):
            self.verify(sidecar=sidecar, sidecar_sha256=pin)

    def test_shortened_witness_inventory_is_rejected_even_when_repinned(self):
        index = deepcopy(self.index)
        index["rows"].pop()
        sidecar = self.root / "shortened.json"
        pin = self.write_index(sidecar, index)
        with self.assertRaisesRegex(ValueError, "delivery sidecar has missing or unexpected witness rows"):
            self.verify(sidecar=sidecar, sidecar_sha256=pin)

    def test_sidecar_pin_does_not_circumvent_the_copied_worker_digest(self):
        alternative = self.root / "changed-worker"
        alternative.mkdir()
        sidecar = alternative / self.sidecar.name
        sidecar.write_bytes(self.sidecar.read_bytes())
        (alternative / "worker.py").write_bytes(b"# Different scripted worker\n")
        with self.assertRaisesRegex(ValueError, "saved worker script does not match the sidecar pin"):
            self.verify(sidecar=sidecar)
