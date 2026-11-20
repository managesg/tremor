# Decision memo: integrating the Anthropic research areas

2026-11-19. Author: Fable 5.2 (planner). Nothing was built, run or spent by me. Details:
`docs/ALIGNMENT-INTEGRATION.md` (the mapping) and `docs/WORKPLAN-ALIGN.md` (the work order).

## The short version

Our testbed bears directly on three things in the Anthropic program: governance of multi-agent teams
(direction 3.17), defensive robustness of shared memory (3.13), and monitor and evaluator hygiene
(3.6, the frontier red team's lessons). It bears partly on eight more directions and not at all on
six, including AI welfare, offensive security and anything that needs training. Two new papers from
the same group (*Aligning AI Teams*, *Worse Together*) already compare soft practices with structural
ones in real model teams, so our novelty claim is narrower than `EMERGENCE-PROGRAM.md` says.

## Decisions (yes or no)

| # | Decision | Recommendation | If no |
|---|---|---|---|
| 1 | Adopt the nine "will not build" rules and the 15 defensive tests as project rules | **Yes** | The dual-use boundary stays implicit |
| 2 | EP-1 tests practice A alone. Practice C gets clobber scoring (same name, last writer survives) and stays at the scripted rung; name herding is a free read-off in EP-1 | **Yes** | EP-1 mixes two practices and C's index stays 0/0 |
| 3 | Redefine practice D on a new "hold notice" task (information arrives after the plan), instead of cutting D | **Yes** | D is cut: on the current task it is the same as A |
| 4 | Add three cards: H (injection warning), S (published safety spec), L (designated safety lead). Build no peer-critique or group-chat card | **Yes** | The two team-alignment papers have no counterpart in our tests |
| 5 | Read rule 2 ("no self-propagating agent code, even in simulation") as allowing card H's test: one fixed, inert, hand-written marker sentence in a temporary toy store, never optimised or evolved, agents with no tools | **Yes, with those limits** | Card H is tested with scripted agents only |
| 6 | Narrow the novelty wording now, and open the two papers and `magelab` in full (zero cost) before the EP-1 pre-registration is frozen | **Yes** | We risk claiming a comparison that is already published |
| 7 | Build the instruments for two follow-up batches now (EP-1b: spec against lead; EP-1c: card H), with no spend approved until each is asked for by name | **Yes** | Only EP-1 is prepared; the alignment tie-in waits |
| 8 | Keep the weight-edit thread at arms 0, A, B, C, D plus one read-only projection monitor; keep "a frontier model writes the edit" (arm E) cut unless the edit beats the decoding fixes | **Yes** | Arm E would need its own budget, which nobody has priced |

None of these asks for money or raises a limit. The owner's USD 10 ceiling, the USD 9 code stop and
the EP-1 sub-cap of USD 5 are unchanged.

## What I could not verify

- **The two key papers.** *Aligning AI Teams* was read as an abstract, *Worse Together* as a blog
  post. Their numbers, tasks and released code were not opened. Task G0-3 fixes this.
- **All outside numbers** are first-party and unreplicated; many pages were read in part (notes 20
  to 22 list which).
- **The code.** I ran no test. I read file lists and these modules: `board.py`, `orders.py` (head),
  `perturb.py` (head), `consolidate.py`, `trapbench/poison.py`, `trapbench/alloc.py`,
  `train/t7_arms.py`, and function lists of the rest. The 186-test count is from the rung-0 note.
- **`cell.py`, `router.py`, `perturb.py`** differ today from the bytes the A0-1 review failed. I did
  not check whether the ranked fixes are all in.
- **The spend code.** The last review says "not accepted, one blocking fix". I do not know whether
  the fix landed.
- **T7.** Arm 0's figures (61.1 tokens per second, 0.116 joules per token GPU-only, all 20 problems
  at the 8,192 cap) come from one output line. I did not read its accuracy, arm B's progress, or
  whether the memory log shows the leak.
- **My rung-0 numbers** for the new instruments (D, S, L, H, C) were derived by hand. Opus must
  recompute them by enumeration (task G0-4).
- **Research notes 13 to 17** were read in their summary and test-design sections, note 18 in part.
- **The key.** `ep-approvals.md` records that the key was read from a live-environment file of
  another repo. WORKPLAN-EP asks for a project-only variable set by the owner. That question is
  still open and I did not look at any environment file.

## Order of work for tomorrow

1. Opus: re-verify `cell.py`, `router.py`, `perturb.py` at today's bytes (G0-1), and give the verdict
   on the spend fix (G0-2).
2. Haiku fetches, Opus reads: the two papers and `magelab`; write the novelty check (G0-3).
3. Sonnet builders in parallel, disjoint files: clobber scoring (S1), hold task (S2), cards D v2, H,
   S, L (S3), evaluator seal (S4), two monitors (S5), note canary and relay lint (S6), egress
   assertions (S7).
4. Opus: exact rung-0 expectations for the new instruments (G0-4).
5. Sonnet, in sequence: enforcement (A7'), adopters and team loop (A6'), rung-0 driver (A9').
6. Opus: gate G1 on the rung-0 report. Nothing paid before it.
7. Then, and only with the owner's verbatim approval on file: the EP-1 pre-registration (practice A
   only), freeze, one canary call, EP-1.
8. T7: let the running smoke finish; change nothing in `train/`. Read arms 0 and B together when B is
   done. The full run stays parked with every other GPU item.

Price sheet: the current one is refused after 2026-11-22, so re-fetch it within 3 days of the canary.
