import sys

from tremor import readouts as _m

sys.modules[__name__] = _m  # same module object as tremor.readouts
