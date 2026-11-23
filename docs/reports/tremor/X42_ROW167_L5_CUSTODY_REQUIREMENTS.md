# X42 row 167 and L5: custody and admission requirements

Requested by the Assistant (`msg_3c7c734027a2`) so these are on record before any quiet-window request. The quiet-machine window tests the suites only. It does not use N2, does not reveal it, and does not run L5.

## Current state at candidate 83e4870

- **Bench re-check:** row 167 INCOMPLETE (`runs/x42-bench-recheck-83e4870.4P3pJg/VERDICT.md`, sha256 `48834c15…`). The carriers are met, and mutant authorship is recorded as metadata (`docs/reports/workplan-ep/R1-row167-mutant-authorship.md`).
- **N2:** sealed. Commitment sha256 `6def4efcb166fc1c8da3f0974e8257c4bbe560c2449f85da86dbc808335119aa` of the UTF-8 `N2.md`, delivered to the custodian (the Local Coordinator Assistant) in `msg_fe35b22e0b12`. The custodian recorded the commitment metadata (`msg_49328f91917b`). This lane has never seen N2.

## Requirements, in order, each with its owner

1. **Custody binding (custodian).** Confirm in a dated message, with path or hash:
   - where the N2 plaintext is held, outside this lane's reach;
   - that its sha256 equals the commitment above;
   - that no copy was forwarded to the TREMOR lane.
2. **L5 run admission (Alejandro).** Give a named, one-use admission for the L5 carrier run that uses N2: scope, resource cap and the exact source commit. The protected-admissions packet (`docs/reports/tremor/OWNER_DECISION_protected_admissions_M3R3_M4_M9.md`, M3 R3-L5 row) records why this is not ready today: there is no native launcher, and the 4-hour slice is above the 3-hour L5 ceiling. Those preconditions stand.
3. **Run under custody (runner owner and custodian).** The admitted run receives N2 only through the custodian's release step. Release happens after the run's code and inputs are pinned, and its outputs are sealed before any reveal.
4. **Reveal and review (custodian, then an independent reviewer).** At the reveal, the custodian releases `N2.md`, and the reviewer:
   - recomputes its sha256 against the commitment;
   - checks the Lean statement of the predicate;
   - checks the 10+ mutants and whether the verifier kills them;
   - confirms the mutant author is not the monitor author.

   Only then can row 167 move from INCOMPLETE.

## What this lane will not do

Seek, read or reconstruct N2; run L5; or request a quiet-host window that touches N2. A quiet-window request, when made, covers the suites at `83e4870` only.
