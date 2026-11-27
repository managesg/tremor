import sys

from tremor.trapbench import alloc2 as _m

sys.modules[__name__] = _m  # same module object as tremor.trapbench.alloc2
