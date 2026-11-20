# lab/quantum

Two independent classical simulators of Grover search, cross-checked against each other.

- `gatesim.py`: stdlib-only gate-level statevector simulator written here from first principles (H gates, oracle phase flip, diffuser built as H^n, I-2|0><0|, H^n). Convention (from QGrid's docstring only): iteration = D @ O, so a global phase (-1)^k versus the textbook form.
- `data/qgrid/quantum/statevector.py`: QGrid's numpy simulator (owner-approved tool, not its domain). Provenance: QGrid internal project. It has no licence file, so it is imported read-only by file path at test time and is NOT copied into this repo.
- PsiQDK is not usable here: its native simulator wheel is proprietary and has no aarch64 build.

Tests: `lab/tests/test_gatesim.py`, `lab/tests/test_quantum_differential.py` (skips if numpy or data/qgrid is missing; `differential-report.md` records the last result).

No quantum advantage is claimed anywhere: these are classical simulations of an idealised noiseless circuit.
