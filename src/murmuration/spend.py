import sys

from tremor import spend as _m

sys.modules[__name__] = _m  # same module object as tremor.spend
