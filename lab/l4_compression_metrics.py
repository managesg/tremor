"""Exact byte and episode retention arithmetic for paired L4 snapshots."""

from fractions import Fraction


def _ratio(numerator, denominator):
    if denominator == 0:
        return None
    ratio = Fraction(numerator, denominator)
    return {"numerator": ratio.numerator, "denominator": ratio.denominator}


def metrics(*, before_bytes, after_bytes, eligible_raw_sizes, retained_raw_sizes):
    """Measure after/before on validated byte counts and raw episode inventories."""
    eligible_raw_sizes = tuple(eligible_raw_sizes)
    retained_raw_sizes = tuple(retained_raw_sizes)
    eligible_count = len(eligible_raw_sizes)
    retained_count = len(retained_raw_sizes)
    eligible_bytes = sum(eligible_raw_sizes)
    retained_bytes = sum(retained_raw_sizes)
    return {
        "loaded_bytes": {
            "before": before_bytes,
            "after": after_bytes,
            "retained_fraction": _ratio(after_bytes, before_bytes),
        },
        "raw_retention": {
            "eligible_count": eligible_count,
            "retained_count": retained_count,
            "eligible_bytes": eligible_bytes,
            "retained_bytes": retained_bytes,
            "count_fraction": _ratio(retained_count, eligible_count),
            "byte_fraction": _ratio(retained_bytes, eligible_bytes),
        },
    }
