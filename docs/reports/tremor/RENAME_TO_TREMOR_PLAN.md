# Rename "murmuration" to TREMOR: plan (owner: Alejandro, 2026-11-27)

The project is called TREMOR. The repository is github.com/managesg/tremor. The lab was developed under
the working name "murmuration"; 103 tracked files mention it (409 matching lines, `git grep -c -i murmuration | awk -F: '{f++;n+=$NF} END{print f,n}'`, 2026-11-27 at 260bbaa).

## Done (docs only)
- Root `README.md` is the TREMOR README; the old lab README is `docs/LAB_README.md`, titled "TREMOR lab".
- The root README says TREMOR is the only project name and lists what still carries the old name.
- Package renamed (committed in 32857d3, local, not pushed): `src/murmuration/` is now `src/tremor/`, and every import, `-m` call and
  `src/murmuration` path in tracked `.py` files under `src/`, `lab/` and `tests/` uses `tremor`. A shim package
  `src/murmuration/` (`__init__.py`, `__main__.py`) makes `murmuration.<submodule>` the same module object as
  `tremor.<submodule>` and keeps `python -m murmuration` working (`tests/test_murmuration_shim.py`).
- Key variable: `ep1.KEY_ENV` is now `TREMOR_EP1_KEY`; `MURMURATION_EP1_KEY` (`ep1.LEGACY_KEY_ENV`) is the fallback.
  Same rules (read in `cli` only, never printed). Both set and different: refused by name, values not printed.
  Both set and equal, or empty, behave as one key / unset.
- Citations of `src/murmuration/<file>:<line>` in older docs and in `prereg/*.md` now mean `src/tremor/<file>:<line>`
  (line numbers moved only in `ep1.py` after the key change). `prereg/*.md` and doc citations were not edited, so their sha256 pins stay valid.
- Pins checked: no pin in `pilot4_preflight_manifest`, `tremor_freeze_skeleton`, `tremor_admission_gate`,
  `pilot_clearance` or `spend` names a renamed file. EP-1 `code_tree_hash` in `prereg/EP1.md` is still blank (not frozen);
  it hashes `src/`, `practices/` and `tests/`, so compute it after this rename.

## Still carrying the old name after 32857d3, and why it is not a find-and-replace
(Items 1 and 2 below are the shim and the fallback key; items 3 and 4 are still open.)
1. `src/murmuration/` (Python package) and every `from murmuration` import in `lab/` and `tests/`.
2. `MURMURATION_EP1_KEY` (`src/murmuration/ep1.py:49`): the key holder sets this name; renaming it
   changes what the holder must set.
3. `prereg/*.md` and `docs/reports/tremor/*`: they cite `src/murmuration/...` paths. The Pilot 4
   preflight manifest and the admission record pin sha256 values of these files, so editing them
   invalidates the pins.
4. This host's checkout directory `~/SeaBridgeAI/murmuration` (other sessions have it as their cwd).

## Steps and status (open steps need Alejandro's yes before the paid window closes, 2026-11-28T23:59Z)
1. OPEN: push this history to managesg/tremor (gate row open, owner; rule 7).
2. DONE in 32857d3: rename the package `murmuration` -> `tremor` with a compatibility shim `murmuration` that re-exports it,
   so old commands keep working; accept `TREMOR_EP1_KEY` and, for one release, `MURMURATION_EP1_KEY`.
3. OPEN (partly): re-pin: regenerate the Pilot 4 preflight manifest and the admission record hashes, re-run the full
   lab and package suites on a clean archive, and re-review the pins (Opus: pins are a safety control).
4. OPEN (owner-run, see OWNER_RUN_RETIRE_OLD_CHECKOUTS.md): after the push, `~/SeaBridgeAI/tremor` fast-forwards to this history and becomes the single
   checkout; retiring the `murmuration` and `tremor-relay-release-20261122` directories is a deletion
   that Alejandro runs himself (exact commands prepared at that time, with a backup).
