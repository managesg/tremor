import json
import subprocess
import sys
import unittest

from lab import l8_loader_receipt
from lab.tests import test_adapter_lineage as fixtures


class L8LoaderReceiptTests(unittest.TestCase):
    def setUp(self):
        import torch
        from safetensors.torch import save

        self.fixture = f = fixtures.AdapterLineageTests()
        self.addCleanup(f.doCleanups)
        f.setUp()
        f.receipt["checkpoints"] = {
            stage: f.artifact(stage + ".safetensors", save({"weight": torch.tensor([[weight, 2.0]])}))
            for stage, weight in (("before", 1.0), ("after", 3.0))
        }
        f.plan["checkpoints"] = f.receipt["checkpoints"]
        f.plan["l4_receipt"] = f.artifact("l4.json", f.receipt)
        self.plan = f.artifact("l8.json", f.plan)

    def test_cli_observes_the_checkpoint_loaded_into_both_modules(self):
        f = self.fixture
        result = subprocess.run([sys.executable, "-B", "-m", "lab.l8_loader_receipt", str(f.root),
                                 str(f.root / self.plan["path"]), "--plan-sha256", self.plan["sha256"],
                                 "--max-bytes", "2048"], capture_output=True, text=True, timeout=20, check=True)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["evidence"], "scripted_cpu_loader")
        self.assertEqual([row["hook_output"] for row in receipt["stages"]], [[[4.0]], [[8.0]]])
        for row in receipt["stages"]:
            self.assertEqual(row["checkpoint_sha256"], f.plan["checkpoints"][row["stage"]]["sha256"])
        self.assertNotEqual(*(row["installed_tensors"]["weight"]["sha256"] for row in receipt["stages"]))

    def test_refuses_dtype_conversion_before_loading(self):
        import torch

        f = self.fixture
        model = torch.nn.Linear(2, 1, bias=False, dtype=torch.float64)
        starting_weights = model.weight.detach().clone()
        with self.assertRaisesRegex(ValueError, "inventory, dtype or shape differ"):
            l8_loader_receipt._load_verified_cpu(model, f.root, f.plan["checkpoints"]["before"], max_bytes=2048)
        self.assertTrue(torch.equal(starting_weights, model.weight))

    def test_refuses_a_loader_that_changes_the_installed_weights(self):
        import torch

        class AlteredLoader(torch.nn.Linear):
            def load_state_dict(self, state_dict, *, strict, assign):
                result = super().load_state_dict(state_dict, strict=strict, assign=assign)
                with torch.no_grad():
                    self.weight.add_(1.0)
                return result

        f = self.fixture
        model = AlteredLoader(2, 1, bias=False)
        with self.assertRaisesRegex(ValueError, "installed module state differs"):
            l8_loader_receipt._load_verified_cpu(model, f.root, f.plan["checkpoints"]["before"], max_bytes=2048)
