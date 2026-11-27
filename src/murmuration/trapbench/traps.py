import sys

from tremor.trapbench import traps as _m

sys.modules[__name__] = _m  # same module object as tremor.trapbench.traps
