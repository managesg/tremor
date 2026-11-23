from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l4e_timeline


class L4ETimelineTests(unittest.TestCase):
    text = {"support": "pressure remained steady", "stimulus": "valve was open", "correction": "valve was shut"}

    def setUp(self):
        self.bundle = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.manifest = self.bundle / "timeline.json"
        self.protected = self.bundle / "protected.json"
        self.protected_document = {"schema": "l4e_protected_roles_v1", "source_ids": ["protected-source"],
                                   "family_ids": ["protected-family"]}
        self.protected_sha256 = self.write_json(self.protected, self.protected_document)
        self.document = {"schema": "l4e_timeline_v1", "protocol": self.artifact("protocol.md", b"Offline test protocol\n"),
                         "events": [self.event("support", "reading", "reading-family", 1, 0, "support"),
                                    self.event("stimulus", "flag-v1", "flag-family", 1, 2, "stimulus"),
                                    self.event("withdrawal", "flag-v1", "flag-family", 1, 4, "withdrawal", "stimulus"),
                                    self.event("correction", "flag-v2", "flag-family", 2, 6, "correction", "stimulus")],
                         "slots": [self.slot("before", 0, ["support"], 2, 1),
                                   self.slot("present", 2, ["support", "stimulus"], 1, 2),
                                   self.slot("withdrawn", 4, ["support"], 1, 1),
                                   self.slot("corrected", 6, ["support", "correction"], 2, 1)]}
        self.write_projections(self.document, "original")
        self.manifest_sha256 = self.write_json(self.manifest, self.document)

    @staticmethod
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def write_json(self, path, document):
        raw = (json.dumps(document, sort_keys=True, allow_nan=False) + "\n").encode()
        path.write_bytes(raw)
        return self.sha(raw)

    def artifact(self, name, raw):
        (self.bundle / name).write_bytes(raw)
        return {"path": name, "sha256": self.sha(raw)}

    def event(self, event_id, source_id, family_id, version, step, kind, target=None):
        content = (self.artifact(f"{event_id}.txt", self.text[event_id].encode()) if event_id in self.text else None)
        return {"event_id": event_id, "chain_id": "chain-one", "source_id": source_id, "family_id": family_id,
                "source_version": version, "step": step, "kind": kind, "target_event_id": target, "content": content}

    @staticmethod
    def slot(slot_id, step, events, adapter_uses, context_uses):
        return {"slot_id": slot_id, "chain_id": "chain-one", "step": step, "event_ids": events,
                "adapter_uses": adapter_uses, "context_uses": context_uses}

    def write_projections(self, document, name):
        for arm in ("adapter", "context"):
            rows = [(slot["slot_id"], use, event_id, None if event_id is None else self.text[event_id])
                    for slot in document["slots"] for use in range(1, slot[f"{arm}_uses"] + 1)
                    for event_id in (slot["event_ids"] or [None])]
            if arm == "adapter":
                fields = ("slot_id", "use", "event_id", "text")
                raw = "".join(json.dumps(dict(zip(fields, row, strict=True)), sort_keys=True) + "\n" for row in rows)
                document[arm] = self.artifact(f"{name}.jsonl", raw.encode())
            else:
                raw = "".join("\t".join("" if value is None else str(value) for value in row) + "\n" for row in rows)
                document[arm] = self.artifact(f"{name}.tsv", raw.encode())

    def verify(self, *, manifest_sha256=None, protected_sha256=None):
        return l4e_timeline.verify(self.bundle, self.manifest,
                                   manifest_sha256=self.manifest_sha256 if manifest_sha256 is None else manifest_sha256,
                                   protected=self.protected,
                                   protected_sha256=self.protected_sha256 if protected_sha256 is None else protected_sha256)

    def test_accepts_eligible_exposures_with_unequal_declared_uses(self):
        report = self.verify()
        self.assertEqual(report["status"], "verified_timeline_projection")
        self.assertIs(report["authorizes_training"], False)
        self.assertIsNone(report["observed_model_tokens"])
        self.assertIsNone(report["observed_runtime_uses"])
        self.assertIs(report["independent_content_ancestry_verified"], False)
        support, stimulus, correction = (len(self.text[key].encode()) for key in ("support", "stimulus", "correction"))
        self.assertEqual(report["arms"], {
            "adapter": {"uses": 6, "content_rows": 9, "text_bytes": 6 * support + stimulus + 2 * correction,
                        "artifact_sha256": self.document["adapter"]["sha256"]},
            "context": {"uses": 5, "content_rows": 8, "text_bytes": 5 * support + 2 * stimulus + correction,
                        "artifact_sha256": self.document["context"]["sha256"]},
        })
        self.assertEqual([row["slot_id"] for row in report["slots"]], ["before", "present", "withdrawn", "corrected"])
        for slot, row in zip(self.document["slots"], report["slots"], strict=True):
            pairs = [(event, self.text[event]) for event in slot["event_ids"]]
            self.assertEqual(row["selected_rows"], len(pairs))
            self.assertEqual(row["semantic_sha256"], self.sha(json.dumps(pairs, separators=(",", ":")).encode()))

    def test_empty_slot_after_withdrawal_requires_an_explicit_marker_per_use(self):
        document = deepcopy(self.document)
        document["events"] = document["events"][1:3]
        document["slots"] = [self.slot("present", 2, ["stimulus"], 1, 1), self.slot("empty", 4, [], 1, 2)]
        self.write_projections(document, "empty")
        pin = self.write_json(self.manifest, document)
        report = self.verify(manifest_sha256=pin)
        text_bytes = len(self.text["stimulus"].encode())
        self.assertEqual(report["arms"], {
            "adapter": {"uses": 2, "content_rows": 1, "text_bytes": text_bytes,
                        "artifact_sha256": document["adapter"]["sha256"]},
            "context": {"uses": 3, "content_rows": 1, "text_bytes": text_bytes,
                        "artifact_sha256": document["context"]["sha256"]},
        })
        raw = (self.bundle / document["context"]["path"]).read_bytes()
        self.assertEqual(raw, b"present\t1\tstimulus\tvalve was open\nempty\t1\t\t\nempty\t2\t\t\n")

        document["context"] = self.artifact("missing-empty-marker.tsv", raw.removesuffix(b"empty\t2\t\t\n"))
        with self.assertRaisesRegex(ValueError, "context projection differs from the frozen ordered slot uses"):
            self.verify(manifest_sha256=self.write_json(self.manifest, document))

    def test_both_arms_cannot_consistently_leak_early_or_read_withdrawn_stimulus(self):
        for position, label in ((0, "early"), (2, "withdrawn")):
            with self.subTest(label=label):
                document = deepcopy(self.document)
                document["slots"][position]["event_ids"].append("stimulus")
                self.write_projections(document, label)
                manifest_sha256 = self.write_json(self.manifest, document)
                with self.assertRaisesRegex(ValueError, "slot selects content outside the active chain prefix"):
                    self.verify(manifest_sha256=manifest_sha256)

    def test_protected_sources_and_families_cannot_enter_the_public_timeline(self):
        for field, value in (("source_ids", "flag-v2"), ("family_ids", "flag-family")):
            with self.subTest(role=field):
                inventory = {**self.protected_document, field: [value]}
                protected_sha256 = self.write_json(self.protected, inventory)
                with self.assertRaisesRegex(ValueError, "protected source or family in public timeline"):
                    self.verify(protected_sha256=protected_sha256)

    def test_repinning_cannot_hide_duplicate_reordered_or_missing_exposures(self):
        for arm in ("adapter", "context"):
            original = (self.bundle / self.document[arm]["path"]).read_bytes()
            lines = original.splitlines(keepends=True)
            alternatives = {"duplicate": original + lines[0], "reordered": b"".join([lines[1], lines[0], *lines[2:]]),
                            "missing": b"".join(lines[:-1])}
            for label, changed in alternatives.items():
                with self.subTest(arm=arm, change=label):
                    document = deepcopy(self.document)
                    extension = "jsonl" if arm == "adapter" else "tsv"
                    document[arm] = self.artifact(f"{arm}-{label}.{extension}", changed)
                    manifest_sha256 = self.write_json(self.manifest, document)
                    with self.assertRaisesRegex(ValueError, f"{arm} projection differs from the frozen ordered slot uses"):
                        self.verify(manifest_sha256=manifest_sha256)

    def test_independent_manifest_and_protected_pins_are_both_required(self):
        for key in ("manifest_sha256", "protected_sha256"):
            with self.subTest(pin=key), self.assertRaises(ValueError):
                self.verify(**{key: "0" * 64})

    def test_empty_inventories_and_empty_slots_in_an_unknown_chain_are_refused(self):
        empty = self.slot("empty", 0, [], 1, 1)
        for label, changes in (
            ("no events", {"events": [], "slots": [empty]}),
            ("no slots", {"slots": []}),
            ("unknown chain", {"slots": [{**empty, "chain_id": "missing-chain"}]}),
            ("only markers", {"slots": [empty]}),
        ):
            with self.subTest(label=label):
                document = {**deepcopy(self.document), **changes}
                self.write_projections(document, "empty-inventory")
                with self.assertRaises(ValueError):
                    self.verify(manifest_sha256=self.write_json(self.manifest, document))

    def test_cross_chain_reuse_of_a_source_requires_the_same_family_and_versioned_bytes(self):
        document = deepcopy(self.document)
        alias = {**document["events"][0], "chain_id": "other-chain", "event_id": "other-support"}
        document["events"].append(alias)
        self.verify(manifest_sha256=self.write_json(self.manifest, document))
        alternate_content = self.artifact("other-support.txt", b"Pressure changed unexpectedly")
        for field, value in (("family_id", "other-family"), ("content", alternate_content)):
            with self.subTest(field=field):
                forged = deepcopy(document)
                forged["events"][-1][field] = value
                with self.assertRaises(ValueError):
                    self.verify(manifest_sha256=self.write_json(self.manifest, forged))
