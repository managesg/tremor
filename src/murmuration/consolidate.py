import sys

from tremor import consolidate as _m

sys.modules[__name__] = _m  # same module object as tremor.consolidate
