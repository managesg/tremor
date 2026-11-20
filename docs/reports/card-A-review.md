# Card A review (EP-1 play arm, paraphrase and leakage)

- reviewer: Opus 5.5 (model reviewer, independent of the card author; the owner may override)
- date: 2026-11-20
- card: `practices/A.md`, version 1, 337 bytes on disk, body 237 bytes (as `practice.load` returns it)
- card sha256 (whole file, the bytes `ep1._preflight` passes to `check_card`): 9875048b79b8585397b44f3c89fddae8cd733dfc318fee99be7d3912f06b3e25
- scorer: `src/murmuration/trapbench/alloc.py`, sha256 91b4d8938dfdb6fb0bd7a738aaa5c66fa1014d476167debf73fb88684a190620 (read at this hash; another agent may be editing it, so this review holds for this scorer version)
- also read: `src/murmuration/cardcheck.py`, `prereg/EP1.md` (sections 6, 7, 13, 14 and the round rules), `practices/pilot/states_the_check.md`, `practices/pilot/keyword_stuffed.md`, `src/murmuration/practice.py` (`neutral`), `src/murmuration/enforce.py` (`claim_before_work`, A V1), `src/murmuration/ep1.py` (`_preflight`)

## cardcheck result (before this file existed)

`python3 -B -I -c` with `cardcheck.check_card(<full A.md text>)`, kind `play`:

```
{'ok': False, 'hits': [], 'reasons': ['paraphrase review not recorded (reviewer path and reviewed_sha256 required)'],
 'paraphrase_review_required': True, 'sha256': '9875048b79b8585397b44f3c89fddae8cd733dfc318fee99be7d3912f06b3e25'}
```

No banned scorer word hits. The only failing reason is the missing review, which this file supplies.
`match_report` on the card body and `practice.neutral(card)`: 237 and 237 bytes, spread 0, ok.

## What the scorer checks (alloc.py at the hash above)

Accepted `work` events on task ids in the set; an answer passes only as a JSON integer equal to the
expected sum; `distinct_passing` (Y numerator) = distinct tasks with a passing work event;
`surviving_passing` = per `name` only the last accepted writer survives; `duplicates` = work events
beyond one per task; `name_collisions`; `extra_work_events` (more than one work event per agent) and
at most `slots` work events decide `valid`.

## Per-sentence verdicts

1. "Before you start work, claim one unclaimed task on the board."
   **OK.** This is the practice itself (claim before work). It names no scorer field, no answer, no
   name rule, no passing condition. "unclaimed" points away from held tasks, which is the practice,
   not the answer key.
2. "Claim only one at a time."
   **OK.** Not a scorer predicate. Round rules already allow at most one claim per round in every arm,
   and the loop makes `extra_work_events` > 0 impossible, so this sentence cannot move `valid`. It is a
   small addition beyond the bare practice and beyond V1 (see section 3), with negligible effect on Y.
3. "If another agent already holds a claim, pick a different task."
   **Paraphrase risk (accepted as inherent).** Near in meaning to the scorer's distinctness
   (`distinct_passing`, `duplicates`), as `cardcheck.py` and EP1 section 6 already state. It is also
   the second half of the practice ("do not work on a task someone else has claimed") and the exact
   condition V1 refuses (`duplicate_claim`). Any faithful statement of claim-before-work implies
   "spread out"; removing that would remove the practice. It does not state that only distinct tasks
   count, that a duplicate is worth nothing, or anything about answers, names or clobber. It tells the
   agent what to do on the board, not how the result is graded.
4. "Release your claim when the task is done or when you are stuck, so others can take it."
   **OK for Y; minor coaching.** Not a scorer predicate. It goes beyond "claim before work" and beyond
   V1, which has no release rule. Within 2 rounds a release cannot hand a task to another agent before
   the single work slot, so the effect on Y is nil. It can move the false-done secondary and the
   board-error release refusals (a release of a claim not won), so those per-arm counts should be read
   with this sentence in mind.

## Questions asked

(1) Leak. The card does not state or restate the scorer: no mention of passing, answers, integer
form, distinct counting, duplicates being worthless, names, collisions, last-writer clobber, rejection
or slots. Compared with `states_the_check.md` (which states each of those) it is far from an answer
key. The one paraphrase is sentence 3, which is the practice itself. The play arm measures a
coordination norm, with the stated limit that the norm and the metric point the same way by design
(the card `measures: duplicate_work_rate, claim_collisions`).

(2) Faithfulness. Sentences 1 and 3 are a faithful, uncoached statement of claim-before-work.
Sentences 2 and 4 add one-at-a-time and release etiquette. Both are ordinary parts of a claim board
practice, carry no grading content, and do not give the agent a strategy beyond the practice. Mild
extra, not coaching toward the metric.

(3) Neutrality and comparison. Byte match with the neutral twin holds (237 = 237); the twin is filler
words, not prose (EP1 section 14 already states that bytes are not tokens). Against the code arm,
V1 enforces exactly sentences 1 and 3 (no claim on another's item; work needs own claim). Sentences
2 and 4 have no code counterpart, so `play` vs `code` compares "rule plus two etiquette lines" with
"rule". For Y this asymmetry is negligible (sentence 2 is structurally enforced in every arm,
sentence 4 cannot act before the work slot). It should be disclosed for the false-done and refusal
secondaries.

## Overall verdict

**APPROVE with the stated paraphrase limit.** No answer-key leak. Sentence 3 paraphrases the
scorer's distinctness, which is inherent to the practice and already recorded in EP1 sections 6 and
14 and `cardcheck.py`; this review lowers that risk and does not remove it. The instrument pilot
(`states_the_check` vs card A) remains the check on a gross leak. Disclose that sentences 2 and 4
have no V1 counterpart when reading secondaries.

Optional, not required: if the owner wants the card to match V1 exactly, a version 2 could read
(166 bytes, well under 600; it would be a new card version, need a new review and change the
237-byte figure in EP1):
"Before you start work, claim one unclaimed task on the board. Work only on a task you have
claimed. If another agent already holds a claim on a task, do not claim it."

reviewed_sha256: 9875048b79b8585397b44f3c89fddae8cd733dfc318fee99be7d3912f06b3e25

## Addendum 2026-11-20 (orchestrator, Opus 5.5): scorer changed, card unchanged

The card bytes are unchanged: `practices/A.md` sha256 is still
9875048b79b8585397b44f3c89fddae8cd733dfc318fee99be7d3912f06b3e25. The scorer changed after this review:
`src/murmuration/trapbench/alloc.py` is now sha256
07ae29d898ee57efea40f02116ab6157d8920350637ea0293a152a9e3988932f (was 91b4d893...0620). The changes are:
- answers pass only as JSON integers;
- unknown-task actions are no-ops (`unknown_task_events`);
- input is the episode action log only, and a malformed event makes the log invalid;
- option C adds `extra_work_events`, `valid`, and Y = distinct_passing / slots, or void.

Re-check: `cardcheck.check_card(kind="play", reviewer=this file, reviewed_sha256=9875048b...)` returns
`ok: True, hits: []`. All new scorer field names are in BANNED, and the card uses none of them.

New interaction considered: under option C, a second accepted work by the same agent voids the episode.
Could the card's "Claim only one at a time" therefore move validity in the play arm only? No.
`team_claude.ROUND_ORDER` allows work only in round 2, and allows at most one work per reply. So
`extra_work_events` is 0 by construction in all three arms. The line can still move the false-done and
release-refusal read-offs, as already noted.

Verdict unchanged: **APPROVE with the stated paraphrase limit**, for scorer sha256 07ae29d8...932f.
