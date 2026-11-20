# Review notes for `docs/PROPOSAL-SHARE.md` (2026-11-19)

Author: Fable 5.2 (planner). Checklist for the owner **before** anything is shared. Nothing was
sent, run, installed or committed. Sharing, licence and publication are still the owner's decision.

Length: 3,980 words counted as tokens containing a letter or digit; `wc -w` prints 4,203 because
it counts table pipes and rule dashes. If the 4,000 limit means `wc -w`, cut section 8 first.

## 1. Claims needing primary-source verification

| # | Claim in the draft | Section | Status today | What to do |
|---|---|---|---|---|
| 1 | Humans 13.6%, auto mode 89%, 1,053 staged testers | 2.2 | Confirmed in the 7 Aug 2026 announcement (`research/05a`, fetched and searched, not read line by line) | Re-open the page; note its 22 Oct update banner |
| 2 | 17% false negatives, n=52 | 2.2 | Confirmed, 25 Mar 2026 engineering post (`05a`) | Re-open |
| 3 | Bash deny rules bypassable (`/bin/rm`, `bash -c`) | 2.2 | Confirmed in the permissions docs (`05a`); pages undated | Re-open; docs change often |
| 4 | Allow rules "Permanently per repository and command"; no expiry | 2.2 | Wording confirmed; "no expiry" is by absence | Keep "we found no expiry setting" |
| 5 | "doctor prompt audit" not found | 2.2 | Not found in docs; only `/doctor`, `claude doctor` | Ask Lydia; do not say the command does not exist |
| 6 | Deny before classifier | 2.2 | Inferred from the decision-order list | Keep the hedge |
| 7 | 1,000 agents, 28.7 h, 60 statements, five tables, "toy experiment" | 2.1 | Confirmed on `claude.dev` (`research/10`); the domain was not confirmed as official; the guessed anthropic.com URL returned 404 | Find the official URL before citing |
| 8 | Table read and write counts, idle helpers | 2.1 | Slide-read by an assistant from screenshots | Check against the recording or post |
| 9 | CL-Bench scores (six models) | 2.1 | Slide-read; not found in text we read | Check the memory post |
| 10 | Wiki 13% to 48%, wiki plus search 54% to 61%, search 53% | 2.1 | Slide-read; `research/10` did not reach that part of the post. Only "53%" is spoken in the transcript | Read the rest of the post |
| 11 | CL-Bench abstract: "naive ICL outperforms systems dedicated to memory management" | 2.1 | Abstract opened (`research/10`) | Re-open arXiv 2606.05661; check the wording |
| 12 | Threshold reading; headroom shares 0.44 to 0.61 and 0.05 | 2.1 | Our arithmetic on slide-read values (`SCIENCE.md` 1.5) | Recompute once #9 is confirmed |
| 13 | OpenShell: policy fields, advisor off by default, opt-in auto-approval, no documented shrink | 2.3 | Confirmed on the pages opened; absence covers three pages | Open the manage-policies page |
| 14 | Managed Agents budgets and tool policies | 2.3 | Pages read in part (`research/07`) | Re-open |
| 15 | "Flows" page 404 | 2.3 | One URL tried | Ask CJ for the current name |
| 16 | Cost pie 67/18/12/3 | 2.4 | **Unconfirmed**; blog text gives only "9-18%" for output | Read the chart image or ask Diogo |
| 17 | Cache-read multipliers 0.1x then, 0.025x to 0.05x now; "two- to fourfold" | 2.4 | Pricing page read 19 Nov 2026 (`research/10`, `05a`) | Re-open on the day of sharing |
| 18 | No opened paper establishes log-N agent memory | 2.4 | Abstracts only (`research/10`) | Keep "no paper we opened" |
| 19 | "72% cache saving" | 8 | Not found in any written source. I could not determine which talk it came from | Leave as "not used", or delete the row |
| 20 | Lee and See 2004; Mayer, Davis and Schoorman | 2.3, 8 | Names reconstructed from garbled transcript text ("Lee and c2 1004", "Shorman"). Not opened | Confirm against CJ's slides |
| 21 | 93.7% cache reads in 42 local sessions; 1,079 events, 11 denials, 1 session | 6 | From `docs/PROPOSAL.md` and the local results report; not re-run | Decide whether to share figures from your own sessions at all |
| 22 | 85 tests green 20 times; 110 test functions | 6 | 85 from the verification reports; 110 counted by `grep "def test_"` today, **not run** | Run the suite before sharing |
| 23 | 22 MB per step leak; zero accuracy results | 6 | As relayed in `docs/PROPOSAL.md`; a smoke run was in progress | Update if the smoke finishes |
| 24 | Complex-systems attributions (Simon, Ostrom, Ashby, Arthur) | 3 | Second-hand; `SCIENCE.md` marks most as unverified | Acceptable as labels; do not quote them |

## 2. Quotes to confirm against recordings (all transcripts are machine-generated)

| Speaker | Quote in the draft | Transcript position | Note |
|---|---|---|---|
| Lance | "We didn't tell them to these tables" | 03:52:38 | Garbled; consider a paraphrase |
| Lance | "globally coherent and not redundant" | 03:56:47 | |
| Lance | "a poison memory was injected and it's stuck there. Dreaming can rescue that." | 04:03:00 to 04:03:05 | |
| Lydia | "if Claude gets it wrong once, can I take it back?" | none | From `research/12` only; I was given no primary transcript for this talk. **Highest risk quote** |
| CJ | "design for appropriate trust, not greater trust" | trust talk, bounding section | He attributes it to a 2004 paper |
| CJ | "signed by a human"; "grow or shrink based on evidence"; "hasn't actually used GitHub for two weeks" | policy section | |
| Diogo | "they're so inflexible in their design because of the tyranny of the KV cache" | 05:23:09 to 05:23:13 | |
| Diogo | "need to rediscover the same patterns of the codebase over and over"; "even naive routing doesn't work" | 05:23:52 to 05:23:59 | |
| Docs | "Permanently per repository and command"; "just 9-18% of the total bill" | written sources | Via `05a` and `research/10` |

CJ's answer to the audience question is paraphrased, not quoted. Check the paraphrase is fair:
he said the human decides whether to promote a repeated request and that flags should be surfaced
for review "in the most automated way possible".

## 3. Privacy scan of the draft

Command run on `docs/PROPOSAL-SHARE.md`: case-insensitive grep for the owner's first name, last
name and user name, the company and backend names, `/home/`, `.orca`, the repository's current
name, the proxy name, "tenant", "codex", and any `x@y` pattern. **Zero hits.**

Checked by reading:
- The CJ transcript labels the questioner by name. The draft says "an audience question".
- No gate IDs, budget caps, GPU-hour figures or approval status. One sentence in section 7 says
  model runs and publication need the owner's separate decision.
- No file paths, inside or outside the repository (only the command names `/doctor` and `/bin/rm`).
- Remaining items the owner may still want out: the model name used to draft (header); figures
  from the owner's own sessions (#21); "one user, one machine"; the outside-consult row in
  section 8; Harrison Stall is named as co-speaker although he is not an addressee.

## 4. What changed from `docs/PROPOSAL.md`, and why

| Change | Why |
|---|---|
| Added section 2, one part per speaker, with figures, status, gaps and a question | The owner's instruction; the internal proposal names the talks only in passing |
| Added the concept table (section 3) | The owner asked that complex-systems concepts be tested, not only cited |
| **Three proposed reinstatements, each marked "owner ruling pending":** scripted shared board (cut as H9/board), coupling-gate test on public git history (H2, deferred), scripted re-verify pass as a consolidation arm (dreaming arms cut) | Cheapest scripted form of each; no cut was reversed. The small-local-model part of H9 stays deferred. The H2 test needs public repositories fetched, which is its own approval |
| Requisite variety and lock-in rows added | In `SCIENCE.md`, absent from the internal proposal |
| Removed: approvals table, gate IDs, caps, USD ceilings, timeline, model-role table, routing order, "+5 from 5", the one-page pitch | Internal; replaced by "what we are and are not asking" |
| "Green" kept only as joules where measured | Matches the internal proposal's cut |
| Confidentiality table turned into a paragraph | Same content, shorter |
| Headline run size given as 240 runs; token and GPU caps omitted | Budget chatter |

## 5. What I could not do

- Verify any quote against a recording, or re-open any web source. All statuses are inherited
  from `research/05a`, `05b`, `10`, `11`, `12`.
- Read the second CJ talk. The brief says it is summarised in `research/07` and `10`; I found
  no summary of it there (file 07 covers platform features; "Flows" returned 404). The draft
  says we have only a topic list.
- Read everything in full. Read in full: `PROPOSAL.md`, `PRINCIPLES.md`, `research/05a`, `05b`,
  `10`, `11`, `12`, the CJ and Lance transcripts. Read in part: `doc-reconciliation.md` (sections
  1 to 4), `gpt-consult.md` (sections 1 to 3), `adversarial-review-2.md` (sections 0 and 3),
  `PLAN.md` (header, H1 to H5, H8, H9, 6.4), `SCIENCE.md` (1.1, 1.2, 1.5, 3, 7.2a, 7.4),
  `ARCHITECTURE.md` (1, 2), `VISION.md` (concept table), the Diogo transcript (05:22:37 to
  05:24:45 only).
- Run the tests, or check that the code matches the statuses in section 6 of the draft beyond
  reading four module docstrings.
- Check the name "Sortie". The draft says so.
- Discrepancy left open: Lance says the box size on the Pokemon slide shows the number of
  memory files; `research/11` says characters. The draft no longer uses that figure.
