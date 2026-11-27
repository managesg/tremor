import sys

from tremor import backend_claude as _m

sys.modules[__name__] = _m  # same module object as tremor.backend_claude
