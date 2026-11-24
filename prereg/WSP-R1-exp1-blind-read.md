# Pre-registration: WSP-R1, blind cross-model replication of the weight-reading Experiment 1

**Status: FROZEN before any reader call** (committed with `lab/wsp_exp1_blind.py`). Owner request 2026-11-24: add "Sparks of Weight-Space Programming" (Takehi, Teoh, Zhang, Khattab, MIT, 2 Nov 2026) to TREMOR research and testing. This is a research row outside milestones M1 to M10. It is not milestone progress. It uses no GPU, install, network fetch or spend beyond the subagent calls counted below.

## Question

From the raw weights of a small PPO policy, with no tools and no forward pass, can a Claude model name the game the network was trained on, as GPT-6 Astra did in the post (4/4)? And does it fail when the spatial structure of the weights is destroyed?

## Inputs (pinned)

- **Source:** the released logs at `data/lm_understand-logs`, commit `4d09ba6` (2026-10-29), from `exp1_which_game/runs/<game>/prompt.txt`.
  - The scripts are MIT-licensed and the logs and networks CC BY 4.0.
  - The clone is older than the post's 12 Nov addendum. Exp 1 does not depend on that addendum, so the clone is not refetched.
- **Checks already run:**
  - The four prompts share one identical text before the weights (sha256 prefix `5980d0e18a05`).
  - Each weight block equals `networks/<id>_actor.txt` byte for byte.
- **Arms**, built by `python3 -I -B lab/wsp_exp1_blind.py build --out runs/wsp-r1-exp1.fhCR1a`:
  - **Real:** the four released prompts, unchanged.
  - **Shuffled control:** the same prompt with values permuted within each tensor (W1, b1, W2, b2, W3, b3). The seed is `20261124`. Headers, shapes, value multiset and formatting are kept; spatial and unit structure is destroyed.
  - The 8 items are in a random order under neutral names (`item1` to `item8`). The key is `runs/wsp-r1-exp1.fhCR1a/sealed-key.json`.
- **Item sha256:**
  - item1 `2bf48447…`
  - item2 `8be91eb0…`
  - item3 `5737c8f5…`
  - item4 `76f30db2…`
  - item5 `56eed644…`
  - item6 `1b143ac2…`
  - item7 `1c75e66a…`
  - item8 `ba1d97cf…`

## Reader

- **Model and runs:** Claude Opus 5.5, as a fresh `general-purpose` subagent (never `fork`). One call per item, 8 calls in total, effort at default (the original used Codex `high`).
- **Access:** each reader gets only its item's path, in a folder holding nothing else, and the instruction to use only the Read tool on that path, in chunks.
- **Blinding:** the brief names no game, no paper, no blog, and neither MinAtar nor Atari.
- **Audit:** the subagent's `tool_uses` count. A run counts only if every tool use was a Read of its own file. The count is the only audit available, because transcripts are not read. This is weaker than the authors' per-event `tool_free` audit, and is recorded as such.

## Scoring (fixed now)

`python3 -I -B lab/wsp_exp1_blind.py score --out <dir>`. The answer's first `Game:` line is mapped by the keyword table in the script (Frogger and road crossing count as Freeway, as in the original). A line that names two games counts as wrong. An independent reviewer then checks the grading and the audit.

## Decision rule

- **Real arm:** report k/4 correct. With n = 4 this is anecdotal, like the original's one run per game, and supports no rate claim.
- **Shuffled arm:** if 2 or more of the 4 controls are graded correct, the real-arm result is VOID. Chance is about 1/4 among the four games, and lower with open answers, so 2 or more points to leakage or a prompt prior.
- **Stop rule:** 8 calls, no reruns or extra calls. A failed or missing answer counts as wrong.

## Budget (Safety rule 8)

This is a named live-eval batch, WSP-R1, with no numeric owner ceiling, so the default applies: USD 5 total and at most 9 calls. It uses 8. Calls run on the subscription with no provider-enforced cap, and the cost is unknown, not zero.

## Result (recorded 2026-11-24, after scoring; the sections above are unchanged)

- **Scorer:** `python3 -I -B lab/wsp_exp1_blind.py score --out runs/wsp-r1-exp1.fhCR1a` gave **real 4/4** and **shuffled 1/4**, exit 0. Run-folder `EVIDENCE.sha256` is `5dfe8b8d…` (18 files).
- **Decision: NOT VOID.** Only 1 shuffled item was correct, below the threshold of 2. The real-arm 4/4 stands, and is anecdotal at n = 4.
- **Answers:**

  | Arm | Game | Reader's answer | Confidence |
  |---|---|---|---|
  | Real | Breakout | Breakout | 85% |
  | Real | Pong | Pong (single-player) | 70% |
  | Real | Pac-Man | Pac-Man | 75% |
  | Real | Freeway | Frogger | 70% |
  | Shuffled | Pac-Man | Pac-Man-style (the hit) | 20% |
  | Shuffled | Pong | Pac-Man / Snake / Asterix | 15% |
  | Shuffled | Breakout | Snake-like | 10% |
  | Shuffled | Freeway | Catch / Breakout-like | 15% |

- **What the readers saw:** on shuffled weights, all four said the first layer looked like noise. Their confidence was 10–20%, against 70–85% on real weights.
- **Audit:** every reader made exactly 6 tool uses, the six 100-line Reads its brief asked for. The count is the only audit available.
- **Independent check (Opus reviewer): ACCEPT.**
  - Checksums pass.
  - A deterministic rebuild gives byte-identical items and key (this lane rechecked all 8 items with `cmp`).
  - Grading by hand agrees with the scorer on whether each answer is correct.
  - The script was not changed after the freeze.
- **Reviewer's caveats:**
  - The single shuffled hit is probably a "Pac-Man-like grid" prompt prior, not reading.
  - `runs/` is git-ignored, so custody rests on `EVIDENCE.sha256`.
  - Reader isolation rests on the brief and the tool count.
- **Batch:** closed at 8 calls under the rule 8 default ceiling, with no reruns.
