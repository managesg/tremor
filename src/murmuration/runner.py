import sys

from tremor import runner as _m

sys.modules[__name__] = _m  # same module object as tremor.runner
