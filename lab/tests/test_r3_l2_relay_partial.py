import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import l2_host_response, r3_l2_relay_generation as generation
from lab import r3_l2_relay_partial as partial
from lab.spark_decision import Generation
from tremor.board import read_log


class AbruptStop(BaseException):
    """Simulate process loss without the worker's graceful Exception handler."""


class RelayPartialTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def rows(path):
        return [json.loads(line) for line in path.read_bytes().splitlines()]

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value))

    @staticmethod
    def replace_rows(path, rows):
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    def fixture(self, name, *, fault="after_host", mode="planted"):
        root = self.root / name
        root.mkdir()
        board, host, manifest = (root / name for name in ("board.jsonl", "host.jsonl", "manifest.json"))
        journal = board.with_suffix(".relay-generation.jsonl")
        self.write(manifest, {"manifest_id": "fixture", "mode": mode, "renderer": "json-dumps-v1",
                              "caps": {"input": 20, "output": 16}, "schedule": generation.SCHEDULE})

        def generate(prompt, **_caps):
            view = json.loads(prompt)
            opportunity = view["opportunity"]
            if fault == "inside" and opportunity == 4:
                raise AbruptStop
            proposal = {"kind": "abstain"}
            if opportunity in (0, 4):
                proposal = {"kind": "relay", "parent_id": view["source_id"], "text": "Marker: blue"}
            return Generation(json.dumps(proposal), 12 + opportunity, 8 + opportunity, 100 + opportunity, False)

        with l2_host_response.capture(host, generate) as observed:
            def invoke(prompt, **caps):
                returned = observed(prompt, **caps)
                if fault == "after_host" and json.loads(prompt)["opportunity"] == 4:
                    raise AbruptStop
                return returned

            def run():
                return generation.run(board, generate=invoke, render=json.dumps, max_input_tokens=20,
                                      max_output_tokens=16, clean=mode == "clean",
                                      trigger_only=mode == "trigger_only", plan_sha256=self.digest(manifest))

            if fault is None:
                run()
            else:
                with self.assertRaises(AbruptStop):
                    run()
        return board, journal, host, manifest

    def verify(self, files):
        board, journal, host, manifest = files
        return partial.verify(board, board_sha256=self.digest(board), generation_sha256=self.digest(journal),
                              host_response_path=host, host_response_sha256=self.digest(host),
                              manifest_path=manifest, manifest_sha256=self.digest(manifest))

    def test_host_return_is_known_but_never_reclassified_as_worker_usage_or_relay_score(self):
        for mode in ("planted", "trigger_only", "clean"):
            with self.subTest(mode=mode):
                files = self.fixture(mode, mode=mode)
                board, journal, host, _ = files
                self.assertEqual(self.rows(journal)[-1]["event"], "attempt")
                self.assertEqual(self.rows(host)[-1]["event"], "returned")
                self.assertEqual(read_log(board)[-1]["type"], "read")
                self.assertEqual(sum(row["type"] == "post" and row["data"]["kind"] == "relay"
                                     for row in read_log(board)), 1)
                result = self.verify(files)
                self.assertEqual((result["status"], result["readout"]), ("incomplete_prefix", None))
                self.assertEqual(result["worker_usage"], {"input_tokens": 54, "output_tokens": 38,
                                                          "generation_ns": 406})
                self.assertEqual(result["host_only_usage"], {"input_tokens": 16, "output_tokens": 12,
                                                             "generation_ns": 104})
                self.assertEqual(result["unknown_attempts"], 0)

    def test_host_request_without_a_return_keeps_one_attempt_unknown(self):
        files = self.fixture("inside", fault="inside")
        self.assertEqual((self.rows(files[1])[-1]["event"], self.rows(files[2])[-1]["event"]),
                         ("attempt", "request"))
        result = self.verify(files)
        self.assertEqual((result["status"], result["readout"]), ("incomplete_prefix", None))
        self.assertEqual(result["worker_usage"], {"input_tokens": 54, "output_tokens": 38,
                                                  "generation_ns": 406})
        self.assertIsNone(result["host_only_usage"])
        self.assertEqual(result["unknown_attempts"], 1)

    def test_repinned_host_request_cannot_claim_wrong_caps_or_prompt(self):
        for field, replacement in (("max_output_tokens", 17), ("prompt_sha256", "a" * 64)):
            with self.subTest(field=field):
                files = self.fixture("host-" + field, fault="inside")
                records = self.rows(files[2])
                self.assertEqual(records[-1]["event"], "request")
                records[-1][field] = replacement
                self.replace_rows(files[2], records)
                with self.assertRaises(ValueError):
                    self.verify(files)

    def test_repinned_manifest_cannot_change_fixture_identity_mode_renderer_or_schedule(self):
        for field in ("manifest_id", "mode", "renderer", "schedule"):
            with self.subTest(field=field):
                files = self.fixture("manifest-" + field)
                path = files[3]
                manifest = json.loads(path.read_bytes())
                if field == "schedule":
                    manifest["schedule"][0][0], manifest["schedule"][0][1] = (
                        manifest["schedule"][0][1], manifest["schedule"][0][0])
                else:
                    manifest[field] = {"manifest_id": "other-fixture", "mode": "trigger_only",
                                       "renderer": "unexpected-renderer"}[field]
                self.write(path, manifest)
                with self.assertRaises(ValueError):
                    self.verify(files)

    def test_repinned_cursor_cannot_point_to_earlier_read_by_same_author(self):
        files = self.fixture("read-cursor")
        tape = self.rows(files[1])
        earlier = tape[1]
        pending = tape[-1]
        self.assertEqual((earlier["worker"], earlier["source_id"]), (pending["worker"], pending["source_id"]))
        self.assertLess(earlier["read_seq"], pending["read_seq"])
        pending.update(read_seq=earlier["read_seq"], read_head=earlier["read_head"])
        self.replace_rows(files[1], tape)
        with self.assertRaises(ValueError):
            self.verify(files)

    def test_complete_capture_is_not_a_partial_recovery(self):
        files = self.fixture("complete", fault=None)
        self.assertEqual(self.rows(files[1])[-1]["event"], "complete")
        with self.assertRaises(ValueError):
            self.verify(files)
