import json
from pathlib import Path
from tempfile import mkdtemp
import unittest

from lab.log_head_receipt import snapshot, verify
from murmuration import board, cell


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(mkdtemp(prefix="murmuration-receipt-test-"))

    def test_cell_valid_rewrite_does_not_match_receipt(self):
        original = self.root / "cell"
        rewritten = self.root / "rewritten"
        original.mkdir()
        rewritten.mkdir()
        cell.append_log(original, {"result": "original"})
        cell.append_log(rewritten, {"result": "changed"})
        receipt = json.loads(json.dumps(snapshot("cell", "run/a0", original)))
        self.assertTrue(verify(receipt, "cell", "run/a0", original))
        self.assertTrue(cell.verify_log(rewritten))
        self.assertFalse(verify(receipt, "cell", "run/a0", rewritten))

    def test_board_receipt_binds_terminal_head_and_identity(self):
        path = self.root / "board.jsonl"
        instance = board.Board(path, seed=1)
        receipt = snapshot("board", "run/board", path)
        self.assertTrue(verify(receipt, "board", "run/board", path))
        self.assertFalse(verify(receipt, "board", "other/board", path))
        self.assertFalse(verify(receipt, "board", "run/board", self.root / "missing"))
        self.assertFalse(verify(dict(receipt, count=True), "board", "run/board", path))
        instance.end_round()
        self.assertFalse(verify(receipt, "board", "run/board", path))
