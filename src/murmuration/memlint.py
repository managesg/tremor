import sys

from tremor import memlint as _m

sys.modules[__name__] = _m  # same module object as tremor.memlint
