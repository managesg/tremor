import sys

from tremor import synth as _m

sys.modules[__name__] = _m  # same module object as tremor.synth
