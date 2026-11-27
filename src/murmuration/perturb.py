import sys

from tremor import perturb as _m

sys.modules[__name__] = _m  # same module object as tremor.perturb
