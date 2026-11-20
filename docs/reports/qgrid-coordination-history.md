# QGrid coordination history (aggregate counts only)

INTERNAL USE ONLY: the source repo has no licence file. No file contents, names, titles or comment text are reproduced. Authors are A1..A5 by first-seen order.

## Method and what was denied

- `gh api` calls: the permission layer DENIED every `gh` call (0 of 300 used). No PR, issue or issue-comment data was obtained. Items that need it are marked NOT DERIVABLE.
- Source used instead: `git clone --bare --filter=blob:none` into the scratchpad (not the repo), then `git log --all` and `git show <sha>:STATUS.md` (call G1 = log, G2 = STATUS.md revisions). `git ls-remote` (G0) confirmed the remote.
- Note: AGENTS.md's gh example names a different repo owner than the brief; counts below are for the managesg repo as cloned.
- Lane ownership by top-level folder only, per AGENTS.md: L1 = site/, grid/; L2 = data/; L3 = quantum/, lean/; shared = everything else (contracts/, fixtures/, pipeline.py, scripts/, docs, root files).

## Figures

| Figure | Value | Source |
|---|---|---|
| Commits, all refs | 168 (74 merge, 94 non-merge); 65 refs | G1 |
| Authors | 5 (A1..A5) | G1 |
| Span | one calendar day (2026-11-08) for 165 commits, 3 on 2026-11-09; first to last about 6 h | G1 |
| Non-merge commits touching each lane | shared 72, L2 25, L1 8, L3 5 (a commit can touch several) | G1 |
| Commits by author | A2 104, A1 26, A5 20, A4 13, A3 5 | G1 |
| PR merge commits | 53; highest PR number 60 | G1 |
| Other merge commits (non-PR) | 21 | G1 |
| Cross-lane commits | 12 of 94 non-merge (12.8%); home lane = author's most-touched non-shared lane; A1 has none (shared-only); A2 touches L1/L2/L3 and is likely an integrator | G1 |
| Commits touching contracts/ or fixtures/ | 3 | G1 |
| Of those, without a prior [CONTRACT] comment | NOT DERIVABLE (needs issue comments) | gh denied |
| Revert commits | 1 | G1 |
| Merge conflicts | 0 mentioned in commit subjects; true count NOT DERIVABLE from history | G1 |
| PR-level lane violation rate | NOT DERIVABLE; commit-level proxy above | gh denied |
| PR open-to-merge median and quartiles | NOT DERIVABLE | gh denied |
| Review comments per PR | NOT DERIVABLE | gh denied |
| STATUS.md revisions | 3, all on 2026-11-08 | G2 |
| Checkbox items at the 3 revisions | done 13/17/23, open 11/9/10 (earliest to latest) | G2 |
| Stages labelled FIXTURE | 0 uppercase labels in any revision; 2 case-insensitive "fixture" mentions in each revision, so the board does not record per-stage FIXTURE labels | G2 |
| Adversarial-review section | absent in revisions 1 and 2, present in revision 3 with 7 items: 4 checked, 3 open (57% fixed) | G2 |

Commits per day per lane: 2026-11-08 shared 69, L2 25, L1 8, L3 5; 2026-11-09 shared 3.

## What this could inform

- Claim-before-work: nothing (no claim data without issue comments).
- One-writer-per-folder: partially. The commit-level cross-lane rate (12.8%) and the integrator-like pattern show how often a lane rule is crossed in practice.
- Contract-change-before-edit: only the base rate of contract/fixture edits (3 commits); compliance not testable.
- Verify-before-done: weakly, via the adversarial section's fix rate (4 of 7) at one point in time.
- Honest labels: not testable; the FIXTURE label does not appear on the board.

## Threats to validity

One project; about six hours of hackathon time pressure; mixed human and agent authors; no controls or counterfactual; the lane-by-author mapping is inferred; squash or merge style can hide per-PR touches; three STATUS.md snapshots are too few for a trend; timezone offsets differ between commit and status stamps.

## Status

This is a descriptive history. Nothing here is a test of our hypotheses.
