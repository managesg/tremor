# WSP-R1 cost: an ESTIMATE from recorded tokens (not a billed figure)

Written 2026-11-26 by the TREMOR lane for the plan's SUBTASK line "WSP-R1 cost upper estimate". Gap review A found that "billing ledger" is not a gate for an estimate: unknown cost is not zero.

**Inputs (recorded, not measured here).** The Assistant's tokens-only file `docs/reports/assistant_reviews/WSP_R1_USAGE_20261125.md` (not readable on this host; the figures come from the plan line and the outbox): 8 calls, input 62, output 39,791, cache create 983,957, cache read 1,841,140 tokens. Prereg `5367f53`, result `5938fed`. The model is reported as "Opus"; the 5-minute versus 1-hour cache-write tier is not recorded.

**Rates.** `docs/reports/tremor/price-sheet-20261126.json` (sha256 `2edb8b5ca979694eefe720d0fb3f0bf2a33cda73966b5c26f856392342a7a0f2`, fetched 2026-11-26; identical rates to the 2026-11-20 sheet), USD per million tokens.

| Model assumed | Cache writes at the 5-minute rate (lower) | Cache writes at the 1-hour rate (upper) |
|---|---|---|
| claude-opus-5-5 | USD 6.08 | USD 9.04 |
| claude-sonnet-5-5 | USD 3.04 | USD 4.52 |
| claude-fable-5-2 | USD 11.80 | USD 17.70 |

Formula: (62 x input + 39,791 x output + 983,957 x cache write + 1,841,140 x cache read) / 1,000,000, per model and tier.

**Reading.** If the calls were Opus 5.5 the estimate is USD 6.08 to USD 9.04; the cache creation dominates (983,957 tokens). This is an estimate: the model, the cache tier, and any fast-mode or batch modifier (none are in the sheet) are assumptions, and a subscription route may not bill per token at all. The billed figure stays with the billing ledger (Console).

**Why it matters.** The owner's paid-call approval for TREMOR is USD 10 in total for M2, M7 and the D8 refetch (`docs/reports/factory_rca_20261125/FINAL_WORKPLAN_20261125.md`). WSP-R1 ran on 2026-11-24, before that approval and on a separate model ledger, so it is not counted against it, but the estimate is a reference for how large an unplanned batch can be: Pilot 4 is capped at USD 0.25 and EP-1 at USD 5.00 (USD 5.25 together, inside the USD 10). If the owner decides WSP-R1 does count against the same USD 10, the headroom left would be USD 10 minus the billed figure, and Pilot 4 plus EP-1 would not both fit at the upper estimate: that is a decision for the owner, not for the lane.

**Not checked.** The recorded token file itself (not on this host), the model and cache tier actually used, the billed figure, whether subscription use is billed at all. An independent Opus check of the arithmetic is requested.
