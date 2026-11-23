# Pre-registration scope: R2 lines L2, L3 and L4 (owner decision, documentary freeze)

**Status: SCOPE FROZEN (documentary).** Only the scope choices below are fixed. Each line's full protocol, code tree hash, protected inputs, admission and resource limits stay open, and this record gives **no run, spend or experiment authority**.

- **Owner decision:** Alejandro, relayed by the Local Coordinator Assistant (owner message `msg_e96a060964d0`, relay `msg_da45097af3c6`).
- **Decision basis:** packet `docs/reports/tremor/OWNER_DECISION_M4_L2_L3_L4_and_M8_prereqs.md`, sha256 `9f01aa7c07d8974fdebcd1775374e592363477778d16829ec689246860dac0c8`, committed in `3162743`.
- **Freeze inputs register:** `docs/reports/workplan-ep/R2-R4-protocol-readiness.md` (sha256 `1352e894…` as read; not edited by this record).
- **Proposal sources:** `docs/PROPOSAL-RESIDENCY-V3.md` at the commit that adds this file.
- **Date:** 2026-11-23.

## L2: memory error spread

1. **In scope:** benign planted notes only, under the D1 dual-use decision. The primary contrast is L2-C, as in the readiness register.
2. **Out of scope for this freeze:**
   - the unplanted ("arising") form of the shortcut;
   - prediction E.
3. **If E is approved later**, through a separate owner decision and its own freeze, support requires a lower confidence bound above **5%** (the proposal's "Line 2E fix", P:404-406), Holm-corrected across tiers. E must be labelled **low power**: the proposal states 2% power at a true 5% rate and 79% at a true 10% rate with n = 200 (P:405). The earlier 1% wording (P:398-399) does not apply.

## L3: monitor ensembles

1. **Primary:** C (selection pressure and rotation), under the existing toy-monitor contract (D1; the proposal's dual-use table, P:979 onwards).
2. **Fallback:** B (catch gain over the top-k at a 5% false-positive rate) becomes primary **only if C is declined before any outcome is seen** (P:462; readiness register, "Select L3-C or its stated fallback before seeing outcomes").

## L4: memory consolidation

1. **Excluded:** L4-D, the arising-shortcut setting outside D1.
2. **Retained:** L4-C (primary), L4-B and L4-E. L4-E keeps its separate adapter and lineage dependency on M5.

## D1 ratification

D1 was recorded by the orchestrator as a disclosed decision under the owner's delegation (`docs/reports/ep-approvals.md:163-166`). This owner decision ratifies D1 where L2's planted notes and L3-C rely on it.

## What still has to happen before any of these lines runs

For each line:
- freeze the full protocol, with its tree hash;
- pin the protected inputs;
- grant a one-use admission with resource limits, as listed in `docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md`;
- pass an independent review.
