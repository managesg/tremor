# Admission record, 2026-11-25 (TREMOR lane)

**Owner words, verbatim, relayed by the PC coordinator at about 22:45Z:** "I approve all requests from agents." Paid calls: "Paid calls for up to $10 for Tremor" (about 22:30Z; USD 10 total across M2, M7 and D8; running total USD 0.00, no call made).

**What this record does.** It records the owner's approval for the five admission lines and states, per run, whether a run can start. It does not create a one-use admission bound to an exact batch and UTC window for any run, because none of the five has the inputs that such an admission must name (`prereg` freeze record contents, `R2-L2-C-protocol.md` section 15). An admission issued without them would bind to nothing. The approval stands: when the inputs below exist, the run needs no further owner step, only its freeze record, which names the batch, the window and the limits. Per-run caps stay the ones in each protocol; the USD 10 cap on paid calls is shared and unchanged. No shared or production data is written by any run named here.

| Line | Owner step | Inputs still missing (named holder) | Can start now |
|---|---|---|---|
| M3 R3-L2 (about 3 GPU-h, local Qwen3.5-4B) | covered | frozen protocol, protected cohort, native launch entry point (line author, evaluator custodian, runner owner) | No |
| M3 R3-L5 (about 4 GPU-h; the lane's decision is 3, the lower figure) | covered | N2 sealed (custodian, X42 row 167), native launcher (L5 author) | No |
| M4 L2-C, L3-C, L4-C freezes | covered; scope rulings decided by the line author under OD4 (L3 primary C; L2 E out of scope; L4 section 16 lock open) | numeric OPEN items with no repo source (sizes, fractions, seeds, pilot SD and ICC), custodian splits, the approved variance pilot (unreleased, ADM:136), independent review of each protocol | No: a freeze with invented numbers is refused |
| M5 L4-E, L8-D | covered | trainer's schedule and price; the 13.5 h ceiling exceeds the 9.5 h residual, so a smaller valid tranche must be priced by the trainer | No |
| M6 | covered | allocation placement, host transport, cost receipts (author, custodian, resource reviewer) | No |
| M9 | covered | eligible supported components, allocation, a frozen EP-1 (EP-1 needs Pilot 4 first) | No |

Order that the inputs unlock: Pilot 4 (needs `MURMURATION_EP1_KEY`, unset in this session) then EP-1 freeze then M9; custodian binding for N2 then L5; line-author numbers and custodian splits then the L2/L3/L4 freezes; trainer price then M5. None of these is a grant, an admission or an acceptance that the lane can supply itself.
