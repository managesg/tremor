import sys

from tremor import trapbench as _m
from tremor.trapbench import alloc, alloc2, hold, poison, sqlseq, traps

# the package alias must also own its submodule names, else the import system re-executes tremor's files under them
for _n in ('alloc', 'alloc2', 'hold', 'poison', 'sqlseq', 'traps'):
    sys.modules[f"{__name__}.{_n}"] = sys.modules[f"tremor.trapbench.{_n}"]
sys.modules[__name__] = _m  # same module object as tremor.trapbench
