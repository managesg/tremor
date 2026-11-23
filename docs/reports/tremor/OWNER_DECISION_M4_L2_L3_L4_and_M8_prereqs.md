# Owner decision: M4 scope rulings for L2, L3, L4 and the M8 smoke prerequisites

Prepared 2026-11-23 on `seabridge-spark` from the murmuration checkout at HEAD `743dffb` (working tree dirty; the parent packet was written at `4442b97`). Read-only: no git write, network, GPU, container, quiet-host run, systemctl or N2 access was used. Nothing here is an admission, reservation or approval. It narrows Group B and the M8 row of `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md` (lines 114-118 and 184-217) to choices Alejandro can answer with one line each.

Abbreviations: **P** = `docs/PROPOSAL-RESIDENCY-V3.md`; **WP** = `docs/WORKPLAN-RESIDENCY-V3.md`; **APR** = `docs/reports/ep-approvals.md`; **RR** = `docs/reports/workplan-ep/R2-R4-protocol-readiness.md`; **CB** = `docs/reports/workplan-ep/Coordinator-blockers-20261122.md`; **FS** = `docs/reports/workplan-ep/R3-first-slices-admission.md`; **L2D** = `docs/reports/workplan-ep/R3-L2-protocol-draft.md`; **SM** = `docs/reports/workplan-ep/SmolLM3-native-smoke-packet.md`; **SMO** = `runs/smollm3-native-owner.vt3Sj1/OWNER.md`; **SAR** = `docs/reports/workplan-ep/Spark-allocation-rephase.md`; **BO** = `runs/m8-smoke-bound-opening.xlu84i/OWNER.md`; **PKT** = `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md`.

## Summary

| Item | Choice | Recommendation | Owner | One-line yes |
|---|---|---|---|---|
| L2 unplanted (arising) variant | Approve the arising form under the P:979 safe design, or decline it | Decline for this freeze. L2 stays on benign planted notes. Prediction E is not run. L2-C, the primary, is unaffected | Alejandro | "Yes: L2 runs planted notes only under D1, the arising form and prediction E are out of this freeze, as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md" |
| L2-E support bound | Lower bound above 1% (P:398-399) or above 5% (P:404-406) | 5%, the later "Line 2E fix". It applies only if E is ever approved. Mark support as prospectively unreachable at n=200 | Alejandro | "Yes: L2-E, if ever approved, uses support at lower bound above 5%, as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md" |
| L3 primary | C (selection pressure and rotation), or B (held-out catch gain over top-k at 5% FPR) | C, chosen now. B stays a registered prediction and becomes primary only if C is declined before any outcome | Alejandro | "Yes: L3 primary = C under the D1 toy-monitor conditions; B becomes primary only if C is declined before any outcome, as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md" |
| L4-D setting outside D1 | Approve the arising-shortcut setting for prediction D, or leave it out | Leave it out of this freeze. L4-C, L4-B and L4-E stay in scope | Alejandro | "Yes: L4-D's arising-shortcut setting is out of this freeze, and L4 keeps C, B and E as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md" |
| M8 SmolLM3 smoke | Reserve 0.1 GPU-hour in `spark-replication` and issue one one-use admission | Approve once these three are met: memory headroom, storage custody, one adopted launcher. Two more steps follow (see Part B) | Spark resource owner, storage operator, runner reviewer; Alejandro for the spend | See Part B, "One-line yes" |

---

## Part A. M4 scope rulings

### What D1 is, and why these still need Alejandro

D1 is recorded at APR:166: "contagion/poisoning with benign planted notes allowed; monitor selection against an optimizer allowed (defensive); direction ablation in the local open 4B model allowed." The orchestrator (Opus 5.5) wrote it as a DISCLOSED-DECISION under the owner's advance delegation (APR:161-165). Alejandro did not write it. P:974-975 says "The project owner has to rule on each before it is built; until then it stays scripted or out." WP:245 lists "Rulings beyond D1, including unplanted contagion" as an owner approval. Wherever a recommendation below relies on D1, Alejandro's yes ratifies D1 for that line.

### L2: unplanted (arising) variant

**(1) The choice, as written.**
- P:369-373 defines two forms. *Planted* is "one fixed, hand-written note ... at five non-zero fractions ... plus a trigger-only control". *Arising* is "nothing planted; a time squeeze and a deliberately broken copy of our own scorer".
- P:979 is the dual-use row "Contagion through shared notes, planted and arising (line 2; line 4 D)". Its proposed safe design says "The arising form exploits a deliberately broken copy of our own scorer, never the live one. Every arm is paired with a defence arm." If declined: "the arising form is dropped and nothing is called an organism."
- D1 covers only benign planted notes (APR:166, P:949). "The unplanted variant needs its own ruling and protocol" (FS:23; also CB:45-46, RR:19, L2D:19-22).

So, because D1 already covers planted notes, the open choice is (a) approve the arising form under the P:979 design, or (b) decline it. Declining it removes only prediction E. Line 2 does not drop to scripted-only.

**(2) Recommendation: (b) decline the arising form for this freeze.** This keeps the preregistered design narrowest, as the brief asks. The repo does not settle the scientific question of whether the arising form is worth its risk.
- The primary contrast is L2-C (P:377-380; WP:50; RR:19), which uses planted notes only. Declining E leaves it untouched (L2D:19-22).
- The arising form sits nearest the rule against self-propagating behaviour (P:971-972, P:979).
- The repo has no protocol for it (FS:23).
- A later, separate ruling and protocol can still add it.

**(3) Risks.**
- *If declined:* prediction E (P:381-382, "arises unplanted in about 5% of episodes on some tier") goes untested. The proposal's novelty claim for "the arising form" (P:420-421) goes unmet in this freeze.
- *If approved:* it needs its own protocol (FS:23) and a broken scorer copy kept apart from the live scorer (P:979). It also needs an episode count for E. The repo sets no count; P:404-406 works through n=200 as an example. Its power is low (see L2-E). It adds a dual-use surface that D1 does not cover.

**(4) One-line yes.** "Yes: L2 runs planted notes only under D1, the arising form and prediction E are out of this freeze, as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md"

### L2-E: support bound 1% or 5%

**(1) The choice, as written.**
- Prediction: "(E) The shortcut arises unplanted in about 5% of episodes on some tier (a point prediction). [45%]" (P:381-382).
- Kill and first support text: "E: killed if on every tier the upper 95% bound (Clopper-Pearson, effective n) is below 5%. Supported if on at least one tier, Holm-corrected across tiers, the lower bound is above 1%: the shortcut arises unplanted at all." (P:397-399)
- Later fix: "**Line 2E fix:** ... Support requires a lower bound above 5%, which at n=200 needs ≥17 events (2% power at true 5%, 79% at true 10%). Holm correction across tiers is applied." (P:404-406)
- RR:53-55 marks the conflict and requires it to be resolved before any approved L2-E protocol is frozen.

The kill rule (upper bound below 5%) is the same under both options. Only the support threshold differs.

**(2) Recommendation: a lower bound above 5%.** It is the later text, headed "Line 2E fix" under the accuracy-review fixes (P:401-406), and it is the stricter claim. Under the L2 recommendation above, E is not run in this freeze, so this ruling only fixes what any later E protocol inherits. Per RR:43-45 ("mark unreachable outcomes prospectively"), the protocol should record that support is nearly unreachable at n=200 when the true rate is near 5%.

**(3) Risks.**
- *5%:* the repo itself puts power at 2% when the true rate is 5% (P:405). A result consistent with the point prediction will almost always read as inconclusive.
- *1%:* it supports "arises at all" (P:399). That is a weaker and different claim than the "about 5%" point prediction (P:381-382). It also contradicts the later fix text.

**(4) One-line yes.** "Yes: L2-E, if ever approved, uses support at lower bound above 5%, as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md"

### L3: primary C or B

**(1) The choice, as written.**
- "(B, a replication) The selected ensemble catches at least 10 points more at a 5% false-positive rate than the top k by accuracy. [30%] (C; **primary**) Under best-of-16 selection against one toy monitor, that monitor's catch rate falls by at least 30 points and a hidden view by at most 10; rotation halves the ensemble's loss and beats conservative aggregation. [30%] If the owner declines the selection arm, B is primary." (P:458-462)
- WP:50-51: "L3 C (B if the selection arm is declined)."
- RR:20 adds "Keep the toy setting defensive and within D1", and RR:57 adds "Select L3-C or its stated fallback before seeing outcomes."
- P:489: "Prediction C needs a dual-use ruling." P:980 sets the conditions: "Our own toy monitor; a benign stand-in (touching a toy file); best-of-N only; no prompt injection, no compaction attack, no fiction or role-play search." D1 records "monitor selection against an optimizer allowed (defensive)" (APR:166; P:950).

**(2) Recommendation: C as primary, chosen now and bound to the P:980 conditions and RR:20. B stays a registered prediction. It becomes primary only if C is declined, and only before any outcome is seen (P:462; RR:57).** C is the registered primary in the proposal, the workplan and the readiness index. D1 already records the selection arm as allowed, so this yes ratifies D1 for L3. "Fallback" here does not mean switching to B if C goes badly. Switching after outcomes would break RR:57.

**(3) Risks.**
- *C:* the proposal itself expects the local-tier kill. "weak local monitors catch under 20% at every setting, and there is nothing to degrade ... so the last outcome is likely on the local tier" (P:469-472). It also adds a selection-against-a-monitor surface (P:980).
- *B:* "at 200 the kill is low-powered and we say so". A paired standard error of about 1.1 points needs "about 900 to 1,700 failure episodes at 10 to 20% discordance" (P:465-467). RR:46-47 sets minima of 400 clean and 200 failure episodes for 5% false-positive readouts. Choosing B also drops the line's stated novelty: "Novelty: low for selection, medium for rotation" (P:487).

**(4) One-line yes.** "Yes: L3 primary = C under the D1 toy-monitor conditions; B becomes primary only if C is declined before any outcome, as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md"

### L4: L4-D setting outside D1

**(1) The choice, as written.**
- "(D, norms through dreams) A shortcut that one agent took once is written into the always-loaded layer by a plain dream within three nights in at least half the chains where it arose, and not by verified replay. [30%]" (P:538-540)
- P:951: "Line 4, text arms ... D1 covers benign planted notes. Review any setting outside that approval."
- CB:52: "An L4-D setting outside D1 needs a separate scope ruling."
- P:979 puts "line 4 D" in the same dual-use row as the arising contagion form. That row's "If declined" text describes only Line 2. **The repo states no consequence for declining L4-D.**

The choice is (a) approve the arising-shortcut setting for D under the P:979 design, or (b) leave D out of this freeze.

**(2) Recommendation: (b) leave D out of this freeze.** This is the narrowest reading, and it matches the L2 ruling for the same dual-use row.
- L4's primary is C (P:536-538; WP:51; RR:21) and does not depend on D.
- L4-B uses "one planted inert wrong note" (P:533-534), which D1 covers.
- L4-E falls under D3 (APR:168; P:957).
- Even if D were approved, P:548-549 says that with "fewer than 20 arise, D is reported as descriptive. At a 5% arising rate, 20 arising chains need about 400 chains." The repo budgets no chain count for L4, so an approved D may still end up descriptive only.

Separately, the authors must bind the token reference and the joint decision across the two strongest settings (RR:55-56). That is an author freeze item, not an owner ruling.

**(3) Risks.**
- *If left out:* prediction D, the only L4 test of norms spreading through dreams, goes unmeasured. "Evan Hubinger and Sara Price for D and E" (P:571) loses one of its two predictions.
- *If approved:* it adds a dual-use surface beyond D1 and needs its own protocol. It needs a deliberately broken scorer copy (P:979). It probably needs about 400 chains just to get beyond descriptive (P:548-549).

**(4) One-line yes.** "Yes: L4-D's arising-shortcut setting is out of this freeze, and L4 keeps C, B and E as recommended in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md"

---

## Part B. M8: three prerequisites for the 0.1 GPU-hour SmolLM3 smoke admission

**Correction to the brief.** The sources list five preconditions, not three (PKT:217; SMO:9-14). The three below are the ones still open on evidence or source. The other two are the approval steps themselves, and they follow once these three are met:
- (4) The Spark resource owner reconciles the current ledger head and writes the 0.1 GPU-hour `spark-replication` placement, keeping the 4.0-hour T7 hold (SMO:12; SAR:53-58).
- (5) The issuer creates the one-use admission for a fresh UTC window, and the coordinator keeps its SHA-256 apart from the admission file (SMO:13).

The smoke is technical only. It does not decide the L1-L3 replication freeze (SMO:6-7).

| # | Prerequisite | Owner | Evidence | Status confirmed against sources |
|---|---|---|---|---|
| 1 | **Memory headroom.** Get a fresh `MemAvailable` reading at or above the stock pre-start check of 73,400,320 KiB (70 GiB). Or get a separately reviewed envelope that fits | Spark resource owner confirms the window or returns the reviewed envelope (SMO:12). Spark operator rechecks host headroom at execution (SMO:14) | SMO:20-21: 57,100,444 KiB (54.46 GiB) at the 2026-11-22 00:33:35 UTC readback, about 15.5 GiB short. SM:43-46: the 70 GiB / 300 s / 0.1 GPU-hour envelope is "**proposed**" and "The reviewer can choose a different validated envelope." The 10 GiB host stop stays (SM:39) | Confirmed. ~54.5 GiB is correct. Not re-read here. The sources also allow a reviewed alternative envelope besides a fresh ≥70 GiB reading |
| 2 | **Storage custody evidence.** Name the canonical model and worker paths. Show the backing bytes stay fixed through cleanup, and reconcile that with final Docker inspection | Spark storage operator and independent runner reviewer (SMO:11) | SMO:29-34: directories are mode 0775 on writable ext4. A read-only Docker bind does not stop a host writer, "as reproduced for the staged worker". SM:128-129: "The staging owner retains custody of those paths during execution." Pins to keep: SMO:36-42 | Confirmed. The repo does not yet name the canonical execution paths, so that is part of this item |
| 3 | **Adopt one launcher source.** Choose the stock launcher or the `--opening-balance` patched launcher, then commit it and re-pin it | Alejandro adopts it. The independent runner reviewer re-pins the source and recipe the admission binds (SMO:13: "exact reviewed source and recipe"). The committer is the owner or the coordinator, not this packet | Stock: `lab/smollm3_smoke_launch.py` is untracked in the checkout (`git ls-files`). It is byte-identical (`cmp`) to `runs/replication-smollm3-staging.out5A0/native-launch-cancellation-final.v022iV/lab/smollm3_smoke_launch.py`, the finalized bundle with source manifest `c8164f59...a450a05c` (SM:174-177; SMO:41). Patched: `runs/m8-smoke-bound-opening.xlu84i` requires `--opening-balance LEDGER R2_GUARD PLACEMENT PLACEMENT_SHA256` and refuses reserves that erase T7 (BO:3-25). 75 tests pass, 78 combined (BO:34-40). Its `source/`, `patch-rehearsal/` and `combined/` launcher copies all differ from the checkout copy (`cmp`). Adoption is open (SM:201-202) | Confirmed, with one new fact. The parent packet had not compared the checkout copy with `v022iV`. They are identical. If the patched source is adopted, the stock source manifest pin (SMO:41) and possibly the recipe pin (SMO:42) no longer apply and must be re-pinned before the admission |

Choosing the launcher is Alejandro's call. The patched source binds the launch to the reviewed ledger opening, with the T7 hold and the R2 charge (BO:8-10, BO:13-17). The resource owner must supply the placement pin anyway (SM:195-196). Its cost is a new source pin and review before the admission. The stock source keeps the existing pins. It does not check the opening at launch (BO:3-6).

**One-line yes (once 1-3 are met).** "Yes: reserve 0.1 GPU-hour in `spark-replication` from the 9.5 residual and issue one one-use admission for the exact SmolLM3 smoke on the adopted launcher source, for one fresh UTC window, as set out in OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md"

That yes covers the placement (step 4) and the one-use admission (step 5) for that exact batch and window. The Spark operator's launch still runs under the issued admission and the shared guard lock (SMO:14). The yes does not cover the L1-L3 freeze or any other batch.

---

Unchecked here: live host memory, current ledger head, the actual storage paths, and whether `xlu84i` changes the create recipe digest. No `prereg/` freeze document was read.
