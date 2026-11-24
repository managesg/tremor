# TREMOR lane decision log

Decisions this lane makes under owner delegation. Each entry states the recommended option, the evidence and the remaining gaps. These decisions do not cover trials, runtime, spend, protected access, push, installs or shared writes, which keep their named approvals.

## 2026-11-23: M8 SmolLM3 smoke, documentary readiness preconditions

**Decided under owner delegation 2026-11-23T23:40Z** (owner, relayed by the Local Coordinator Assistant in `msg_9cb97dbb5a42`: "TREMOR: decide documentary M8 readiness preconditions and record exact gaps"). This is documentary only. It gives no run, reservation, spend or admission. The 0.1 GPU-hour reservation and the one-use admission remain a separate yes.

Sources:
- `docs/reports/tremor/OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md` (`9f01aa7c…`), Part B. Within it, SMO is `runs/smollm3-native-owner.vt3Sj1/OWNER.md`, SM is `docs/reports/workplan-ep/SmolLM3-native-smoke-packet.md`, and BO is the opening-balance packet cited there.
- `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md` (M8 row).

### Decision 1. Memory headroom: keep the stock gate

- **Decided:** keep the stock pre-start check. A fresh `MemAvailable` reading of at least 73,400,320 KiB (70 GiB) is taken at execution, and the 10 GiB host stop stays. No smaller envelope is adopted, because none has been reviewed (SM:43-46 calls the 70 GiB / 300 s / 0.1 GPU-hour envelope "proposed").
- **Evidence:**
  - Last packet readback: 57,100,444 KiB (54.46 GiB) on 2026-11-22 at 00:33:35 UTC (SMO:20-21), which is below the gate.
  - Read-only snapshot by this lane on 2026-11-23 at about 23:45 UTC: `MemAvailable` = 75.15 GiB, which is above the gate.
- **Gap:** memory depends on what else is resident at launch. The Spark operator must take the fresh reading at execution (SMO:14). The resource owner must confirm a window in which it holds (SMO:12). Today's snapshot is not that reading.

### Decision 2. Storage custody: read-only, hash-bound paths

- **Decided:**
  - **Name the paths:** before any admission, the storage operator names the canonical model directory and worker path.
  - **Freeze them:** for the run, those paths are made non-writable to every host writer, not just read-only inside the container, or replaced with a content-addressed copy the operator owns.
  - **Hash them:** a sha256 manifest of every file is taken before the run and after cleanup, and reconciled against the final `docker inspect` mounts.
  - **Approve:** the independent runner reviewer accepts the manifests.
- **Evidence:**
  - Directories are mode 0775 on writable ext4, and a read-only Docker bind does not stop a host writer, "as reproduced for the staged worker" (SMO:29-34).
  - The staging owner keeps custody during execution (SM:128-129). The pins to keep are at SMO:36-42.
- **Gaps:**
  1. The canonical paths are not named in the repo.
  2. No pre-run or post-cleanup manifest exists.
  3. The paths are currently writable.

  Holders: the Spark storage operator and the independent runner reviewer. The next event is the operator naming the paths.

### Decision 3. Launcher source: adopt the `--opening-balance` patched launcher

- **Decided:** adopt the patched launcher, which binds the launch to the reviewed ledger opening, with the T7 hold and the R2 charge (BO:8-10, BO:13-17). The stock launcher does not check the opening at launch (BO:3-6). The stricter check wins, the same rule used for every X42 merge conflict.
- **Evidence:**
  - The stock launcher `lab/smollm3_smoke_launch.py` is untracked and byte-identical to the finalized bundle copy in `runs/replication-smollm3-staging.out5A0/native-launch-cancellation-final.v022iV/`.
  - The patched copies (`xlu84i`) differ from it.
  - The resource owner must provide the placement pin either way (SM:195-196).
- **Gaps:**
  1. The patched source is not committed.
  2. Its source pin, and possibly the create-recipe digest, must be recomputed and pinned.
  3. The independent runner reviewer must re-review the exact source and recipe the admission binds (SMO:13).
  4. Nobody has checked whether `xlu84i` changes the recipe digest.

  Holders: this lane can commit and pin once the runner reviewer is available, and the reviewer re-reviews. The next event is the re-pin.

### After all three

The bounded yes stays as written in the packet: reserve 0.1 GPU-hour in `spark-replication` from the 9.5 GPU-hour residual and issue one one-use admission for the exact SmolLM3 smoke on the adopted launcher, for one fresh UTC window. This needs Alejandro's or PC's named approval, because it is a spend and runtime gate.

### Decision 3 follow-up: patched launcher adopted in `0b1e394`

The exact bytes from `runs/m8-smoke-bound-opening.xlu84i` are committed: 17 new lab files plus that packet's `lab/r3_resource_audit.py`. They were verified in `runs/m8-launcher-adoption-prep.551eS6` (EVIDENCE.sha256 `d5115eb2…`, ADOPT.sha256).

- **Recipe digest:** unchanged by the patch, `27a220e968184f3be53c5bbe5bbf9c1c049d730f0b229e01d87ccf873e8b6a43` for both stock and patched. It matches the vt3Sj1 pin.
- **Tests:** the xlu84i `verify.sh` exited 0 (75 tests). The smoke tests passed, 50 OK.
- **Superseded:** the stock source-manifest pin `c8164f59…`. The patched source manifest that replaces it, by sha256 of the committed bytes at `0b1e394`:

```
fd0fac7a8ef749adba676021c854fbbfbc2d726d4be89d3f9cea73671d1f286e  lab/smollm3_opening_balance.py
614bf82974a1b3335fca55743992ac8b518eb7c43998cc670303c6c44189e1f2  lab/smollm3_smoke_launch.py
78fe23335856eec34b5936fd191829721060022108f86cfdc1364b21b3fb74a3  lab/smollm3_smoke_preflight.py
980c09cdb9b4106eef02c40264fd5246a2f4c9fc7482de8e934fb7a0b636ff56  lab/tests/test_smollm3_smoke_launch.py
```

- **Remaining gaps:**
  - an independent review of `0b1e394` (requested);
  - the runner reviewer's acceptance of this manifest for the admission;
  - memory and storage, as in Decisions 1 and 2.

### Decision 3 follow-up 2: review of 0b1e394 and the full closure manifest

Two independent reviews REJECTED the `0b1e394` evidence, not its bytes. The bytes, the added-checks-only diff, the unchanged recipe digest and R3 behaviour all held. Fixes:

- **Fixture inside the repo.** The 12 opening-balance tests read a fixture outside the repo. `3b9f3ae` moved it to `lab/tests/fixtures/smollm3_opening/`, but `.gitignore` (`*.jsonl`) silently dropped `resource-ledger.jsonl`, so `ea821f4` force-adds it. On a clean `git archive ea821f4` all of these pass: `test_smollm3*` (50 OK), `test_r3_*` (121 OK), `test_spark_*` (23 OK) and `test_replication_inventory*` (13 OK, 1 skipped). The r3, spark and replication tests need `PYTHONPATH=src`.
- **Working tree synced.** The shared checkout's working-tree copies of the adopted files equal HEAD, so it no longer runs the stock launcher.
- **Closure widened.** The first 4-file manifest, and a first 28-file version, both missed files. The manifest below is the union of the stock pin's `lab/` entries and every `lab/smollm3_*`, `lab/spark_*`, `lab/r3_resource_audit.py`, test and fixture file, hashed at `ea821f4` (36 files; the last two spark tests, unchanged since, were added after the third review). The launch imports `lab/replication_inventory.py` through the preflight (`lab/smollm3_smoke_preflight.py:8`). The stock pin's `replay.py` and `replay_cancellation.py` are review scripts inside the bundle, not repo files.
- **Stock pin path.** The stock pin is `runs/smol-review-launch-join.RtBV9f/source/stock.sha256` (24 lines), as the prep `OWNER.md` said. An earlier version of this entry gave a wrong path.

**Open gap: the launch runs code that changed after review.** Four files differ from the stock pin. The launch, preflight and launch-test changes are the adopted patch. `lab/replication_inventory.py` is not part of the patch:

- `lab/replication_inventory.py`: stock pin `f7dc8f55…`, now `3bfe5af6…`
- `lab/smollm3_smoke_launch.py`: stock pin `728d3ba5…`, now `614bf829…`
- `lab/smollm3_smoke_preflight.py`: stock pin `5ebf9e4e…`, now `78fe2333…`
- `lab/tests/test_smollm3_smoke_launch.py`: stock pin `bb56623a…`, now `980c09cd…`

`lab/replication_inventory.py` changed in `009bb0b`, `67d88fa` and `63f1890`. Every reviewed bundle (`RtBV9f`, `xlu84i`) used `f7dc8f55…`. Before any admission, the runner reviewer must either review the HEAD bytes or bind the admission to a content-addressed source tree that carries the reviewed `f7dc8f55…`. This lane has not verified what the HEAD changes do (126 insertions, 12 deletions since `30788cb`). The runner reviewer must read that diff. The choice and the review belong to the runner reviewer. Nothing here grants a run.

```
41cdbac1526020ac6015188b4436cc856f77acfb28795850af79fcea2aab9e1f  lab/r3_resource_audit.py
3bfe5af69dd7be6873f3f6013f0d23075ba653150f6ed5c4e1d333cd391db4fc  lab/replication_inventory.py
fd0fac7a8ef749adba676021c854fbbfbc2d726d4be89d3f9cea73671d1f286e  lab/smollm3_opening_balance.py
7676b01dc6956bae06e2924225eb1fd1d15ba2e0e1e0ba597fa1350ecc830ecb  lab/smollm3_smoke_admission.py
5f6961d8c003a5f30f27d6a99706a195e859f9b383ece835c4bae9d8ae531cfd  lab/smollm3_smoke_container.py
614bf82974a1b3335fca55743992ac8b518eb7c43998cc670303c6c44189e1f2  lab/smollm3_smoke_launch.py
1504a5938882edf41d3670c09b302a6d7402832aee41aed00a35623d966261bf  lab/smollm3_smoke_metrics.py
78fe23335856eec34b5936fd191829721060022108f86cfdc1364b21b3fb74a3  lab/smollm3_smoke_preflight.py
85a355bb325e2fb2d0da23d1bab33a08fddbf2567e5435f80225f133662dfd70  lab/smollm3_smoke_settlement.py
e9742f988032aed81f33a231fd81011e6bff48ad939f0bce6457f1d05770cdd1  lab/smollm3_smoke_worker.py
74026cbea396bced1799ef0e87e6d03cdce2a658d47497d035b5d124aa9ccb92  lab/spark_calibration.py
e36746acb1bc779ba1ea04aca3ccb7fa1152e2b015c61ace66e8c294a0f79516  lab/spark_calibration_guard.py
84f0a4efc25e72552aaae1aaee0e1c30e2c5402d1a0047925deb882d61dc4faf  lab/spark_causal_decision.py
98c1ded35232841ac4699c9762bbd7ccbe9fdfdfe60c5a9bc0df4b77f69a76fe  lab/spark_decision.py
369cbc6ee59dc9ae50a0b0dde8189d7be418fca4c91a658f6245e0707fa48af9  lab/tests/fixtures/smollm3_opening/r2-calibration.log
4394d1c6d09eabd9b463b08e03956d9977bd6c28fbe74c2f1fb7a34ee65cdadd  lab/tests/fixtures/smollm3_opening/resource-ledger.jsonl
e8cb73bd751cb0775abc648a7b1ed9702e90b258335a7e0b51afd74ce39be2ff  lab/tests/fixtures/smollm3_opening/rollback-admission.json
3dc4f062f9fd8dcefa310acb8aebb279f9e591e9c711a68648852cb7051bd51e  lab/tests/fixtures/smollm3_opening/rollback-placement.json
e4fb3b13f577e22fcced04194c1aa390aef3f11ba35582e43ea3c7d193af5ddc  lab/tests/fixtures/smollm3_opening/rollback-reserve.json
0e13c36ccb862b0702fb580dc30db70b0696ef1a4b4fe4141fe9714d08039be8  lab/tests/fixtures/smollm3_opening/synthetic-admission.json
cf6e3b20e7e77880ce92f9a9df0bc695a362f57e6580192dbd990a629712677c  lab/tests/fixtures/smollm3_opening/synthetic-placement.json
4da274d38dbec90c11ab967040d4c584b3bbdc81d99078dff61de44f1c32c5ef  lab/tests/fixtures/smollm3_opening/synthetic-reserve.json
1f9f1ff9f3546031951663c06c11ad26c327dd4e5cbd6597afe0635edffd7b2f  lab/tests/test_r3_exact_container.py
f84325d86c8ba79ca58957b9a68b3a9245432b8487e9e336e06227a5aabbc24f  lab/tests/test_r3_resource_audit.py
4bb8e2d4d26133f8afd699015a80c47c9bdb8ffe4c076eb713ae156510794c02  lab/tests/test_smollm3_opening_balance.py
c1adba5fae380de02e738fa3e22d1874f418c32a7de33213861cbf89c70922fe  lab/tests/test_smollm3_opening_preflight.py
0c45a3dc1be46daa0799f2947f3e61d171f387fe90322c96929926871f108632  lab/tests/test_smollm3_smoke_admission.py
de5b623021ccf350268b3d4600ec8599455ce8947672a4049acdf95bef5db34b  lab/tests/test_smollm3_smoke_container.py
980c09cdb9b4106eef02c40264fd5246a2f4c9fc7482de8e934fb7a0b636ff56  lab/tests/test_smollm3_smoke_launch.py
3cae6eb35240cef13de519e9aba24e6f2eabbbbe7fbb788f32abe446a755c54d  lab/tests/test_smollm3_smoke_metrics.py
2e1e93a3f2fe9956ff252aa2d61ce54a69d4e347b308d73316caaf424c5ff2f1  lab/tests/test_smollm3_smoke_settlement.py
fcc21ea3c1bc40fad1d0f7ba2e97718dfee68582360ddb74ea6a87ea1cc9019a  lab/tests/test_smollm3_smoke_worker.py
41786d2a7117feeecdfc43c77808e5e46b416e02a60ff1cc806fd05509b9cf55  lab/tests/test_spark_admission_diagnostic.py
dea597b814f4221f38af7c1d4334333c8cd3000e943e575c2cf101ca368cac4d  lab/tests/test_spark_admission_journal.py
cde7d754aeefd969df44cb34b5a136653197ee4a66d370c3ad2af9cad4f6b982  lab/tests/test_spark_calibration_guard.py
59a11d9ed6882093c43344ba7e4b4783e270b0de0beebb5424d047fc7339b826  lab/tests/test_spark_decision.py
```

### Decision 4: `lab/replication_inventory.py`, adopt exact HEAD (closes the open gap above)

**Decided under owner delegation 2026-11-23T23:40Z**, on the Assistant's request `msg_c0f6cd21db13` (queue item `tremor-m8-inventory-closure-offline`). This is offline and documentary only. It gives no launch, GPU, spend or admission, and the resource and custody gates stay separate.

- **Decided:** the M8 admission binds the exact HEAD bytes `3bfe5af69dd7be6873f3f6013f0d23075ba653150f6ed5c4e1d333cd391db4fc`. No separately staged historical copy, and no shared revert.
- **Why:**
  - The preflight calls only `_normalized` and `_snapshot` (`lab/smollm3_smoke_preflight.py:76-79`) and never passes `compare_tensors`.
  - On that path, the diff `30788cb..63f1890` changes only how bytes are hashed: `_file_digest` now runs through `_check_file` and `_hash_bytes`, which do the same steps in the same order.
  - The rest of the diff is new code the preflight never reaches: the Safetensors tensor checks behind `compare_tensors`, the identical-payload rejection in `verify`, a `--compare-tensors` flag, and `_capture_bytes`.
  - Adopting HEAD keeps one source tree. A staged old copy would add a second tree to keep in custody.
- **Evidence** (`runs/m8-inventory-closure.Wk4Oqq/`, `EVIDENCE.sha256` `fa4fe9cc…`):
  - **Equivalence:** `equivalence.py` loads both versions (`f7dc8f55…` from `30788cb`, `3bfe5af6…` from HEAD) and runs the preflight path on 14 fake snapshots. Both versions give identical results in all 14 cases (2 accepted, 12 rejected with the same messages), so none diverge. The rejected cases are grown, shortened and same-size corrupt weights, an extra file, a missing file, a symlinked file, no config, empty architectures, a shard not in the index, an empty weight, an identity mismatch and an LFS mismatch. Exit 0.
  - **Focused fake tests** on a clean `git archive 7d2717b`:
    - `test_smollm3*`: Ran 50, OK.
    - `test_replication_inventory*` (`PYTHONPATH=src`): Ran 13, OK, 1 skipped.
  - **Closure manifest:** regenerated at `7d2717b` as `closure.sha256` (36 files, `9076d475…`). It equals the follow-up 2 block line for line, including `3bfe5af6…`.
  - **Recipe digest:** unchanged at `27a220e9…`. The recipe is the container create argv, built by `lab/smollm3_smoke_container.py`, which does not import `replication_inventory`.
- **Remaining:** an independent verdict on this record and the exact tree (requested). Then the runner reviewer accepts the closure for the admission. Memory, storage, reservation and admission stay as in Decisions 1 to 3.
- **Independent verdict: ACCEPT** (Opus reviewer, against `a6a7875`). An AST comparison shows that, besides `_file_digest`, only `_snapshot`, `verify` and `main` changed. `_normalized`, `_tree`, `_metadata`, `_json` and all constants are identical. With `compare_tensors=False`, `_snapshot` returns the same dict. The reviewer added 17 adversarial cases of its own: weights over the `CHUNK` size, nested directories, the legacy dict manifest, the JSON limit, a nested symlink, duplicate keys, NaN, a bool size and a `..` path. Old and new diverge on none. It reran the tests and the hashes and got the same results. Its nits: this lane's 14 cases did not cover the chunked-read path (its own cases did), and the evidence folder is git-ignored, so custody rests on `EVIDENCE.sha256` `fa4fe9cc…`.
