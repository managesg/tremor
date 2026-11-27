import sys

from tremor.trapbench import sqlseq as _m

sys.modules[__name__] = _m  # same module object as tremor.trapbench.sqlseq
