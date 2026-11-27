import sys

from tremor import manifest as _m

sys.modules[__name__] = _m  # same module object as tremor.manifest
