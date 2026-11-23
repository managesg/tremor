import json
import subprocess
import sys
import unittest

from lab import adapter_lineage
from lab.tests import test_adapter_lineage as fixtures


class AdapterTensorLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AdapterLineageTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def checkpoint(self, stage, values, *, metadata, shape):
        import numpy
        from safetensors.numpy import save

        data = save({"weight": numpy.asarray(values, dtype=numpy.float32).reshape(shape)},
                    metadata={"label": metadata})
        return self.fixture.artifact(stage + ".safetensors", data)

    def bind(self, before, after):
        f = self.fixture
        checkpoints = {"before": before, "after": after}
        f.receipt["checkpoints"] = checkpoints
        f.plan["checkpoints"] = checkpoints
        f.plan["l4_receipt"] = f.artifact("l4.json", f.receipt)

    def verify(self, limit=2048):
        return adapter_lineage.verify_tensor_change(self.fixture.root, self.fixture.plan, max_bytes=limit)

    def test_same_weights_with_distinct_metadata_cannot_supply_a_change(self):
        before = self.checkpoint("before", [1.0, 2.0], metadata="first", shape=[2])
        after = self.checkpoint("after", [1.0, 2.0], metadata="second", shape=[2])
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.bind(before, after)
        self.assertEqual(self.fixture.verify()["after_sha256"], after["sha256"])
        with self.assertRaisesRegex(ValueError, "tensor payloads are unchanged"):
            self.verify()

    def test_payload_change_and_comparability(self):
        before = self.checkpoint("before", [1.0, 2.0], metadata="first", shape=[2])
        after = self.checkpoint("after", [1.0, 3.0], metadata="second", shape=[2])
        self.bind(before, after)
        checked = self.verify()
        self.assertEqual((checked["checkpoint_tensor_count"], checked["changed_tensor_count"]), (1, 1))
        with self.assertRaisesRegex(ValueError, "CPU inspection limit"):
            self.verify(limit=1)
        reshaped = self.checkpoint("after", [1.0, 3.0], metadata="second", shape=[1, 2])
        self.bind(before, reshaped)
        with self.assertRaisesRegex(ValueError, "tensor identities, types or shapes differ"):
            self.verify()

    def test_invalid_tensor_file_cannot_use_valid_opaque_digest(self):
        before = self.checkpoint("before", [1.0, 2.0], metadata="first", shape=[2])
        after = self.fixture.artifact("after.safetensors", b"invalid container")
        self.bind(before, after)
        with self.assertRaisesRegex(ValueError, "invalid Safetensors checkpoint"):
            self.verify()

    def test_pinned_tensor_header_cannot_shadow_a_conflicting_dtype(self):
        f = self.fixture
        before = self.checkpoint("before", [1.0, 2.0], metadata="first", shape=[2])
        after = self.checkpoint("after", [1.0, 3.0], metadata="second", shape=[2])
        data = (f.root / after["path"]).read_bytes()
        length = int.from_bytes(data[:8], "little")
        raw_header = data[8:8 + length].rstrip()
        first_weight = dict(json.loads(raw_header)["weight"], dtype="I32")
        duplicate = b'{"weight":' + json.dumps(first_weight).encode() + b"," + raw_header[1:]
        self.bind(before, f.artifact("after.safetensors",
                                    len(duplicate).to_bytes(8, "little") + duplicate + data[8 + length:]))
        plan = f.artifact("l8.json", f.plan)
        outcome = subprocess.run([sys.executable, "-B", "-m", "lab.adapter_lineage", str(f.root),
                                  str(f.root / "l8.json"), "--plan-sha256", plan["sha256"],
                                  "--safetensors-max-bytes", "2048"],
                                  capture_output=True, text=True, timeout=5, check=False)
        self.assertEqual(outcome.returncode, 2)
        self.assertIn("after.safetensors: duplicate JSON member", outcome.stderr)
