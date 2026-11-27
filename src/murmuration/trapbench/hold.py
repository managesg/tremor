import sys

from tremor.trapbench import hold as _m

sys.modules[__name__] = _m  # same module object as tremor.trapbench.hold
