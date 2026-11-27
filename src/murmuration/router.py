import sys

from tremor import router as _m

sys.modules[__name__] = _m  # same module object as tremor.router
