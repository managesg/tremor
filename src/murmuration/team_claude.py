import sys

from tremor import team_claude as _m

sys.modules[__name__] = _m  # same module object as tremor.team_claude
