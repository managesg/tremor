import sys

from tremor import enforce as _m

sys.modules[__name__] = _m  # same module object as tremor.enforce
