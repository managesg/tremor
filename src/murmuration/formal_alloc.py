import sys

from tremor import formal_alloc as _m

sys.modules[__name__] = _m  # same module object as tremor.formal_alloc
