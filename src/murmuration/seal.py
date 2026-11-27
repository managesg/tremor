import sys

from tremor import seal as _m

sys.modules[__name__] = _m  # same module object as tremor.seal
