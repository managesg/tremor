# M10 local release adoption (recorded disposition)

**Authority:** Alejandro approved the existing requests within their conditions, relayed by the Assistant in `msg_1b04c3446d4e`: "M10 local release adoption may proceed within its exact verified 14-patch scope; timer disposition stays with its named executor." The packet is `docs/reports/tremor/OWNER_DECISION_M10_release_and_T7.md`, Decision 2.

## Adopted

The accepted 14-patch local release, 50 files, is now the local release of record. Its inventory is `runs/m10-ordered-release-preflight.ss65l8/RELEASE14.sha256`, sha256 `36ee25cdd265b5337466f72a64d55af907701295bbce3aeeb8a39e8d39b5074a`, re-hashed today.

## Checks run on 2026-11-23, before recording

All commands ran from `/home/adelmar/SeaBridgeAI/murmuration`.

| Check | Result |
| --- | --- |
| `LC_ALL=C bash runs/m10-ordered-release-preflight.ss65l8/verify.sh \| cmp - …/stdout.log` | exit 0, byte-identical. Under the default `en_US.utf8` locale it differs at line 12, the unpinned sort order already recorded in Table A; `LC_ALL=C` is the exact form. |
| `(cd runs/m10-ordered-release-preflight.ss65l8 && sha256sum -c EVIDENCE.sha256)` | exit 0 |
| `bash runs/wednesday-combined-current.y5ahz3/release-check.sh <replay.1rpwFn/release> <fresh path>` | exit 0; reader layouts reported through `WK-1280` and `WK-480` |
| `(cd runs/tremor-chat-intake.f0VZwV && sha256sum -c EVIDENCE.sha256 FRONTEND.sha256)` | exit 0 |

The checks write locally only: `verify.sh` writes a replay folder inside its packet folder, and the release check writes to a fresh scratch path.

## What adoption does not do

Nothing was copied, committed into the release tree, pushed or published. These items stay open with their owners:

- G8 sharing and any publication: separate, named yes.
- GitHub rendering.
- The provider Console totals and the T7 4.0 GPU-hour hold.
- The publication timer: its named executor.

## Rollback

Record a withdrawal note. Adoption changes no file or repository state.
