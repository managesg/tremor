import sys

from tremor import quarantine as _m

sys.modules[__name__] = _m  # same module object as tremor.quarantine
