# murmuration

Research prototype: can complex-systems ideas (adaptation, feedback, decay, shared state) make
coding-agent permissions, orchestration and memory better? **Status: exploratory. Nothing here
predicts real-world behaviour. No licence chosen yet (owner decision).**

## Track 1 — Permission replay ledger (built)

Question: when a human must approve agent tool calls, does *grow on need, decay on idle*
beat *promote repeated requests* on prompt count and standing exposure?

`ledger.py` parses Claude Code transcript JSONL into permission events and replays four policies
over the **same** event stream: `always_ask`, `static`, `promote_repeated`, `grow_decay`.
Invariants (tested): a denied call is never promoted; a ceiling (`--deny`) key never enters the
allowlist; replay is deterministic. Stdlib only, no installs, no network.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests          # 9 tests
PYTHONPATH=src python3 -m murmuration synth > /tmp/s.jsonl     # seeded fake transcript (illustration)
PYTHONPATH=src python3 -m murmuration report ~/.claude/projects --salt <secret> --deny Bash:rm
```
`--salt` hashes capability keys so the JSON is shareable. Output is counts only; prompt text and tool
output are never stored.

### Limits (read before citing anything)
- **Counterfactual.** Replay cannot know what the agent would do under a different decision. Claims
  are limited to prompt counts and exposure (idle allow-rule days), never task outcomes.
- **Prompt counts are an upper-bound proxy.** Transcripts do not say which approved calls were
  prompted originally (auto mode, allow rules), so every non-allowlisted call counts as a prompt.
- **Denial detection** is verified for one format (`Permission to use … has been denied`). The
  "user declined" pattern is unverified; override with `--deny-regex`.
- **"Workaround after denial"** is a proxy (same tool, different key within 3 calls).
- **Capability key** is coarse: tool name, or `Bash:<first token>`.
- **Corpus.** The only real data on the dev box was 155 events / 1 session — far below the ≥200
  event kill threshold, so *no real-data conclusion exists yet*. Run it on a larger local corpus.
  Synthetic results (invented usage) only show the mechanics.

Kill criteria (pre-stated): <200 real events; denials unreliable in transcripts; grow_decay within
noise of promote_repeated.

## Track 2 — Complex-systems research (in progress)
See `docs/research/`. Every citation carries a verified Y/N flag; unverified items are labelled.

## Safety and privacy
No credentials, tenant data or provider calls. Do not publish transcripts; share only salted
aggregates.
