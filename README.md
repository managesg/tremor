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
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m murmuration synth > /tmp/s.jsonl     # seeded fake transcript (illustration)
PYTHONPATH=src python3 -m murmuration report ~/.claude/projects --salt <secret> --deny Bash:rm
```
`--salt` hashes capability keys so the JSON is shareable. Output is counts only; prompt text and tool
output are never stored.

## Commands

`PYTHONPATH=src python3 -m murmuration <command> --help`. All commands print JSON (counts only, never
transcript or message content) except `synth`, which prints a fake transcript.

| Command | What it does |
|---|---|
| `report` | replay four permission policies over transcripts |
| `sweep` | H1 tau sweep: tau chosen on train sessions, scored on held-out sessions |
| `allowlist` | mine an allowlist on train sessions, score on test sessions |
| `hazard` | E1.2 reuse-gap fit, power law vs exponential |
| `tokens probe\|ledger` | token usage key names / per-session token ledger (`ledger` needs `--salt`) |
| `memlint` | provenance lint of a directory of memory records |
| `coupling` | E2.1 co-change pairs from git history |
| `manifest` | run manifest plus optional tree hash (`--root` feeds both the git SHA and the tree hash; symlinks under `--tree` are refused) |
| `prereg-check <file> --tree .. --root ..` | fail unless the tree still matches the prereg's `code_tree_hash:`; a blank hash is refused |
| `trap-gen`, `seq-gen` | generate the planted-wrong-note repo / E8.3 SQL sequence |
| `run` | one E8.3 episode; scripted backend only, `local_hf`/`claude` refused unless `--allow-backend` (claude is an unapproved stub) |
| `power-parse` | integrate nvidia-smi CSV power samples (GPU-only joules) |
| `synth` | seeded fake transcript (illustration only) |

`report`, `sweep`, `allowlist` and `hazard` print capability keys: they require `--salt`, or an explicit
`--unsafe-raw-keys` (output then not shareable).

**Freezing a prereg.** Commit first. Run the manifest command with the exact
source paths the protocol requires, then record its `tree_hash` in the
preregistration's `code_tree_hash:` line. Before each run, pass the same
root and paths to the check.

```bash
PYTHONPATH=src python3 -m murmuration manifest --root . --tree src train
PYTHONPATH=src python3 -m murmuration prereg-check prereg/H7.md --root . --tree src train
```

These examples cover `src` and `train`. For a new protocol that executes
bench code from `lab`, include `lab` in both commands or use the
protocol's explicit file manifest. The enclosing Git commit and the
selected source hash identify different parts of an archived or
locally modified checkout. To verify an archived hash calculated relative
to a single subtree, pass that directory as `--root` and `.` as `--tree`.

## Wave 1 status

Built: the commands above, stdlib only, with unit tests (`discover` passes). Verified: mechanics on
synthetic and generated data only; see `docs/reports/wave1-verification.md`. **No real-data H1
conclusion exists**: the one real corpus is far below the 200-event threshold, and nothing has been
run against a real model. Plan and open items: `docs/WORKPLAN.md`.

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

### TREMOR progress (offline tooling, as of 2026-11-27; local commits only)
TREMOR measures how well teams of AI agents do on tasks whose answers a program can check exactly. The
plan is written down and frozen before any paid or GPU run. **Only milestone M1 (a small GPU
calibration) is accepted: 1 of 10.** No agent has been run on the R5/R6 lines yet and the paid total is
USD 0.00 (hard cap USD 10 in code).

Built and tested offline (stdlib only; each module has tests and mutation checks, see
`docs/reports/tremor/REVIEW_ITEMS_ATTACK_EVIDENCE.md` for sha, test command and counts):
- **Money guard:** `src/murmuration/spend.py`, `ep1.py`: price-sheet pins, a hard USD 10 cap no argument can
  raise, refusal of a batch opened in two ledger files.
- **Gate and sealed inputs:** `lab/tremor_admission_gate.py`, `lab/tremor_sealed_inputs.py`,
  `lab/tremor_freeze_skeleton.py`: no run unless a freeze record and an admission record agree; one use
  per batch.
- **R6 task families** (`lab/r6_*`): exact formula and circuit-size tables, a predicate sandbox, F1 logic
  tasks, T1 definition-audit pairs, T2 permanent/Hamiltonian-cycle identity tasks (two independent
  implementations must agree before a label exists), T3 finite lemmas with a reviewed `rank_f2` primitive,
  Stage A scoring, scorecard and Holm decision.
- **Rehearsals:** an end-to-end gate rehearsal and an end-to-end R6 pipeline rehearsal, both offline.
- **Drafts waiting for named people** (nothing frozen or admitted): `docs/reports/tremor/` (M4 freeze
  records, M7 spend sheet, M10 settlement reconciliation, row 167 reveal checklist).

What is not done: Pilot 4 and EP-1 (key holder), any Inkling-2-Mini GPU run on the Spark (PC must place
the shared model slot; TREMOR has not contacted it), custodian-held sealed inputs, M3, M5-M10 admissions.
The VP != VNP paper (shared 2026-11-23) is used only as a source of finite test tasks; its proof is not
verified by us and nothing here supports any claim about P vs NP. Plan and checklist:
`docs/reports/TREMOR_GOAL_AND_PLAN_20261123.md`; handoff: `docs/reports/HANDOFF_TREMOR_20261126.md`.

## Safety and privacy
No credentials, tenant data or provider calls. Do not publish transcripts; share only salted
aggregates.
