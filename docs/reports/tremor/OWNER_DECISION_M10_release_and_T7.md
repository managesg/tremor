# M10 owner decision packet: resources, release adoption, publication timer

Prepared November 23, 2026 on `seabridge-spark` (read-only; no git writes, no network, no timer or unit change). Acceptance stays 1/10. Paths are relative to `/home/adelmar/SeaBridgeAI/murmuration` unless absolute. Anything not recorded in a cited file is stated as unknown.

## Summary

| # | Decision | Owner | Recommendation |
|---|----------|-------|----------------|
| 1 | Resource reconciliation: paste Console totals; keep or dispose the provisional 4.0 GPU-hour T7 hold | Alejandro (Console reading); resource owner and claims reviewer (T7 disposition) | Paste the Console numbers listed below. Keep the 4.0 hold until evidence binds T7 containers to GPU time and cleanup. Do not release it on the current evidence. |
| 2 | Adopt the accepted 14-patch local release as the local release of record | Release owner and Alejandro | Adopt locally (a recorded disposition only). Keep G8 sharing and any publication as a separate, later yes. |
| 3 | Durable hold on the enabled one-shot timer `tremor-public-update-20261122.timer` | Alejandro (user-manager owner) | Run `systemctl --user disable` on the timer. Do not use `mask`. |

## Decision 1. Resource reconciliation (GPU ledger and provider Console)

**Decision and owner.** Alejandro reads the provider Console and pastes the totals below into the chat. The resource owner and claims reviewer then record (a) the hosted-API reconciliation and (b) a disposition of the provisional T7 hold (`docs/reports/workplan-ep/Execution-plan-20261123.md:43-44`; blocker owners per `docs/reports/TREMOR_GOAL_AND_PLAN_20261123.md:52-54`). D6 defers the canary-versus-Console reconciliation until publication (`docs/reports/workplan-ep/Pilot4-pricing-verification-gates.md:24`).

**GPU-hour ledger as recorded (copied exactly).**

| Item | Figure | Source |
|------|--------|--------|
| R2 native GPU | 0.100000 hours reserved, 0.023123 charged, 0.076877 released; "No outstanding hold on this admission" | `docs/reports/workplan-ep/Portfolio-evidence-and-resource-reconciliation-20261121.md:257` |
| R2 settlement time | 83.24227687099483 seconds reconciles to 0.023123 GPU-hours | `docs/reports/workplan-ep/R3-resource-accounting-audit.md:9` |
| T7 historical GPU | 2.405372 retained generation hours; 8,535.6347455 seconds from three completed arms plus 123.7038407 seconds from two probes; 8,655-second wall subtotal for the three containers includes startup and overlaps the completed-arm time and excludes the probes | `Portfolio-evidence-and-resource-reconciliation-20261121.md:258` |
| T7 provisional hold | 4.0 GPU-hours, retained "Exact GPU attachment, full attempted occupancy and cleanup remain unavailable" | same file `:258`; also `Execution-plan-20261123.md:1542`, `:1585`; `Spark-allocation-rephase.md:3` |
| Program planning balance | 65.976877 GPU-hours after the settled R2 charge and the T7 hold; R2/R3 share 7.476877; L1-L8 nominal ceilings total 49 | `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`; `Spark-allocation-rephase.md:4-6` |
| Proposed SmolLM3 reserve | 0.1 hour leaves 9.4 in that row and 65.876877 in the historical program model; not yet a binding reservation | `Portfolio-evidence-and-resource-reconciliation-20261121.md:259`; `Execution-plan-20261123.md:487-489` |

Note: 2.405372 hours of retained generation time is a floor on measured activity, not billed occupancy. The 4.0 hold is a planning number the docs call provisional; the files do not state how 4.0 was derived, so it is not re-derived here.

**What evidence would settle T7 (per the recorded gaps).** A record that joins each of the three named T7 container instances to its Docker runtime ID, its GPU attachment interval and its terminal cleanup. The journal replay found 11 named T7 endpoint joins and 28 Docker task-deletion records whose runtime IDs cannot be linked to the T7 names, plus three unassigned NVIDIA memory warnings (`Portfolio...:258`; `Execution-plan-20261123.md:1580-1585`; `runs/t7-dated-daemon.oo7Qwv/OWNER.md`). The monitor replay saw 126 arm-name sightings that do not bind container instances (`Execution-plan-20261123.md:1537-1542`, `runs/t7-monitor-clock-sightings.vof1t2/OWNER.md`). Absent such a join, the options are: keep the hold (default) or the resource owner records a named, reasoned release or a different figure. No agent may invent that figure.

**Provider Console totals the owner must read and paste (the agent cannot access them).** The provider is the Anthropic Console (`docs/reports/ep-approvals.md:40,80,97`). The repo does not name the exact Console page labels, so read the page that shows cost and token usage for the workspace/key used by the Murmuration spend ledgers and state the page name and the "data as of" time you read:
1. Total USD cost, all dates, for that workspace or key. The local comparison value is USD 0.0413027 (stored sum 0.041302700000000000620), 417 paired charges (`runs/m10-api-repricing.FKG1Eo/report.json`; `Portfolio...:260`).
2. If the page allows a date filter, the USD cost and input/output tokens per batch, to compare with the ledger: canary 0.0046625 USD, 46605 in / 4 out; pilot 0.0114893 USD, 41088 / 14761; pilot2 0.0069008 USD, 41238 / 5554; pilot3 0.0182501 USD, 112706 / 13959 (same report.json, `by_batch`). Batch dates are not in this packet; use the ledger timestamps in `runs/spend/*.jsonl`.
3. Current available budget or credit balance, and the workspace spend limit (the approvals call for a limit of USD 10 or less; `docs/reports/ep-approvals.md:40,80`). The report records `current_available_budget_usd: null` and `provider_console_total_usd: null`, so both are unknown today.
Console data lags (it did not show a canary 21 minutes old; `ep-approvals.md:97`), so note the read time. Unknown stays unknown: if a number cannot be read, paste "not available", not an estimate.

**Procedure and commands (local writes only: no network, no spend).**
- Before: `bash runs/portfolio-api-nested.x81FKM/verify.sh` (regenerates the API receipt from the four local ledgers; prints "Retained local API accounting report reproduced byte for byte."), and `sha256sum -c runs/portfolio-reconciliation.BNttQL/evidence.sha256`.
- Record step (manual): the owner pastes the Console numbers in chat; the claims reviewer records them with the read time and compares to the ledger. Pilot 4's own Console criterion is separate (criterion 7, `Pilot4-pricing-verification-gates.md:24`).
- After: rerun the two commands above and confirm they still pass; the stored report must be unchanged (this decision adds a record, it does not change `report.json`).

**Scope.** Accounting records only. No spend, run, reservation or ledger edit. Does not authorize Pilot 4, EP-1 or any paid call (`report.json`: `authorizes_execution: false`).

**Rollback.** Withdraw or supersede the recorded disposition by a new dated note; the original ledgers and reports are retained byte for byte.

**Risk.** A mismatch between Console and ledger would show unrecorded or mispriced spend (a risk of undercounting, not of new spend). Releasing the T7 hold without evidence would overstate remaining GPU budget; keeping it only reduces planning headroom.

**Recommendation.** Paste the Console numbers; keep the 4.0 hold; do not reduce it without the container-to-GPU-to-cleanup join.

## Decision 2. Adopt the accepted 14-patch local release

**Decision and owner.** Release owner and Alejandro decide whether the accepted 14-patch candidate becomes the local release of record. Adoption is a recorded disposition. G8 sharing and any publication need their own, later approval (`docs/reports/TREMOR_GOAL_AND_PLAN_20261123.md:53`; `Execution-plan-20261123.md:2853-2869`).

**Accepted evidence.**
- Candidate: `runs/m10-ordered-release-preflight.ss65l8/replay.1rpwFn/release` (50 files), built from clean staging base `a99cddd1301905566e09a25b10aa583af9867ad3` by applying fourteen patches (`runs/m10-ordered-release-preflight.ss65l8/OWNER.md`).
- Inventory `runs/m10-ordered-release-preflight.ss65l8/RELEASE14.sha256`: 50 lines, SHA-256 `36ee25cdd265b5337466f72a64d55af907701295bbce3aeeb8a39e8d39b5074a` (re-hashed now).
- Accepted packet `runs/tremor-chat-intake.f0VZwV`: `OWNER.md` SHA-256 `3d744345798f1f132bfa5fd4acbc1444e8cee1b0a3abdc439053699b8671d45f` (re-hashed now), `EVIDENCE.sha256` prefix 6590b891, `FRONTEND.sha256` prefix 6800c876 (prefixes as recorded in `Execution-plan-20261123.md:2855-2863`; full values not re-verified here). Assistant acceptance `msg_805f62c63b42` (relayed by PC) rehashed 7/7 intake, 6/6 frontend and 50/50 release files, at local scope only.
- Reader replay: eight pages, 38 local references, six layouts, exit 0 (`runs/tremor-chat-intake.f0VZwV/FRONTEND.md`).

**What adopting means locally.** The owner records, in chat and in the handoff, that this 50-file tree with inventory hash `36ee25cd...5074a` is the local release of record. Nothing is copied, committed, pushed or published by adoption. The staged repo `/home/adelmar/SeaBridgeAI/tremor-relay-release-20261122` stays at `a99cddd` (checked clean today; `git status --porcelain` empty). Applying the 14 patches into that repo, or committing them, is a separate local step needing its own ask. No such command is recorded in the repo, so none is invented here.

**Checks before and after adoption (local writes only).**
```bash
cd /home/adelmar/SeaBridgeAI/murmuration
set -o pipefail
bash runs/m10-ordered-release-preflight.ss65l8/verify.sh | cmp - runs/m10-ordered-release-preflight.ss65l8/stdout.log
(cd runs/m10-ordered-release-preflight.ss65l8 && sha256sum -c EVIDENCE.sha256)
bash runs/wednesday-combined-current.y5ahz3/release-check.sh \
  "$PWD/runs/m10-ordered-release-preflight.ss65l8/replay.1rpwFn/release" \
  "$(mktemp -d)/release-check-out"
(cd runs/tremor-chat-intake.f0VZwV && sha256sum -c EVIDENCE.sha256 FRONTEND.sha256)
```
(The last line assumes both manifests use paths relative to that directory; if not, run each as recorded in the packet.) Notes: `verify.sh` writes a `replay.XXXXXX` folder into the packet folder; `release-check.sh` takes `tree output` and runs `mkdir -m 700 "$output"`, so the output path must not exist yet (it is a fresh path under a new temp dir, which you may delete afterwards). Expected: all exit 0 and byte-identical output. Not run for this packet; they were run and recorded by the earlier acceptance.

**Scope.** Local only. Still open and not covered: GitHub rendering, G8 sharing, T7 accounting, Console totals (`runs/m10-final-reader-resume.zX5zc5/OWNER.md`).

**Rollback.** Record a withdrawal note. No file or repo state changes under adoption, so nothing to restore.

**Risk.** Low locally. The risk is a reader treating adoption as clearance to publish; it is not. Also note the timer in Decision 3 targets an older commit (`3f674dd`), not this release.

**Recommendation.** Adopt locally; require a fresh, named yes for G8 and for any push.

## Decision 3. Durable hold on the publication timer

**State today (read-only, November 23).** `systemctl --user list-timers --all` shows `tremor-public-update-20261122.timer` with no NEXT and no LAST. `is-enabled` returns `enabled`; ActiveState `inactive`, Result `success`. The unit is in `/home/adelmar/.config/systemd/user/` (timer sha256 `739d5873...9812d9476`, service sha256 `05e7b94a...c045832a`), linked from `timers.target.wants/`. `OnCalendar=2026-11-22 11:00:00 America/New_York` with `Persistent=true`. The earlier stop is evidenced in `runs/publication-hold-confirmed.HiOLje/` (before: active/waiting, next elapse 11:00 EST; after: inactive, no elapse; persistence readback: `Persistent=yes`, `UnitFileState=enabled`; `evidence.sha256` file hash `9ed28c63...bb5ae9` as cited in its `coordinator-status.md`). The service runs `/home/adelmar/.local/state/tremor-release-20261122/publish.sh`, which ends in `git push origin 3f674dd...:refs/heads/main` to `https://github.com/managesg/tremor.git`. `loginctl` shows `Linger=yes`.

**Risk of leaving it enabled.** The timer was only stopped, not disabled. A user-manager restart, reboot (linger is on) or `systemctl --user start` re-loads an enabled timer; with `Persistent=true` and a past `OnCalendar`, systemd may fire it as a missed run. Mitigation by script design: `publish.sh` first requires the staged repo `HEAD` to equal `3f674dd42dcc89f4a650b88ea9fb728de4162c0c`; the repo is at `a99cddd`, so that guard should fail it, but a restage or checkout to `3f674dd` would remove that protection. A public push is not reversible by this lane. Treat the guard as incidental, not as a hold.

**Decision and owner.** Alejandro runs the commands (user-manager config is owner-controlled; this lane made no durable change).

**Commands (recommended: disable).**
```bash
# before: confirm state
systemctl --user is-enabled tremor-public-update-20261122.timer      # expect: enabled
systemctl --user show tremor-public-update-20261122.timer -p UnitFileState,ActiveState,NextElapseUSecRealtime
# hold: removes the timers.target.wants link, keeps both unit files
systemctl --user disable tremor-public-update-20261122.timer
systemctl --user stop tremor-public-update-20261122.timer            # already inactive; harmless
# after: confirm
systemctl --user is-enabled tremor-public-update-20261122.timer      # expect: disabled
systemctl --user list-timers --all --no-pager | grep tremor-public-update || echo "no next trigger"
sha256sum ~/.config/systemd/user/tremor-public-update-20261122.{timer,service}   # unchanged, as above
```
**Stronger option (not recommended).** `systemctl --user mask tremor-public-update-20261122.timer` fails because a real unit file exists in `~/.config/systemd/user/`; `--force` does not override this (not tested). Masking by replacing the file, if forced some other way, would replace that file with a link to `/dev/null` and lose the unit text. Only use it after copying both unit files elsewhere.

**Undo.** `systemctl --user enable tremor-public-update-20261122.timer` re-creates the wants link; it takes effect at the next timer start (`--now`, a user-manager restart or a reboot with linger), and that start fires the `Persistent=true` catch-up immediately. Do not undo before the owner has separately approved publication; the stale `OnCalendar` date has passed, so re-enabling with `Persistent=true` can trigger an immediate catch-up run. If a publication is ever approved, prefer a new reviewed timer or a manual run of `publish.sh --check` first (it runs `git push --dry-run`, which still contacts GitHub with the stored credentials), after updating the reviewed commit, rather than re-enabling this one.

**Scope.** Only this one timer unit. No change to the service file, `publish.sh`, the staged repo, vLLM processes (observed parent 2674, engine 30034 in the hold evidence) or other timers.

**Rollback / checks.** As above; the unit files remain on disk and their hashes can be compared before and after.

**Recommendation.** Disable now; leave the unit files in place; keep publication as a separate approval.

## Not verified here
Console values, the T7 container-to-GPU join, GitHub rendering, whether `systemctl --user disable` behaves exactly as expected on this host (not run), the full `EVIDENCE.sha256` and `FRONTEND.sha256` hashes, and the Murmuration HEAD (now `4442b97`; the plan recorded `d897860`).
