import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from lab import l4e_timeline_token_count


class L4ETimelineTokenCountTests(unittest.TestCase):
    @staticmethod
    def digest(raw):
        return hashlib.sha256(raw).hexdigest()

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        note = self.artifact("note", b"valve was open")
        stem = {"chain_id": "chain", "source_id": "source", "family_id": "family", "source_version": 1}
        events = [
            {**stem, "event_id": "stimulus", "step": 0, "kind": "stimulus", "target_event_id": None,
             "content": note},
            {**stem, "event_id": "withdrawal", "step": 1, "kind": "withdrawal", "target_event_id": "stimulus",
             "content": None},
        ]
        slots = [
            {"slot_id": "present", "chain_id": "chain", "step": 0, "event_ids": ["stimulus"],
             "adapter_uses": 2, "context_uses": 1},
            {"slot_id": "empty", "chain_id": "chain", "step": 1, "event_ids": [],
             "adapter_uses": 1, "context_uses": 2},
        ]
        adapter = [
            {"slot_id": "present", "use": 1, "event_id": "stimulus", "text": "valve was open"},
            {"slot_id": "present", "use": 2, "event_id": "stimulus", "text": "valve was open"},
            {"slot_id": "empty", "use": 1, "event_id": None, "text": None},
        ]
        self.document = {
            "schema": "l4e_timeline_v1", "protocol": self.artifact("protocol.md", b"Scripted fixture"),
            "events": events, "slots": slots,
            "adapter": self.artifact("adapter.jsonl", "".join(json.dumps(row) + "\n" for row in adapter).encode()),
            "context": self.artifact("context.tsv", b"present\t1\tstimulus\tvalve was open\nempty\t1\t\t\nempty\t2\t\t\n"),
        }
        self.protected = self.json_artifact("protected.json", {
            "schema": "l4e_protected_roles_v1", "source_ids": [], "family_ids": [],
        })
        self.tokenizer = Mock()
        self.tokenizer.encode.return_value = SimpleNamespace(ids=(1, 2, 3))

    def artifact(self, path, raw):
        (self.root / path).write_bytes(raw)
        return {"path": path, "sha256": self.digest(raw)}

    def json_artifact(self, path, data):
        return self.artifact(path, json.dumps(data).encode())

    def count(self):
        manifest = self.json_artifact("timeline.json", self.document)
        with patch.object(l4e_timeline_token_count.l4e_public_token_count, "load_tokenizer",
                          return_value=(self.tokenizer, {"manifest_sha256": "a" * 64})):
            return l4e_timeline_token_count.count(
                self.root, self.root / manifest["path"], self.root / self.protected["path"], self.root,
                manifest_sha256=manifest["sha256"], protected_sha256=self.protected["sha256"],
                snapshot_sha256="a" * 64,
            )

    def test_repeated_and_explicitly_empty_visits_stay_distinct_from_runtime_unknowns(self):
        report = self.count()
        adapter, context = (report["arms"][arm] for arm in ("adapter", "context"))
        self.assertEqual((adapter["raw_note_tokens"], context["raw_note_tokens"]), (6, 3))
        self.assertEqual((adapter["empty_payload_visits"], context["empty_payload_visits"]), (1, 2))
        self.assertEqual(context["slots"][1]["visits"][1], {
            "use": 2, "content_rows": 0, "empty_payload": True, "raw_note_tokens": 0,
        })
        self.assertIsNone(report["observed_model_tokens"])
        self.assertIsNone(report["observed_runtime_uses"])
        self.assertIsNone(report["observed_gpu_wall_seconds"])
        self.assertIs(report["authorizes_training"], False)
        self.tokenizer.encode.assert_called_once_with("valve was open", add_special_tokens=False)

    def test_re_pinned_ineligible_projection_is_refused_before_tokenizing(self):
        self.document["context"] = self.artifact("early.tsv", b"present\t1\tstimulus\tvalve was shut\n")
        with self.assertRaisesRegex(ValueError, "context projection differs"):
            self.count()
        self.tokenizer.encode.assert_not_called()
