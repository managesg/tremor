import sys

from tremor import ledger as _m

sys.modules[__name__] = _m  # same module object as tremor.ledger
