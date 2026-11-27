import sys

from tremor import stats as _m

sys.modules[__name__] = _m  # same module object as tremor.stats
