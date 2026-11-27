# Owner-run packet: make one TREMOR checkout (the murmuration directory becomes `tremor`)

Revised 2026-11-27 after review. Agents never delete source folders (Safety rule 1): this packet only
prepares commands for Alejandro. Every step is a rename, a fetch or a backup; nothing is deleted.
Facts come from read-only commands run 2026-11-27 (no network). Counts move: re-run the commands.

## 1. Verified facts (re-run to refresh)

| Path (under ~/SeaBridgeAI) | Branch | Remote | `git status --short` | `??` | du -sh |
|---|---|---|---|---|---|
| `murmuration` (lab) | `master` | none | 288 lines (206 tracked changes, 82 untracked) | 82 | 25G |
| `tremor` (clone) | `main` | origin https://github.com/managesg/tremor.git | 0 | 0 | 45M |
| `tremor-relay-release-20261122` (worktree of tremor) | detached @ a99cddd | same repo | 0 | 0 | 8.7M |

Refresh: `for d in murmuration tremor tremor-relay-release-20261122; do echo $d; git -C ~/SeaBridgeAI/$d rev-parse --short HEAD; git -C ~/SeaBridgeAI/$d rev-list --count HEAD; git -C ~/SeaBridgeAI/$d status --short | wc -l; done`
(at preparation time murmuration and tremor were both at the same HEAD, 85c05a0).

- Design defect of the earlier draft: `tremor` is a clean 45M clone; `murmuration` alone holds `data/`
  (14G), `runs/` (11G), `coordinator-outbox/`, the untracked files and the modified files. Making
  `tremor` the single checkout would strand them. So the **murmuration directory becomes the single
  checkout**, renamed to `tremor`.
- `git worktree list` (in tremor): tremor [main], tremor-relay-release-20261122 (detached HEAD a99cddd).
- a99cddd ("docs: distinguish Pilot 3 clearance and generation limits") and 3f674dd ("test: publish
  replayable scripted relay controls") are on local branch `tremor/pilot3-clearance-copy` only;
  `git branch -r --contains a99cddd` printed nothing. They are NOT on origin.
- murmuration has no remote (`git remote -v` printed nothing); `origin/main` does not exist there.
- No D: mount (`/mnt/d`, `/d` absent). Backup path is the owner's choice.
- Whether GitHub origin still equals the last fetched tip, whether `data`/`runs` exist elsewhere, and
  which sessions are open now: UNVERIFIED.

## 2. Step 1: save a99cddd (+3f674dd) first

Either push `tremor/pilot3-clearance-copy` from the tremor clone (a push is gated: Safety rule 7, only
Alejandro decides), or bundle it and check the bundle:

```bash
BK=/path/chosen/by/owner/tremor-retire-20261127     # define first; every later command uses it
mkdir -p "$BK"
git -C ~/SeaBridgeAI/tremor bundle create "$BK/pilot3.bundle" tremor/pilot3-clearance-copy
git -C ~/SeaBridgeAI/tremor bundle verify "$BK/pilot3.bundle"     # must print "is okay"
```

## 3. Step 2: preconditions

- [ ] Step 1 done (bundle verified, or the branch pushed).
- [ ] Stop every session whose cwd is murmuration or the worktree, then
      `ls -l /proc/*/cwd 2>/dev/null | grep -E 'murmuration|tremor-relay'` prints nothing (it lists pids).
      Close the lane chat or its Orca terminal; do not start a second session for the lane.
- [ ] Decide on the 288 changed paths in murmuration: they stay in place (the rename keeps them), so
      nothing is lost; commit them later under the lane's normal rules.

## 4. Optional backup (the directory is only renamed, not changed)

A tar of the whole 25G murmuration directory is OPTIONAL. If wanted, the command checks free space first:

```bash
need=30; have=$(df --output=avail -B1G "$BK" | tail -1 | tr -dc 0-9)
[ "$have" -ge "$need" ] || { echo "only ${have}G free at $BK, need ${need}G"; exit 1; }
tar -cf "$BK/murmuration.tar" -C ~/SeaBridgeAI murmuration
( cd "$BK" && sha256sum murmuration.tar pilot3.bundle > SHA256SUMS && sha256sum -c SHA256SUMS )
```
Run `df -h "$BK"` first and read it. Tar duration: UNVERIFIED.

## 5. Step 3: retire the small clones, then rename murmuration to tremor

Order matters: the worktree is registered inside `tremor/.git`, so move it with git while `tremor` is
still in place (`git worktree move` is the safe route). Do not run `git worktree prune` here: prune
only drops registrations for worktree paths that no longer exist, and it is needed only if the owner
moved the worktree by plain `mv` (then run `git -C ~/SeaBridgeAI/tremor.retired-20261127 worktree repair <new-path>`
rather than prune, to keep the link).

```bash
cd ~/SeaBridgeAI
git -C tremor worktree move ../tremor-relay-release-20261122 ../tremor-relay-release-20261122.retired-20261127
mv tremor tremor.retired-20261127
mv murmuration tremor
```

## 6. Step 4: attach the remote in the renamed directory (owner-run)

```bash
cd ~/SeaBridgeAI/tremor
git remote add origin https://github.com/managesg/tremor.git
git fetch origin
git fetch "$BK/pilot3.bundle" tremor/pilot3-clearance-copy:refs/heads/tremor/pilot3-clearance-copy   # only if not pushed
git status -sb
git log --oneline origin/main..HEAD
git branch -vv
```
Check: `git status -sb` shows `master` ahead of nothing or only by commits you expect (no upstream is set;
`master` is not `origin/main`, so compare with `git log origin/main..HEAD` and `HEAD..origin/main`). Push
only after this check, and only by the owner under rule 7. How local `master` relates to `origin/main`
(same history or not) is UNVERIFIED until the fetch runs.

## 7. Optional compatibility link

Historical handoffs (about 40, UNVERIFIED count) and lane checklists name `~/SeaBridgeAI/murmuration/...`.
They keep working if the owner re-creates the old name as a link (reversible, no cost):
`cd ~/SeaBridgeAI && ln -s tremor murmuration`. Remove it later with `rm murmuration` (symlink entry only,
never `rm -r`; Safety rule 1 allows this only with bounded approval, so it is the owner's call).

## 8. Rollback

```bash
cd ~/SeaBridgeAI
rm murmuration 2>/dev/null     # only if the symlink was created; it is a link, not the directory
mv tremor murmuration
mv tremor.retired-20261127 tremor
git -C tremor worktree move ../tremor-relay-release-20261122.retired-20261127 ../tremor-relay-release-20261122
```
(Run the last line from a state where `tremor` is the clone again.) Full restore: `tar -xf "$BK/murmuration.tar" -C <empty dir>`.

## 9. Update after the rename (all UNVERIFIED unless noted)

- Every doc, handoff and outbox path `~/SeaBridgeAI/murmuration/...` now points at the renamed
  directory: either keep the symlink from step 7 or edit the paths (grep `SeaBridgeAI/murmuration`).
  Verified hits so far: `~/.agents/agent-manager/pilot-lanes/outbox/tremor-coordinator-status.md` and the
  inbox `PC_ALL_BLOCKERS_WORKPLAN_V2_20261122-2d2173c9.md`.
- Orca workspace paths for the lane (point at `~/SeaBridgeAI/tremor`), lane checklist, handoffs and the
  owned-paths blocks; `lane-session-check.js tremor` and the supervisor lane config.
- Scripts or tests with absolute paths into `murmuration/` (data and runs locations).
- The murmuration-to-tremor package rename SUBTASK is separate and not done by this packet.
