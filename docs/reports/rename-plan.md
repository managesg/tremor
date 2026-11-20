# Rename plan: murmuration to Sortie (2026-11-19)

Author: Fable 5.2 (planner). **Plan only. Nothing was renamed, moved, committed or run.**
Owner decision: the name is Sortie. Not checked: whether the name is free (PyPI, npm, GitHub,
domains, trademarks). "Sortie" is a common English and French word, so other software very
likely uses it (from memory, unverified). Search before anything is published (gate G8).

## 0. Facts this plan rests on (read-only checks, 2026-11-19)

- Repo: `/home/adelmar/SeaBridgeAI/murmuration`, branch `master`, no remote, HEAD `972dee3`,
  many uncommitted files from several agents.
- Package: `src/murmuration/` (17 `.py` files incl. `trapbench/`). No `pyproject.toml`; the
  package is found through `PYTHONPATH=src` and a `sys.path` insert in each test.
- `train/*.py` derive every host path from `__file__` (`ROOT`). No host path is hard-coded.
  Hard-coded names: the image tag `murmuration-t7:1`, the container prefix `murm-t7-`
  (`train/t7_host.py` lines 61 and 70) and the User-Agent `murmuration-fetch` (`train/fetch.py`).
  Container paths (`/work/...`) do not contain the name.
- `tree_hash` hashes each file's path relative to the root plus its bytes
  (`wave1-acceptance.md` section 1: "the same tree at another checkout location: equal").
  So moving the repo directory does **not** change `code_tree_hash`; renaming
  `src/murmuration/` and editing `train/t7_host.py` **does**.
- Every `code_tree_hash:` line in `prereg/` is blank. No freeze exists yet.
- Orca: repo `8c507fd0-a84c-4760-a3b2-ceebaecf5dcb`, name `murmuration`, registered by that path.
- A T7 smoke container (`murm-t7-arm0`) was running when this was written.

## 1. Risk if done while a job runs

`train/t7_host.py` opens its outputs by absolute path (`ROOT/runs/t7-smoke/...`) during and
after the container run, and the watchdog and memory log do the same. If the directory moves
under it, the power CSV, summary and log writes fail or the run ends without results. The
container's bind mounts would probably survive a directory move (bound at start), but that is
reasoning, not tested. A package rename under a running job changes the files mounted at
`/work/src`. **Do every step only when no job is running and no other agent is editing.**

Also: a rename **after** a freeze would void that freeze (new `code_tree_hash`, new run needed).
**Do Phase A before any pre-registration is frozen.**

## 2. Preconditions (all must hold; stop if one fails)

```
docker ps --filter name=murm-t7 --format '{{.Names}}'     # prints nothing
pgrep -af 't7_host|t7_gen'                                # prints nothing
git -C /home/adelmar/SeaBridgeAI/murmuration status --short   # only files the owner knows about
grep -n '^code_tree_hash:' prereg/*.md                    # every value blank
```

1. The owner confirms: the smoke has ended, the doc reconciliation is finished, and no other
   session is writing in this repo.
2. The owner approves, in the current session: the commits below, and (Phase B) the new
   directory path. Commits and root changes are gated; this plan is not approval.
3. Pending uncommitted work is committed first as its own local commit, staged by path by the
   agent that owns it, so the rename commit contains only the rename.
4. Record the baseline: `PYTHONPATH=src python3 -B -m unittest discover -s tests 2>&1 | tail -3`
   (note the test count; 110 test functions were counted on 2026-11-19, not run) and
   `PYTHONPATH=src python3 -m murmuration manifest --root . --tree src train` (the old tree hash).

## 3. Phase A: in-repo rename (one commit; reversible with `git revert`)

All commands from the repo root.

1. **Package directory.** `mv src/murmuration src/sortie` (plain `mv`, so ignored
   `__pycache__` folders move too and no empty `src/murmuration/` is left behind to shadow
   imports). Check: `test ! -e src/murmuration`.
2. **Imports and module strings**, in code and tests only:
   ```
   grep -rlw murmuration src tests train --include='*.py' | xargs sed -i 's/\bmurmuration\b/sortie/g'
   ```
   This covers `from murmuration ...` (5 source lines, 17 test files), `prog="murmuration"`
   and the User-Agent in `train/fetch.py`. It does **not** match `murmuration_power` in
   `__main__.py` line 15 (the underscore is a word character); change that internal loader
   label by hand to `sortie_power`.
3. **Docker names** in `train/t7_host.py`: after step 2 the image tag reads `sortie-t7:1`.
   Change the container prefix by hand: `"murm-t7-"` to `"sortie-t7-"`. Then add the new tag to
   the existing image; no rebuild, no pull, the old tag stays:
   `docker tag murmuration-t7:1 sortie-t7:1`.
   `train/Dockerfile` does not contain the name; leave it.
4. **CLI module name.** Nothing else to do: `python3 -m sortie` works once the directory is
   renamed. There is no installed entry point.
5. **Living docs and command strings**, edited by hand, not by blanket `sed`, because some
   sentences are about the old name:
   - `README.md` (6 hits): title, commands (`-m sortie`), plus one line "formerly `murmuration`".
   - `prereg/H7.md` (2), `prereg/H8.md` (1): the `-m murmuration` commands and the
     `src/murmuration/trapbench/sqlseq.py` path.
   - `docs/PLAN.md` (18), `docs/WORKPLAN.md` (4), `docs/ARCHITECTURE.md` (2), `docs/VISION.md`
     (2), `docs/SCIENCE.md` (1), `docs/PROPOSAL.md` (2): titles and paths.
   - **Do not change** quoted owner words (`WORKPLAN.md` section 1 quotes the approval verbatim,
     including the old name and path) or the naming rationale in `VISION.md`; rewrite that
     paragraph to say the rename happened.
6. **Historical files stay as they are:** `docs/reports/**`, `docs/research/**`, `runs/**`
   (meta files hold old absolute paths), `data/**`. Add one note,
   `docs/reports/README.md`: "Reports before <date> use the old name `murmuration` and old
   paths `src/murmuration/...`; read them as `sortie`."
7. **Residue check** (expected hits only in the historical folders, the README "formerly"
   line and the quoted approval):
   `grep -rnw murmuration --include='*' . --exclude-dir=.git --exclude-dir=data --exclude-dir=runs --exclude-dir=reports --exclude-dir=research`
8. **Verify** (section 5). Only if green:
9. **Commit**, staged by path, no `--no-verify`, no push, no history rewrite:
   ```
   git add -A src tests train README.md prereg docs/PLAN.md docs/WORKPLAN.md docs/ARCHITECTURE.md \
           docs/VISION.md docs/SCIENCE.md docs/PROPOSAL.md docs/reports/README.md
   git commit -m "refactor: rename package murmuration to sortie"
   ```
   with the session's `Co-Authored-By` trailer. `git show --stat -M HEAD` should list the
   package files as renames.

## 4. Phase B: directory and Orca (optional; can wait or be skipped)

The package rename does not need the directory to move. Phase B changes nothing in git and
nothing in `code_tree_hash`. Skipping it leaves a repo called `murmuration` holding a package
called `sortie`; that is the smallest change and is acceptable until the owner wants more.

1. Owner names the target. Proposed: `/home/adelmar/SeaBridgeAI/sortie` (lower case, matching
   the package). The workspace rule requires approval for root changes.
2. Close every terminal and agent session whose working directory is the old path (owner; a
   lane has one session, and its chat is bound to the workspace, so ask before touching it).
3. `mv /home/adelmar/SeaBridgeAI/murmuration /home/adelmar/SeaBridgeAI/sortie`
   (same filesystem, so it is one rename; read-only weights under `data/hf` move with it).
4. Orca. The CLI help lists `repo add`, `repo show`, `worktree set --display-name` and
   `project setup-update --path --display-name`, and **no** `repo rename` or `repo rm`.
   Re-read `orca --help` at the time, then:
   - if `orca project setups --json` shows a setup for this repo:
     `orca project setup-update --setup <id> --path /home/adelmar/SeaBridgeAI/sortie --display-name Sortie`;
   - otherwise `orca repo add --path /home/adelmar/SeaBridgeAI/sortie`, and the owner removes
     the dead `murmuration` entry in the Orca app. An agent does not delete registrations.
   - Display name only (if Phase B is skipped): `orca worktree set --worktree <selector> --display-name Sortie`.
   Check: `orca repo list` shows the new path; `orca worktree list` resolves.
5. Optional bridge for one session, only if some script or note still uses the old absolute
   path: `ln -s sortie /home/adelmar/SeaBridgeAI/murmuration`. It sits outside the hashed tree.
   Remove it later with `unlink` (the link entry only), after reporting link and target.
6. Update absolute paths in living notes outside the repo (handoff notes, the parent's goal
   record). Not searched here.

## 5. Verification commands (after Phase A, again after Phase B)

```
PYTHONPATH=src python3 -B -m unittest discover -s tests 2>&1 | tail -3   # same count as baseline, OK
PYTHONPATH=src python3 -m sortie --help                                   # exit 0
for c in report synth sweep allowlist hazard tokens memlint coupling manifest trap-gen seq-gen run power-parse; do
  PYTHONPATH=src python3 -m sortie $c --help >/dev/null || echo "FAIL $c"; done
PYTHONPATH=src python3 -m murmuration --help                              # must fail: No module named murmuration
PYTHONPATH=src python3 -m sortie manifest --root . --tree src train       # new tree hash; differs from baseline
docker image inspect sortie-t7:1 --format '{{.Id}}'                       # same id as murmuration-t7:1
git status --short                                                        # clean after the commit
```

Run the subcommand list against `python3 -m sortie --help` first; newer subcommands
(`prereg-check` is named in the README) must be added to the loop. Record the old and new tree
hash in the commit's report. The T7 host script cannot be exercised without the GPU: its
renamed tag and container prefix stay **unverified** until the next approved smoke run.

## 6. Rollback

| Step | Undo |
|---|---|
| Phase A commit | `git revert --no-edit <sha>` (own commit, clean tree). No reset, no force |
| Docker tag | Nothing to undo: the old tag was never removed |
| Phase B move | `mv` back to the old path; `orca project setup-update` or `repo add` for the old path |
| Bridge symlink | `unlink /home/adelmar/SeaBridgeAI/murmuration` |

## 7. Not checked

- Name availability of "Sortie" anywhere.
- Whether Orca keeps chat history when a repo's path changes; whether a `project setup` exists
  for this repo.
- References to the old path outside this repo (other repos' notes, agent memory, shell history).
- Whether tests assert on the image tag or container prefix (grep before step 3).
- No command in this plan was run.

verified: 972dee3 (plus working tree) 2026-11-19
