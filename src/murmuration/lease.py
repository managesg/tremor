import sys

from tremor import lease as _m

sys.modules[__name__] = _m  # same module object as tremor.lease
