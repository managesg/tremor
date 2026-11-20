# murmuration: work plan

2026-11-19, Opus 5.5 (orchestrator). Plan only; nothing below has been run. `PRINCIPLES.md` and
`PLAN.md` govern the science; this file governs build order, roles and stops. "6.2" etc. = PLAN.

## 1. Approval scope

Parent's reading, verbatim (the ceiling of this plan):

> APPROVED, within the documented scopes and caps in PLAN.md section 6.2 and the last report: G0 first LOCAL commit (no push, no remote); E8.1 read token-usage counts from local transcripts (counts only, salted, no content); all zero-cost build work (E1.0 already fixed; E1.1-E1.3 on local traces; hazard.py; coupling.py; memlint.py; trapbench generator+scorer; stats.py; manifest.py; E8.1 token-class ledger; tests); G2a pull of ONE NVIDIA PyTorch container image after the tag is verified to exist (docker manifest inspect, read-only) and disk/memory headroom is checked; G3(i) weights for Qwen/Qwen3.5-0.8B plus the released edited checkpoint ONLY after the exact HF IDs and licences are confirmed via the Hugging Face API/pages (record evidence); G9 clone github.com/RikiyaT/lm_understand-logs and run T7 arms 0 and A-D (inference only, 12 GPU-hour cap, abort if free memory < 10 GiB); G5 caps for E8.3 (8 GPU-hours), E8.2 (16), E8.4 (16, conditional); Claude-side batches staged with a smoke test first and a hard USD ceiling per batch (C0 smoke USD 5; total ceiling USD 185 as in PLAN; the owner has not given a C0 call number, so use the PLAN default of 9 calls for smoke and STOP to ask before exceeding). NOT APPROVED (must stop and ask): G1 (cloning up to 20 public repos), G2b Unsloth packages, any other weights, G4 serving port, G6 LoRA training, any push/PR/remote/publication/contacting the Claude Code team (G8), any spend beyond the stated ceilings, touching shared endpoints (spark-vllm, ports 8010/8080), any work in /home/adelmar/SeaBridgeAI/manageesg-backend or manageesg-frontend. Also still open: what the owner meant by '+5 from 5' (do not guess), who creates the signing key (owner), and the owner must confirm model licences (we only collect evidence).

Reading note (2026-11-19, not part of the quote): "total ceiling USD 185 as in PLAN" is PLAN
4.3's proposal total including the conditional C6, not an approved ceiling. Approved Claude
spend is C0 only (USD 5, 9 requests); every later batch needs its own approval (PLAN 4.3, 6.2
G7). Later owner decisions on 2026-11-19 (H8 exploratory; T7 12-point gate; E9 in principle,
13 GPU-hours) are in PLAN 6.4 with the review's recommended cuts, none applied.

Where 6.2 or the repo Safety rule is narrower, the narrower rule wins:

| Item | Status | Stop and ask when |
|---|---|---|
| G0 | Approved: one local commit | a second commit (freezes use content hashes, section 5); any remote |
| Wave 1 build | Approved | a dependency, install, or file outside the task's list |
| E1.1-E1.3, E8.1 on `~/.claude/projects` | Approved: salted counts | message text would be read |
| G2a + `pip install transformers` in a derived image | Approved after preflight | tag missing; NGC login; any other package (`math-verify`, IFEval deps, vLLM) |
| G3(i) | Evidence approved; download after the owner names the cache dir (6.2) and confirms licence (3.2) | ID missing, gated, or licence not Apache-2.0/MIT |
| G9 clone, datasets, T7 staged (stage 1 B, A, 0; stage 2 C, D, D-null past the 12-point gate) | Approved, 12 GPU-h. Stage 2, arm 0, arm D, LoRA: RECOMMENDED CUT, awaiting owner (PLAN 6.4) | dataset licence unclear; projection above cap; watchdog kill cause still unknown |
| G11 E9 | Approved in principle: 13 GPU-h, USD 0, downloads at most 20 GB (parent's design choice). E9-0 kept; E9-1, E9-2 RECOMMENDED CUT, awaiting owner (PLAN 6.4) | before any E9-1 or E9-2 GPU time |
| E8.3 / E8.2 / E8.4 | Caps approved, **not runnable** | E8.3 subject is G3(ii) (not approved; needs G4 or in-process); E8.2 needs E2.2 tasks (G1 or unchecked CooperBench licence); E8.4 needs E3.3 |
| C0 | Approved: USD 5, 9 requests | >9 requests; 4.4 isolation needs a Claude Code install plus firewall; billing route without API usage fields |
| C1, C2, C4, C5, C6 | **Ask after C0 report** | 6.2 G7 "No second batch without a new approval"; Safety rule 8 |
| G1, G2b, G3(ii-iv), G4, G6, G8, G10 | Blocked | owner |
| spark-vllm, 8010/8080, manageesg-*, deletion | Never | n/a |

## 2. Task DAG

**Wave 0, W0-1 (orchestrator): baseline and G0.**
1. `PYTHONPATH=src python3 -m unittest discover -s tests -v` must print OK with 9 tests. That count is the README's claim, not yet run.
2. Add `runs/`, `data/` and `.salt` to `.gitignore`.
3. Grep the staged files for secrets (`sk-`, `AKIA`, `PRIVATE KEY`, `token=`).
4. Stage the paths by name and commit locally with the session's `Co-Authored-By` trailer, never with `--no-verify`.

Acceptance: `git log --oneline | wc -l` prints 1 and `git status --short` prints nothing.

**Wave 1: zero-cost build, run in parallel.**
- Builder: Sonnet 5.5 (high effort). Verifier: Opus 5.5 with a fresh context and the brief in section 4.
- Standard library only: no network, no GPU.
- A builder owns only its listed files plus `tests/test_<module>.py`. Unlisted paths are under `src/murmuration/`.
- Acceptance: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_<module>.py' -v` passes and covers the listed checks.
- Token estimate (a Fermi guess, recorded per task): S, at most 150 lines, about 0.2M tokens; M, about 0.4M.

| ID | Goal (ref) | Files | Interface | Tests must cover | Size, after |
|---|---|---|---|---|---|
| W1-01 | manifest (5.1) | `manifest.py` | `tree_hash(paths)`; `build(config, seed)` with git SHA, config hash, versions, price-sheet source | stable hash; a one-byte edit changes it; missing value null, not 0 | S, W0 |
| W1-02 | stats (2, 5.4) | `stats.py` | `paired_bootstrap(rows, cluster, metric, n, seed)`; `holm`; `all_seeds_rate`; `check_prereg` | Holm known answer; resamples by cluster; seeded determinism; hash mismatch raises | M, 01 |
| W1-03 | E1.1, E1.3 (T1) | `ledger.py` (additions), `tests/test_ledger.py` | `counts`; `split_sessions(ev, 0.7)` by time; `tau_sweep`; `mine_allowlist` | old 9 tests; no session in both halves; tau picked on train only (poisoned-test fixture) | M, W0 |
| W1-04 | E1.2 | `hazard.py` | `gaps`; `fit -> {alpha, rate, llr, p, n}` | seeded exponent within ±10%; exponential data favours exponential | S, W0 |
| W1-05 | E8.1 | `tokens.py` | `probe` (key names and counts only); `ledger(paths, salt)`: 4 classes, cache-hit, subagent cold start, reads per write | canary text in a message never reaches output | M, W0 |
| W1-06 | memlint (5.2) | `memlint.py` | `lint(rec, root)`; `lint_dir` -> counts | no source rejected; dangling pointer; secret canary; size cap | S, W0 |
| W1-07 | trapbench traps (T3) | `trapbench/__init__.py`, `trapbench/traps.py` | `gen(seed, family, out)`; pure `score` | byte-identical per seed; scripted wrong-note follower hits canary | M, W0 |
| W1-08 | E8.3 sequence (6.3 #12) | `trapbench/sqlseq.py` | `gen` -> SQLite DB + 40 questions; `score` | byte-identical; family-split hash check; scripted oracle beats scripted stateless | M, 07 |
| W1-09 | T7 scripts, power (6.3 #10) | `train/t7_arms.py`, `train/t7_edit.py`, `train/power.py`, `tests/test_t7_pure.py` | `power.sample -> {joules_gpu, seconds, idle_fraction, baseline_w}`; `t7_arms.run(arm, problems, cap, out)` | torch-free parts only: nvidia-smi parsing, energy integration, accuracy by truncation at 2k/8k | M, W0 |
| W1-10 | runner (5.2) | `runner.py` | `run(task, arm, seed, backend)`; backends `scripted`, `local_hf` (lazy import, in-process) | scripted backend runs a W1-08 sequence; `local_hf` on the host fails cleanly | M, 08 |
| W1-11 | E2.1 | `coupling.py` | `coupling(repo, before_sha)` | temp-repo fixture; commits after the cutoff ignored | S, W0 |
| W1-12 | prereg H1, H7, H8, E8.1 | `prereg/*.md` | SCIENCE 6 template; `code_tree_hash:` blank | Fable drafts, Opus checks every number against 1.2 and T8; 4 files contain `code_tree_hash` | S, 01 |
| W1-13 | CLI (5.3) | `__main__.py`, `README.md` | subcommands for 01-11 | full `discover` OK; `<sub> --help` exits 0 | S, all |

**Wave 2: approved gated work, in order.** Described, not run. Containers: `--rm --gpus all --memory 60g`, no `-p`, `--network none` except downloads; `data/ runs/ train/` read-write, `src/ tests/` read-only.

1. **E1.**
   1. Salt into `runs/.salt` (mode 600, never printed).
   2. Fewer than 200 events or 30 sessions: report "H1 precondition not met: untestable on this corpus, not refuted" and stop.
   3. Else freeze H1, run E1.1-E1.3, salted summary to `docs/reports/`.
2. **E8.1.**
   1. `tokens probe`; under 30 sessions with usage fields: counts only.
   2. Else freeze E8.1, run the ledger; record the price sheet URL and date (unreadable: USD null).
3. **G2a.**
   1. Preflight: `docker manifest inspect nvcr.io/nvidia/pytorch:25.11-py3` exits 0 (401 = NGC login: stop); 100 GiB disk and 20 GiB MemAvailable free.
   2. `docker pull`; build `murmuration-t7:local` adding only pinned `transformers`; record the digest.
4. **Container smoke.** T7 scripts and runner on a tiny random-init model (no download); base sha256 unchanged after the edit.
5. **G9.**
   1. `gh api repos/RikiyaT/lm_understand-logs --jq .size` under 5 GB; `git clone --depth 1` into `data/`.
   2. Read `code/mathqa.py`, `code/evaluate.py`, requirements; any package beyond image + transformers: **ask** (`math-verify` expected).
   3. Take the edited-checkpoint ID from the README, never hardcoded.
6. **G3(i).**
   1. HF API JSON and LICENSE for both IDs (revision, licence, sizes) into `docs/reports/G3i-evidence.md`.
   2. Ask the owner: cache directory (proposed `data/hf/`) and licence confirmation.
   3. After yes: download the pinned revision, `chmod -R a-w`, sha256 manifests.
7. **Datasets** (MATH-500, MMLU-Pro subset, IFEval, practice set). Record each licence first. Stop if a licence is unclear or the IFEval checker needs packages.
8. **T7 smoke.** Blocked: both smoke arms were killed by the 10 GiB watchdog, cause unknown; find the cause first.
   1. `t7_samples.smoke_ids` (MATH-500 items outside the main set), arms 0 and B: tokens/s, watts, peak memory only. Never choose a setting on them.
   2. Arm C's r is chosen on 20 seeded `math_train.jsonl` practice problems (`prereg/H7.md` 6), and only if stage 2 runs.
   3. Projection above the 12 GPU-h remaining: **ask** (vLLM is separate). Never shrink n.
9. **T7 main, staged (`prereg/H7.md` 6, 12).**
   Freeze H7. Stage 1: arms B, A, then 0 on the 100 seeded problems; read the 12-point gate once. Stage 2 (C, D, D-null, off-target) only if the gate passes. Per-problem JSONL so a stop leaves a valid partial result. Stage 2, arm 0, arm D: RECOMMENDED CUT, awaiting owner (PLAN 6.4).
10. **E8.3.** Harness and H8 prereg only; 0.8B as subject goes to Fable (D1), then the owner (the 30% stateless floor makes it likely uninformative). E8.2, E8.4: nothing.
11. **C0 preflight only.** Ask unless all hold: a billing route returning usage fields (not the 20150 proxy or a subscription); 4.4 isolation; a 9-request counter checking USD 5 before each call. The runner's Claude backend waits for the yes.

**Wave 3: waiting on the owner.** G1 then E2.x and E8.2; G3(ii) plus G4 or in-process, then E8.3 and H6; G3(iii) plus G5, then E3.3, E3.4, E8.4; G2b and G6 if H7 survives; C1-C6; G8; G10.

## 3. Roles

| Role | Model | Does | Never |
|---|---|---|---|
| Orchestrator, verifier | Opus 5.5 | dispatch, gates, Wave 2, adversarial review, G0 | builds unless escalated |
| Builder | Sonnet 5.5 high | one W1 task, its files | commit, push, install, other files |
| Consultant | Fable 5.2 | prereg drafts; D1 E8.3 subject; D2 precondition-kill readings (E1, E8.1); D3 arm C overlaps the published presence penalty 1.5 (file 08), and arm D's "loop" token definition; PLAN/PRINCIPLES contradictions; tasks after two failed attempts | experiments, bulk |
| Bulk | Haiku 5.5 | results-to-table moves no script can do | judging |

**Escalation:** two failed acceptances move a task to Opus; Fable's design answers go to `docs/reports/decisions.md`, and the owner is asked if one changes a gate; subagents never commit, push or dispatch.

## 4. Verification protocol
1. The orchestrator reruns the acceptance command and quotes its output in the same turn. No command result, no "done".
2. An Opus verifier gets the diff, the task row and the pstack `interrogate` brief, never the builder's summary. It tries to refute the work. Targets: hidden network or writes, untested invariants, missing units, null recorded as 0, content leaks.
3. `git diff --stat` touches only the task's files.
4. Evidence goes to `docs/reports/workplan/<ID>.md`: the command, its output, the verdict, tokens and open findings. Raw output goes to `runs/`.
5. A task returns once with findings; a second failure escalates.

## 5. Pre-registration discipline
1. `prereg/<H>.md` copies the prediction, minimum effect, kill rule, n, seeds, split and analysis from PLAN.
2. Before the main run, the orchestrator records `code_tree_hash` (`manifest.tree_hash` over `src/` and `train/`), the config hash and the prereg file's own sha256, timestamped in `docs/reports/prereg-freezes.md`. PLAN 5.1 wants `prereg/` committed first, but only one commit is approved, so confirmatory runs (E1 sweep, E8.1, T7 main) wait for the owner's answer to question 1.
3. `stats.check_prereg` refuses mismatches. A code change after the freeze means a new freeze and a new run.
4. Smoke and practice data never enter the confirmatory analysis.
5. The test split is opened once.

## 6. Cost and energy accounting

| Wave | Tokens | Joules | USD |
|---|---|---|---|
| 0-1 | agent usage per task in evidence files; Fermi 3-4M | CPU, not measured (stated) | subscription route: unknown, not zero |
| 2 E1, E8.1 | 0 | not measured | 0 |
| 2 T7 | generated tokens from the JSONL; arm 0 at most 3.3M; A-D sized at step 8 | GPU only: `nvidia-smi --query-gpu=timestamp,power.draw,utilization.gpu --format=csv,noheader,nounits -lms 1000`; energy = sum of watts x 1 s | kWh; USD needs the owner's tariff |
| 2 C0 | API usage fields | n/a | usage x price sheet; stop at 5 |

**Power sampling.**
- Shared GPU: record 60 s of baseline first; report gross and baseline-subtracted joules; list compute apps at start and end.
- Idle fraction = samples with `utilization.gpu` of 0 / samples in the job window.
- GPU-hour = a wall-clock hour the job holds the GPU.

## 7. Risks and stop conditions

| Risk | Rule |
|---|---|
| Shared unified memory | Kill the job if MemAvailable (`/proc/meminfo`, polled every 10 s) drops below 10 GiB. The "free" column read 3 GiB while the box was idle, so it is not used; owner to confirm. Run with `--memory 60g` |
| Disk | No pull or download when less than 100 GiB is free (our choice) |
| Shared box, caps | Never touch another process, spark-vllm, 8010/8080 or OmniRoute; GPU-h meter per arm stops at the cap. E1 hit its precondition (1,079 events, 1 session; E8.1: 42 sessions with usage fields, 5 main); nothing waits on them |
| Destruction | Delete only the task's own temp files; the owner runs 6.2 rollbacks. Base weights read-only; a sha256 mismatch aborts T7 |

## 8. First 10 tasks (dispatch now)
1. W0-1 (orchestrator): run the baseline tests, add the `.gitignore` entries, grep for secrets, make the G0 commit.
2-9. W1-01, -03, -04, -05, -06, -07, -09, -11 in parallel (their files do not overlap).
10. Read-only preflight (orchestrator): the tag's `docker manifest inspect`, disk and MemAvailable, the repo size via `gh api`, the HF API JSON for `Qwen/Qwen3.5-0.8B`. No pull, no download. Then send the owner the questions below.

## 9. Cut by the five-step filter
- `cell.py`, `gate.py`, `memstore.py`, `board.py`: no reachable decision (section 1 rows; E5.6 exceeds 9 requests). Defers the signing key. Open (2026-11-19): adversarial review 2 recommends reinstating `cell.py`, the scripted router and the hub-as-cell contract tests (PLAN 6.1 P1b, 6.4); uncommitted `cell.py` and `router.py` exist, not verified. Owner ruling pending.
- 6.3 #8, opening the ten sources: no public claim is approved. memlint over owner memory: no decision.
- Pre-registrations H2-H4, H6, H9: runs blocked. Deleting `synth.py`: tests use it.

## Owner questions
1. Later local commits in `murmuration` (no push): a standing yes, or ask each time?
2. The G3 cache directory (proposed `data/hf/`), and licence confirmation from the evidence file.
3. Packages beyond transformers (`math-verify`, the IFEval checker), once they are listed.
4. The E8.3 subject: allow 0.8B after Fable's view, or approve G3(ii) with in-process inference?
5. C0: a billing route that returns usage fields; a Claude Code install in an isolated container; a call limit above 9.
6. Does the memory floor mean MemAvailable?
7. What does "+5 from 5" mean?
8. The signing key: will you create it when `cell.py` resumes?
