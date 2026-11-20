import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "train"))
try:
    import torch
    import t7_gen as G
except ImportError:  # host has no torch; runs in the container
    torch = None


@unittest.skipIf(torch is None, "needs torch (container)")
class Filtered(unittest.TestCase):
    def test_presence_top_k_top_p(self):
        logits = torch.tensor([[5.0, 4.0, 3.0, 2.0, 1.0, 0.0]])
        seen = torch.tensor([[True, False, False, False, False, False]])
        out = G.filtered_logits(logits, 1.5, seen, 1.0, 3, 0.95)
        self.assertEqual(int(torch.isfinite(out).sum()), 3)  # top-k 3 survives
        self.assertTrue(torch.isfinite(out[0, 1]) and torch.isfinite(out[0, 2]))  # 5.0 penalised to 3.5, still top 3
        self.assertFalse(torch.isfinite(out[0, 4]))
        tiny = G.filtered_logits(logits, 0.0, torch.zeros_like(seen), 1.0, 6, 0.1)
        self.assertEqual(int(torch.isfinite(tiny).sum()), 1)  # the first token always stays


if __name__ == "__main__":
    unittest.main()
