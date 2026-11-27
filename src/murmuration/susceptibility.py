import sys

from tremor import susceptibility as _m

sys.modules[__name__] = _m  # same module object as tremor.susceptibility
