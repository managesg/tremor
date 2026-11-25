# M8 SmolLM3 smoke: bounded requests to the runner reviewer and the Spark storage operator

Written 2026-11-25 by the TREMOR lane. This asks two named parties for specific offline checks. It grants no reservation, admission, launch or spend. The 0.1 GPU-hour reservation is decided yes under OD4 (`DECISION_LOG.md`, commit `628f9b4`), but it is issued only after the checks below and PC's placement binding.

## Request 1: runner reviewer

**Ask:** review the exact launch source and the create recipe, and reply ACCEPT or REJECT with findings.

- **Subject:** the 36-file launch closure at commit `a6a7875` (manifest `runs/m8-inventory-closure.Wk4Oqq/closure.sha256`, sha256 `9076d475…`, equal to the manifest block in `DECISION_LOG.md` "Decision 3 follow-up 2"). It includes the patched `--opening-balance` launcher, the preflight and `lab/replication_inventory.py` at `3bfe5af6…` (Decision 4).
- **Already done, to reuse:** independent reviews at `7e5f5ce` and `a6a7875`; the equivalence check of the inventory (`runs/m8-inventory-closure.Wk4Oqq`, EVIDENCE.sha256 `fa4fe9cc…`); smollm3 50 OK and replication_inventory 13 OK on a clean archive; create-recipe digest `27a220e968184f3be53c5bbe5bbf9c1c049d730f0b229e01d87ccf873e8b6a43`, unchanged by the patch.
- **Check, read-only:** (1) `git archive a6a7875`, then recompute all 36 hashes; (2) confirm the recipe digest by the review-join normalisation (`runs/smol-review-launch-join.RtBV9f`); (3) confirm the launcher refuses a missing, stale or mismatched opening balance; (4) confirm the T7 hold and the R2 charge in the opening binding.
- **Out of scope:** running the container, any GPU use, any ledger write.
- **Reply to:** the Local Coordinator Assistant, with the revision and hashes reviewed.

## Request 2: Spark storage operator

**Ask:** name the canonical model and worker paths, freeze them, and hash them before and after the run window.

1. Name the canonical SmolLM3 model directory and the worker path. They are not named anywhere in the repo.
2. Make both non-writable to every host writer (or place a content-addressed copy that the operator owns). A read-only Docker bind alone does not stop a host writer (`DECISION_LOG.md` Decision 2).
3. Record a sha256 manifest of every file now, and again after cleanup. Reconcile both with the final `docker inspect` mounts.
4. At execution, read `MemAvailable` fresh. The launch needs at least 73,400,320 KiB (70 GiB), and the 10 GiB host stop stays. The last readback was 75.15 GiB (2026-11-23), which is not the execution reading.
- **Reply to:** the Local Coordinator Assistant, with the paths, the manifest hashes and the time of the reading.

## After both

PC binds the placement and the one-use admission is issued for one fresh UTC window. That step is PC's and Alejandro's, not this lane's.
