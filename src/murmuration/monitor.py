import sys

from tremor import monitor as _m

sys.modules[__name__] = _m  # same module object as tremor.monitor
