import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from murmuration import ledger, synth  # noqa: E402

D = ledger.DAY


def ev(day, key, denied=False, tool=None, session="s"):
    return ledger.Event(session, day * D, tool or key.split(":")[0], key, denied)


class ParseTests(unittest.TestCase):
    def test_denial_detected_from_real_format(self):
        lines = [
            {"sessionId": "a", "timestamp": "2026-01-01T00:00:00Z", "message": {"content": [
                {"type": "tool_use", "id": "1", "name": "Bash", "input": {"command": "tail -1"}}]}},
            {"sessionId": "a", "timestamp": "2026-01-01T00:00:01Z", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "1", "is_error": True,
                 "content": "Permission to use Bash with command tail -1 has been denied."}]}},
            {"sessionId": "a", "timestamp": "2026-01-01T00:00:02Z", "message": {"content": [
                {"type": "tool_use", "id": "2", "name": "Bash", "input": {"command": "ls"}}]}},
            {"sessionId": "a", "timestamp": "2026-01-01T00:00:03Z", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "2", "is_error": True, "content": "Exit code 1\nboom"}]}},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.jsonl")
            open(p, "w").write("\n".join(map(json.dumps, lines)))
            out = ledger.parse([d])
        self.assertEqual([(e.key, e.denied) for e in out], [("Bash:tail", True), ("Bash:ls", False)])

    def test_salt_hides_keys_consistently(self):
        self.assertEqual(ledger.cap_key("Bash", {"command": "rm -rf x"}, "s"), ledger.salted("Bash:rm", "s"))
        self.assertNotIn("rm", ledger.cap_key("Bash", {"command": "rm x"}, "s"))


class ReplayTests(unittest.TestCase):
    def test_always_ask_prompts_every_event(self):
        e = [ev(0, "Read"), ev(1, "Read"), ev(2, "Read")]
        self.assertEqual(ledger.replay(e, "always_ask")["prompts"], 3)

    def test_promote_repeated_hand_count(self):
        e = [ev(i, "Read") for i in range(6)]  # approvals 1..3 prompt, promoted at 3rd, then free
        r = ledger.replay(e, "promote_repeated", promote_after=3)
        self.assertEqual((r["prompts"], r["promotions"], r["final_rules"]), (3, 1, 1))

    def test_decay_reprompts_after_idle_and_caps_exposure(self):
        e = [ev(0, "Read"), ev(1, "Read"), ev(2, "Read"), ev(100, "Read"), ev(101, "Read")]
        pr = ledger.replay(e, "promote_repeated", tau_days=14, promote_after=3)
        gd = ledger.replay(e, "grow_decay", tau_days=14, promote_after=3)
        self.assertEqual(pr["prompts"], 3)
        self.assertEqual(gd["decays"], 1)
        self.assertEqual(gd["reprompts_after_decay"], 1)
        self.assertEqual(gd["prompts"], 4)  # decay costs one extra prompt here...
        # exposure = idle days a held rule sat unused: 98+1 for promote_repeated, 14+1 for grow_decay
        self.assertAlmostEqual(pr["exposure_idle_days"], 99.0)
        self.assertAlmostEqual(gd["exposure_idle_days"], 15.0)

    def test_denied_never_promoted_and_ceiling_never_allowed(self):
        e = [ev(i, "Bash:rm", denied=True) for i in range(5)] + [ev(i, "Bash:curl") for i in range(5)]
        for p in ("promote_repeated", "grow_decay"):
            r = ledger.replay(e, p, promote_after=2, deny_keys={"Bash:curl"})
            self.assertEqual(r["promotions"], 0)
            self.assertEqual(r["final_rules"], 0)
            self.assertEqual(r["prompts"], 10)

    def test_deterministic_and_empty(self):
        self.assertEqual(ledger.replay([], "grow_decay")["prompts"], 0)
        a = synth.generate(3)
        self.assertEqual(a, synth.generate(3))
        self.assertNotEqual(a, synth.generate(4))

    def test_classify_denials(self):
        e = [ev(0, "Bash:rm", True), ev(0.1, "Bash:rm"), ev(1, "Bash:rm", True), ev(1.1, "Bash:ls"),
             ev(2, "Bash:rm", True), ev(2.1, "Read")]
        self.assertEqual(ledger.classify_denials(e, window=1), {"retried": 1, "workaround": 1, "moved_on": 1})


def _stream(test_events):
    # 10 sessions: s00..s06 train (days 0-69), s07..s09 test (days 70-99)
    base = [ev(d, "Grep", session="s%02d" % (d // 10)) for d in range(70)]
    base += [ev(d, "Read", session="s00") for d in (0, 1, 2)]  # promoted, then idle ~67 days in train
    return sorted(base + test_events, key=lambda e: e.t)


class HoldoutTests(unittest.TestCase):
    def test_counts_and_split_never_share_a_session(self):
        e = _stream([ev(d, "Grep", denied=d == 71, session="s%02d" % (d // 10)) for d in range(70, 100)])
        self.assertEqual(ledger.counts(e), {"events": 103, "sessions": 10, "denials": 1})
        tr, te = ledger.split_sessions(e, 0.7)
        self.assertEqual((len({x.session for x in tr}), len({x.session for x in te})), (7, 3))
        self.assertFalse({x.session for x in tr} & {x.session for x in te})
        self.assertLess(max(x.t for x in tr), min(x.t for x in te))

    def test_tau_chosen_on_train_only_poisoned_test_half(self):
        clean = _stream([ev(d, "Grep", session="s%02d" % (d // 10)) for d in range(70, 100)])
        poison = _stream([ev(d, "Read", session="s%02d" % (d // 10)) for d in (70, 71, 72)]
                         + [ev(85, "Grep", session="s08")]  # keeps 10 sessions so the 7/3 split matches
                         + [ev(d, "Bash:rm", denied=True, session="s09") for d in range(90, 100)])
        a, b = ledger.tau_sweep(clean), ledger.tau_sweep(poison)
        self.assertEqual(a["chosen_tau"], 1)  # train half alone: fixture is meaningful
        self.assertEqual(a["chosen_tau"], b["chosen_tau"])
        self.assertEqual(a["rows"]["train"], b["rows"]["train"])
        self.assertNotEqual(a["rows"]["test"], b["rows"]["test"])  # the poison did reach the test half

    def test_mine_allowlist_scores_late_window(self):
        e = [ev(0, "Read", session="a"), ev(1, "Read", session="a"), ev(2, "Read", session="a"),
             ev(3, "Bash:ls", session="a"), ev(4, "Bash:rm", True, session="a"),
             ev(10, "Read", session="b"), ev(11, "Bash:rm", True, session="b")]
        r = ledger.mine_allowlist(e, 0.5, promote_after=3, deny_keys={"Bash:rm"})
        self.assertEqual(r["allowlist"], ["Read"])
        self.assertEqual((r["false_deny"], r["excess_grant"], r["covered"]), (0, 0, 1))
        self.assertEqual(ledger.mine_allowlist(e, 0.5, promote_after=3)["false_deny"], 0)  # rm never reached 3 approvals

    def test_cli_report_applies_deny_keys_to_the_allowlist(self):
        # Row-155 review defect 2: cli_report dropped deny_keys for the mined allowlist.
        e = [ev(d, "Bash:rm", session="a") for d in range(10)] + [ev(20, "Read", session="b")]
        r = ledger.cli_report(e, train_frac=0.5, deny_keys=("Bash:rm",))
        self.assertNotIn("Bash:rm", r["allowlist"]["allowlist"])


class CliTests(unittest.TestCase):
    def test_synth_pipeline_end_to_end(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), "..", "src"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.jsonl")
            open(p, "w").write(subprocess.run([sys.executable, "-m", "murmuration", "synth"], env=env,
                                              capture_output=True, text=True, check=True).stdout)
            out = subprocess.run([sys.executable, "-m", "murmuration", "report", p, "--deny", "Bash:rm", "--unsafe-raw-keys"],
                                 env=env, capture_output=True, text=True, check=True).stdout
        rep = json.loads(out)
        names = [x["policy"] for x in rep["policies"]]
        self.assertEqual(names, ["always_ask", "static", "promote_repeated", "grow_decay"])
        self.assertGreater(rep["n_events"], 1000)


class TauRowNullTest(unittest.TestCase):
    def test_zero_denominators_are_none_and_never_meet_bar(self):
        row = ledger._tau_row([], 14, 3, ())
        self.assertIsNone(row["exposure_saving"])
        self.assertIsNone(row["extra_prompts"])
        self.assertFalse(row["meets_bar"])
        self.assertEqual(row["prompts"], {"promote_repeated": 0, "grow_decay": 0})

    def test_defined_row_carries_numerators(self):
        ev = [ledger.Event("s", d * ledger.DAY, "Read", "Read", False) for d in (0, 1, 2, 3, 40)]
        row = ledger._tau_row(ev, 7, 3, ())
        self.assertIsNotNone(row["exposure_saving"])
        self.assertIn("promote_repeated", row["idle_days"])
        self.assertGreater(row["prompts"]["promote_repeated"], 0)


if __name__ == "__main__":
    unittest.main()
