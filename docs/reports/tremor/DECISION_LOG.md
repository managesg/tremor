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
