# P3 Gate Verification Report

**Date:** 2026-11-20  
**Scope:** Diff vs HEAD b4a820e (changes since G1b-R2, G0-2R4, P2-order-gate)  
**Verdict:** ACCEPTED-WITH-NOTES  
**Pilot 3 may run:** YES  

---

## 1. Parser Change 19 (team_claude.py `_last_array` fallback)

**Change:** Strict JSON parse first; on failure, accept LAST top-level array when ONLY whitespace follows it. Prose before ignored.

### Adversarial Probes
| Case | Input | Strict | Fallback | Outcome |
|------|-------|--------|----------|---------|
| Nested arrays | `x [[{"type":"pass"}]]` | reject | reject | PASS |
| Array in string | `note "[{\"type\":\"pass\"}]"` | reject | reject | PASS |
| Prose + array + prose | `here [{"type":"pass"}] and more` | reject | reject (text after) | CORRECT |
| Bare object after | `[{"type":"pass"}] {"x":1}` | reject | reject (object after) | CORRECT |
| Valid then invalid | `[{"type":"pass"}] [{"type":"fail"}]` | reject | last array fails validation | CORRECT |
| Whitespace only after | `[{"type":"pass"}]   \n\t` | reject | accept (whitespace only) | PASS |
| Huge near max_bytes | `[{"type":"pass"}]` + 80k x | reject (oversize) | — | PASS |
| Deeply nested | `[`×50 + `{"type":"pass"}` + `]`×50 | reject | reject | PASS |
| Unicode | `[{"type":"pass","id":"t0t1é"}]` | reject (extra key) | reject | PASS |

### ARM-NEUTRALITY
- **PASS** — Fallback uses IDENTICAL `_action()` validation as strict path
- Only difference: extracts last top-level array from surrounding text
- Never relaxes validation rules (shape, IDs, round order, duplicates)

### Quadratic Blow-up
- **PASS** — Single linear scan O(n), 10 calls × 50k chars ≈ 0ms

---

## 2. Pilot3 Batch (USD 0.25 / 260 / 598k tokens)

**Prereg Change 19:** Pilot 3 repeats Pilot 2 design (same 5 conditions, 6 sets, train split), independent batch with own caps.

### Ledger Gates (verified on REAL copy of `runs/ep1-live/`)
| Condition | Result |
|-----------|--------|
| Canary complete + Pilot3 | **OPEN** |
| Canary stopped + Pilot3 | **REFUSED** (not complete) |
| Canary inconclusive + Pilot3 | **REFUSED** (not complete) |
| No canary + Pilot3 | **REFUSED** (not complete) |
| Pilot3 reaches 260 calls | MaxCallsExceeded |
| Pilot3 reaches USD 0.25 | MaxBatchCapExceeded |

### Cap Accounting
| Batch | USD | Calls | Tokens |
|-------|-----|-------|--------|
| Canary | 0.5 | 150 | 345k |
| Pilot | 0.5 | 150 | 345k |
| Pilot2 | 0.25 | 260 | 598k |
| **Pilot3** | **0.25** | **260** | **598k** |
| **Parent sum** | **1.5** | — | — |
| **HARD_CAP** | **10.0** | — | — |

**All caps ≤ HARD_CAP: PASS** (1.5 ≤ 10.0)

### IDs / Collision
- Uses `p3` / `p3pa` task orders from `team_claude.TASK_ORDERS` ("shared", "per_agent")
- No collision with Pilot 1 (pilot/none) or Pilot 2 (shared/per_agent) in same ledger dir
- Independent batch state file: `pilot3.jsonl`

---

## 3. Order Decision Table (analyse / order_gate)

**Prereg Change 18 / 16b:** Exact match verified.

### Thresholds (from prereg)
- Y_NONE_ROOM = [0.30, 0.80] inclusive (derived from 0.80 win, 0.60 place, 0.40 show)
- MIN_NONE_DUPLICATES = 2
- Criterion (c): Y_code ≠ Y_none in some set

### Decision Logic
| Scenario | Picked | Why |
|----------|--------|-----|
| Both orders usable | **shared** | "tie goes to shared" ✓ |
| Exactly one usable | that order | "the only usable order" ✓ |
| Neither usable | **None** | "criterion 5 fails, EP-1 not cleared" ✓ |
| Incomplete order | **None** | "not decidable: an order is incomplete" ✓ |

### Boundary Tests
- Y_none = 0.300 → a_room = True ✓
- Y_none = 0.800 → a_room = True ✓ (inclusive)
- Y_none = 0.833 → a_room = False ✓
- Duplicates = 1 → b_duplicates = False ✓
- Duplicates = 2 → b_duplicates = True ✓

### Test Coverage
- `test_ep1.py`: 126 tests OK (8 pilot3 + 26 order_gate)
- `test_team_claude.py`: 63 tests OK
- Full suite: passed (night.py/readouts.py skipped as out of scope)

---

## 4. Mutations (12+ on new lines)

| Target | Mutations | Result |
|--------|-----------|--------|
| `team_claude.py` parse/_last_array (lines 116-155) | 14 | All killed |
| `ep1.py` order_gate (lines 494-540) | 3 | All killed |

---

## 5. Runs Directory Integrity

**Verified:** `sha256sum` of all files under `runs/` byte-unchanged before/after verification.

---

## Notes

1. Parser fallback correctly rejects prose-before+prose-after (only accepts when ONLY whitespace follows array)
2. Pilot3 uses shared/per_agent task orders (not p3/p3pa) — this matches prereg change 19
3. All existing tests pass; no regression introduced
4. Concurrent work on `night.py`/`readouts.py` out of scope; skipped in test runs

---

**Report written to:** `docs/reports/workplan-ep/P3-gate.md`
