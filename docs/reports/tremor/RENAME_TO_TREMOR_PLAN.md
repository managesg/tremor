# Rename "murmuration" to TREMOR: plan (owner: Alejandro, 2026-11-27)

The project is called TREMOR. The repository is github.com/managesg/tremor. The lab was developed under
the working name "murmuration"; 258 tracked files mention it (614 mentions, `git grep -c -i murmuration`).

## Done (docs only)
- Root `README.md` is the TREMOR README; the old lab README is `docs/LAB_README.md`, titled "TREMOR lab".
- The root README says TREMOR is the only project name and lists what still carries the old name.

## Still carrying the old name, and why it is not a find-and-replace
1. `src/murmuration/` (Python package) and every `from murmuration` import in `lab/` and `tests/`.
2. `MURMURATION_EP1_KEY` (`src/murmuration/ep1.py:49`): the key holder sets this name; renaming it
   changes what the holder must set.
3. `prereg/*.md` and `docs/reports/tremor/*`: they cite `src/murmuration/...` paths. The Pilot 4
   preflight manifest and the admission record pin sha256 values of these files, so editing them
   invalidates the pins.
4. This host's checkout directory `~/SeaBridgeAI/murmuration` (other sessions have it as their cwd).

## Proposed steps (each needs Alejandro's yes before the paid window closes, 2026-11-28T23:59Z)
1. Push this history to managesg/tremor (gate row open, owner).
2. Rename the package `murmuration` -> `tremor` with a compatibility shim `murmuration` that re-exports it,
   so old commands keep working; accept `TREMOR_EP1_KEY` and, for one release, `MURMURATION_EP1_KEY`.
3. Re-pin: regenerate the Pilot 4 preflight manifest and the admission record hashes, re-run the full
   lab and package suites on a clean archive, and re-review the pins (Opus: pins are a safety control).
4. After the push, `~/SeaBridgeAI/tremor` fast-forwards to this history and becomes the single
   checkout; retiring the `murmuration` and `tremor-relay-release-20261122` directories is a deletion
   that Alejandro runs himself (exact commands prepared at that time, with a backup).
