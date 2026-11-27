import sys

from tremor import vreplay as _m

sys.modules[__name__] = _m  # same module object as tremor.vreplay
