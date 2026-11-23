# X42 Gate R1 bench re-review packet: candidate d918428

**For:** the designated independent bench reviewer (PC forwards this packet). **Written:** 2026-11-23 on host `seabridge-spark`, by the TREMOR lane, from repository files only. **Status:** a brief. It grants no access, spend, session or approval, and it is not a verdict.

Designation basis: `coordinator-outbox/pc-x42-r1-reviewer-designation-1355Z.md` (a fresh-context Opus-tier adversarial reviewer briefed with `interrogate`, distinct from the source author, the host operator and the host reviewer). That designation was written for e972484a and says a fresh nomination is needed after the grader fix. This packet is that fresh nomination's review brief.

## 1. The candidate

| Item | Value |
| --- | --- |
| Commit | `d918428` = `d91842854838e6c7945585a319853d1289d14d4b` |
| Tree | `6b15853eafadb433b6f53fa62ac41caa5b9b5fff` (563 files, all regular, mode 100644) |
| Parent | `1f45463` (L5 grader fix adopted) |
| Repo HEAD today | `4442b97`, which differs from d918428 by two docs-only files (`docs/reports/TREMOR_GOAL_AND_PLAN_20261123.md` and the row-157 addendum). Review the d918428 tree, not HEAD. |
| Policy file | `docs/WORKPLAN-RESIDENCY-V3.md`, sha256 `71c1cb470a3c1438dc2348963360167a49455bf864f1310b507cb37b5cbfc9f1`. Same bytes at e972484a and at d918428. All R1 boxes are still unchecked in it. |

**Relation to e972484a.** e972484a is not a git object. It is the sha256 of the archive manifest `runs/r1-n2-corrected-candidate.i5ACbL/source.sha256` (351 files; bytes under `.../source/`), which the previous REJECT was bound to. d918428 is that archive plus this lane's R1 build, committed so the bytes are a git tree. 144 archive files were absent from git and were added; 52 differing files were merged by an independent classification (34 keep the lane's version, 12 take the archive, topology.py merges to the lane's version, 4 governance conflicts keep the stricter lane version, the L5 grader takes the archive's stricter version plus the adopted fix). Evidence: `runs/x42-rebuild-lineage-receipt.fPcr5u/` (`RECEIPT.md`, `decisions.tsv`, `attribution.tsv`, `archive-manifest.sha256`, `rebuild-paths.txt`, `working-tree-newer-than-commit.txt`). That receipt records a fresh-context Opus review of d918428 with ACCEPT. That is a lane-side lineage review, not the Gate R1 bench verdict, and it does not bind you.

**Previous verdict:** `runs/x42-r1-bench-verdict.uPqmQ9/VERDICT.md` (REJECT, bound to e972484a). Defect D1 (`readouts.pairwise_miss`) is the only code defect it names.

## 2. Row-by-row brief (policy rows 155-169)

Row numbers are line numbers in the policy file. Rows 156, 160, 161, 163, 164, 166 and 168 are continuation lines of the item above them. Module hashes are the first 16 hex of sha256 at d918428. Paths are relative to `/home/adelmar/SeaBridgeAI/murmuration`.

### Row 155 (read module bodies) - previous: INCOMPLETE
- **Previous:** box unchecked; the policy's own "Not checked" section (line 252) still says "docstrings only".
- **Changed:** a fresh-context Opus body review of the ten modules at `00619ed`: `runs/r1-row155-body-review.ipRvT9/REVIEW.md` (module hashes, extension constraints, three docstring/body disagreements, eight demonstrated defects; it notes `poison` lives at `src/murmuration/trapbench/poison.py`). Fixes, each with a test: `30bb01c` (coupling option-like revisions; ledger `deny_keys`), `33b2ca2` (perturb non-bool `passed`, negative tokens), `52cbce1` (monitor, enforce, consolidate, orders).
- **Check:** the seven fixed modules differ from the e972484a archive and from `00619ed`; `board.py`, `memlint.py`, `poison.py` are byte-identical to the archive. Read the bodies yourself and decide whether the row's work (read before extending) is evidenced. Tests: `tests/test_{board,orders,perturb,monitor,consolidate,enforce,ledger,coupling,memlint}.py`, `tests/test_hardening.py`.
- **Not checked by that review:** the R1 technique modules, `stats.paired_bootstrap` edge cases, memlint with symlinks. The policy checkbox and line 252 text were not edited; whether they must be is your call.

### Row 157 (episode design v2) - previous: INCOMPLETE
- **Previous:** four rounds, but round 1 not scored apart; staggered reads hit a delivery-log marker; "contention above 1" undefined (2 claimants in round 1 only; 4 agents for 6 tasks overall).
- **Changed:** only definitions. `docs/reports/workplan-ep/R1-row157-contention-definition.md` (sha256 `b9db8f838448d11e681809bbc4a56f018d743a295f91cc19364dc06ea33cc5f8`, commit `8a16e88`, in the candidate) defines design contention kappa_r = A_r/T_r, requires kappa > 1 in every round with T_r >= 1, and scores round 1 apart. `docs/reports/workplan-ep/R1-row157-contention-addendum.md` (sha256 `f6ae2b439ef0eca40053f80e243e9158bef67edcef2969392381f0ae640e0b0d`, commit `5cabfe7`, after the candidate, docs-only) pins scheduled counts before the reveal.
- **Generator unchanged:** `lab/r1_episode_v2.py` and `lab/r1_episode_board_coupling.py` are byte-identical to the e972484a archive (checked with cmp). Staggered reads are still undefined (definition item 9 defers them to a separate frozen document; none exists in the repo).
- **Row-157 pre-reveal pins (what exists, what does not):**
  1. Definition sha and commit: pinned (above).
  2. Addendum sha and commit: pinned (above).
  3. Per-round table of scheduled agents and open tasks (or the generator rule), with its sha256, generator revision and seeds: the addendum requires this before any bench outcome is revealed. I found none committed. Treat as not pinned unless you find one.
  4. Staggered-reads definition: not pinned.
  Do not pass the row by running the generator and fitting a rule to it; that is the post-reveal route the addendum forbids. Evidence of the generator's behaviour: `runs/r1-episode-v2.TN86mA/`, `lab/tests/test_r1_episode_v2.py`, `lab/tests/test_r1_episode_board_coupling.py`.

### Row 158 (night loop) - previous: ACCEPT with caveat
- **Previous caveat:** `night.consolidate` returns a new store and keeps the old one, but `lineage` searches one store, so full history needs all stores joined.
- **Changed:** nothing in the candidate. `src/murmuration/night.py` (`9ce6c4e8f6cd512e`) is byte-identical to the archive; last touched by `154e280` (isolate archived night-loop provenance). Related evidence: `runs/r1-night-store-isolation.Ldw3Rp/`. Tests: `tests/test_night.py`.
- **Check:** whether the caveat still stands as stated; rule on the row as you see it.

### Row 159 (readouts in one thin module) - previous: REJECT (no `susceptibility.py`, no adoption or cascade-depth, Kish and fluctuation ratio in lab, defect D1)
- **Changed:** `src/murmuration/susceptibility.py` (`276f819a7697b95e`, commit `da38c43`). It re-exports `rerun_variance`, `dose_slope`, `reproduction_number`, `recovery_time`, `pairwise_miss` from `readouts.py`, ports `response_fluctuation_ratio` and `kish_spread_check` from lab, and adds `adoption` and `cascade_depth`. Tests: `tests/test_susceptibility.py`.
- **D1 fix:** `899ffeb`, `src/murmuration/readouts.py` (`b43e84c7867a842d`): `pairwise_miss` returns None for an undefined Kish n_eff. Test: `tests/test_readouts_kish_guard.py`. The previous review reproduced D1 on e972484a; reproduce the fixed behaviour on the d918428 tree.
- **Verifier receipt:** susceptibility ACCEPT in `runs/r1-row169-module-verification.BBKCr0/RECEIPTS.md` (module unchanged since).
- **Open from the lane's own notes:** the policy lists "response to fluctuation ratio" and "Kish n_eff with the spread check"; the scientific variance denominator and reference condition belong to the prospective protocol, not this module.

### Row 162 (seven scripted nulls) - previous: REJECT (no L4 iterated map, no L6 fixed K/D lease null, L7 one fixed shuffle, L2 one generation only, L1 without scripted adopters)
- **Changed:** `src/murmuration/nulls.py` (`3fd363a26ae50ba0`, commit `00619ed`, then fixes `08659a3`, `6e33ad2`, `7b4ea36`, `9203700`, `cf9572e`). Functions: `scripted_adopters` (L1), `reed_frost` (L2 well-mixed epidemic with immunity, all generations), `correlated_monitors` (L3), `iterated_map` and `recovery_nights` (L4), `fixed_kd` (L6), `random_blocks` (L7, exact over partitions). The L5 random-order control is `lab/r1_l5_random_order_null.py`, outside `nulls.py`. Tests: `tests/test_nulls.py`, `lab/tests/test_r1_l5_random_order_null.py`.
- **Check:** each expected value against your own enumeration or closed form; the seven policy lines against these functions one to one; the `recovery_nights` compute guard (answers past the 2^22-bit guard are refused; `cf9572e` counts x and tol against it).

### Row 165 (technique modules) - previous: REJECT (none of the seven modules existed)
| Module (line) | File at d918428 | sha256 (16) | Test |
| --- | --- | --- | --- |
| `sgv` (L1) | `src/murmuration/sgv.py` | `0507d6f5d01c6661` | `tests/test_sgv.py` |
| `quarantine` (L2) | `src/murmuration/quarantine.py` | `1dab1758e89a7371` | `tests/test_quarantine.py` |
| `monsel` (L3) | `src/murmuration/monsel.py` | `57d6e0d61f5ce1f2` | `tests/test_monsel.py` |
| `vreplay` (L4) | `src/murmuration/vreplay.py` | `073d576a4b509c57` | `tests/test_vreplay.py` |
| `evapclaim` (L5) | `src/murmuration/evapclaim.py` | `46c87e87aafcbc47` | `tests/test_evapclaim.py` |
| `lease` (L6) | `src/murmuration/lease.py` | `8b9812a732b23d69` | `tests/test_lease.py` |
| `blocks` (L7) | `src/murmuration/blocks.py` | `77abcb79bf7e241c` | `tests/test_blocks.py` |

Commits: `4464b7e` lease, `bf304de` evapclaim, `44e19cc` sgv, `604fa25` quarantine, `fb9fb62` monsel, `7d28822` vreplay, `b264d8f` blocks, then fixes `de56a29`, `a5b85c0`, `08659a3`, `6e33ad2`, `7b4ea36`, `9203700`, `cf9572e`. The seven row-165 workers originally ran on a Windows read-only host and could not reach the Spark repository; their claims were not accepted, and the modules were verified from the Spark tree (row 169). The mapping from modules to the lab `l1_*`...`l7_*` files is not written down as a table; derive it from the module docstrings if you need it.

### Row 167 (L5 carriers, N2 Lean predicate, 10+ mutants) - previous: INCOMPLETE, custody-gated
- **Carriers present:** `lab/l5_carrier_fixture.py`, `lab/l5_dispatch_carriers.py`, `lab/l5_dispatch_census.py`, `lab/l5_taskset.py`, `lab/l5_shard_boundary.py` (memory arm and sharded environment arm, scripted). Both fixture files are byte-identical to the archive.
- **N2:** not in the repository by design. The public sibling norm is synthetic (`lab/l5_public_sibling_norm.lean`, `lab/l5_sibling_norm_control.py`); `docs/reports/workplan-ep/L5-N2-heldout-design.md` states the scientific N2 and its Lean statement are open. Custody status in section 5.
- **Mutants:** `lab/r1_public_arithmetic_mutants.py` and `lab/r1_independent_verifier_mutation_audit.py`; result `runs/r1-independent-verifier-mutants.1kFdlv/result.json`: 12 compiled mutations of `alloc.score`, 12 killed, `protected_n2` false, `bench_acceptance_claimed` false. These are mutants of the public arithmetic scorer, not of an N2 verifier, and the repository does not record their authorship against the policy's "author who is not the monitor author".
- **L5 grader fix:** adopted in `docs/reports/workplan-ep/R1-L5-grader-fix-decision.md` (sha256 `a0810957cc18b2e7a2e3f63e55245bc256e9d44003cfcbd3b82f7dc0cc73b40c`); patch `runs/r1-execution-consistency.BtUauk/owner.patch` (sha256 `16a1262ef94ad0f8b1b3f656ea8e8703f2130af6596f386df930031191f5b143`) changes `lab/l5_grader_custody.py` and `lab/tests/test_l5_grader_custody.py`; the decision notes the check proves two records agree, not where they came from.

### Row 169 (per-module Opus verification, then `interrogate`) - previous: INCOMPLETE (no receipts)
- **Changed:** `runs/r1-row169-module-verification.BBKCr0/RECEIPTS.md`: one fresh-context Opus verifier per module at `a5b85c0` (six REJECT with reproductions, `susceptibility` ACCEPT, `nulls` interrupted); second round at `08659a3`; third pass at `6e33ad2`; diff review of `7b4ea36` (REJECT on `recovery_nights`); fix `9203700`; the `9203700` review (REJECT on refusal speed only), fixed in `cf9572e` (worst case 0.93 s; full suites lab 406, package 850 per `runs/commit-suite-rn2.xfJTDa`). The R1 modules in d918428 are byte-identical to `cf9572e` per the rebuild receipt.
- **Honest gap:** the last per-module receipts name hashes from earlier cuts, and there is no per-module verdict recorded at the exact d918428 bytes; the only review at d918428 is the lane's candidate-level review (`runs/x42-rebuild-lineage-receipt.fPcr5u/RECEIPT.md`). Whether that suffices for the row, or you need per-module verdicts on these bytes, is your decision.
- **This packet is the `interrogate` pass the row asks for.**

## 3. Reproduction (read-only against the repository)

Confirm the host first: `hostname` must print `seabridge-spark`; stop and report otherwise. Everything below writes only inside a scratch directory.

```bash
cd /home/adelmar/SeaBridgeAI/murmuration
test "$(git rev-parse d918428^{tree})" = 6b15853eafadb433b6f53fa62ac41caa5b9b5fff
scratch=$(mktemp -d); git archive d91842854838e6c7945585a319853d1289d14d4b | tar -xf - -C "$scratch"
mkdir -p "$scratch/data/tools/lean" "$scratch/runs/ep1-live" "$scratch/home" "$scratch/tmp"
ln -s "$PWD/data/tools/lean/lean-4.35.0-linux_aarch64" "$scratch/data/tools/lean/lean-4.35.0-linux_aarch64"
cp -r runs/ep1-live/pilot3 "$scratch/runs/ep1-live/pilot3"   # outside the manifest; sha256 in section 4
cd "$scratch"
base=(env -i HOME="$scratch/home" TMPDIR="$scratch/tmp" PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=)
"${base[@]}" PYTHONPATH=src:tests:. /usr/bin/python3 -B -m unittest discover -s tests -v          # package suite
"${base[@]}" PYTHONPATH=src:lab:tests:. /usr/bin/python3 -B -m unittest discover -s lab/tests -t . -v   # lab suite
```
This follows `runs/commit-suite-rn2.xfJTDa/suite.sh`, which used a 900 s timeout and `nice -n 10`. The package suite took 755.6 s on the host at d918428, so use a longer timeout or none. A container variant (image `sha256:c74c8710f2bc017b5de956853c50d896af4aa49b751bb87cbebf69e5206befb7`, `--network=none --read-only --memory=4g --cpus=2`) is in `runs/container-suite-d918428.Q1iSRQ/run.sh`. A run was in progress there when this packet was written; its logs and exit files are evidence only once `DONE` exists.

**Recorded results at d918428** (host, clean `git archive`, `runs/commit-suite-rebuild.gtQgQg/`): package 869 tests, OK, 1 skipped, exit 0; lab 832 tests, FAILED with errors=10, skipped=9, exit 1. The lane's own review records the same lab errors on the archive suite.

**Known environmental errors (all 10 are in the lab suite):**
- 4 in `lab.tests.test_adapter_tensor_lineage` (`test_invalid_tensor_file_cannot_use_valid_opaque_digest`, `test_payload_change_and_comparability`, `test_pinned_tensor_header_cannot_shadow_a_conflicting_dtype`, `test_same_weights_with_distinct_metadata_cannot_supply_a_change`): numpy-dependent.
- 3 in `lab.tests.test_l8_loader_receipt` (`test_cli_observes_the_checkpoint_loaded_into_both_modules`, `test_refuses_a_loader_that_changes_the_installed_weights`, `test_refuses_dtype_conversion_before_loading`): torch-dependent.
- 3 in `lab.tests.test_pilot4_preflight_manifest` (`test_modified_candidate_request_digest_fails_closed`, `test_modified_price_sheet_fails_closed`, `test_pending_manifest_replays_without_sockets_and_keeps_a_distinct_batch`): the logged FileNotFoundError is `runs/ep1-live/pilot3/episodes.jsonl`, which is outside the manifest and git-ignored. With pilot3 copied as above these may pass; I have not shown that.
The attribution of each test name to numpy, torch or pilot3 comes from the rebuild receipt's counts (4/3/3) and the test file names, not from a per-test traceback check. Whether these errors may stay in a "green" suite is for you and the host reviewer to rule; the policy gives no skip or error allowance.

## 4. Pins for outside-the-manifest inputs
`runs/ep1-live/pilot3/` sha256: `episodes.jsonl` `04401ed5cf7d07e82e65bfa95d792234ac201cb591b12419434bbff6c2e4e0f6`; `final.json` `c104fedf6f277c61fb5c28140b2881afac67fdd6edf465b2685ca988a84ed8e4`; `pilot_trace.txt` `f7116becf94086692a1b182de849472343866eea1b16084d4aac5635fa52eb19`; `schedule.json` `2a0188449dff2b411c67b603473349325ad8148afbaa74ef2d109d84a55ce003` (observed 2026-11-23, not previously pinned by the lane). `data/math500/test.jsonl` is in the d918428 tree. The Lean toolchain at `data/tools/lean/lean-4.35.0-linux_aarch64` is outside git; its identity is recorded in earlier run folders only.

## 5. N2 custody
- Commitment: `6def4efcb166fc1c8da3f0974e8257c4bbe560c2449f85da86dbc808335119aa`, held by the Assistant (Codex c125641a). The plaintext is sealed with an independent author. **This packet contains no N2 content, and you must not ask for, derive or look for any.**
- Consequence for row 167: the N2 Lean predicate and mutants of an N2 verifier cannot exist in the repository until the custodian releases them under a separate admission. Rule on what the bench shows and say plainly what is custody-gated; do not substitute the public synthetic sibling for N2.

## 6. Your limits
Read-only on the repository: no edits, no git writes, no commits, no fetch or push, no network, no paid or GPU calls, no N2 access, no session launch, no host probes of other lanes. Scratch space only for the section 3 run. You rule on the bench, not on scope, and not on host qualification: the three quiet-machine runs are a separate gate (`OWNER_DECISION_X42_quiet_host_window.md`) and are not implied by any verdict here. Verifiers check claims against code; if a claim and code disagree, say which.

## 7. Output format
One file, bound to `d91842854838e6c7945585a319853d1289d14d4b` and tree `6b15853eafadb433b6f53fa62ac41caa5b9b5fff`. Start with the source check (tree id, file count, policy sha256 `71c1cb47...`) and your host check. Then:

| Row | Verdict | Evidence you checked (paths, commands, counts) | Reason |
| --- | --- | --- | --- |

with one line per row 155, 157, 158, 159, 162, 165, 167, 169, each ACCEPT, REJECT or INCOMPLETE. Use INCOMPLETE where the evidence cannot exist yet (custody, undefined terms) and REJECT where it exists and fails; say which. Add: defects found (with a reproduction each), what you did not check, and one overall line ("Gate R1 bench part: ACCEPT / REJECT / INCOMPLETE at d918428"). A verdict binds to d918428 only; any later source change needs a fresh nomination and a fresh review.
