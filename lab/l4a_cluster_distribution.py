"""Exact ordered resampling of fixed paired cluster gains."""

from collections import Counter
from fractions import Fraction
from itertools import product


def distribution(values, *, max_draws):
    """Enumerate all cluster draws for the mean of the sampled gains."""
    if type(max_draws) is not int or max_draws < 1:
        raise ValueError("max_draws must be a positive integer")
    gains = tuple(values)
    if not gains or any(type(gain) is not Fraction for gain in gains):
        raise ValueError("expected a nonempty sequence of Fraction cluster gains")
    count = len(gains)
    # For a large inventory, the 2**count lower bound avoids constructing count**count.
    if count > max_draws.bit_length() or count ** count > max_draws:
        raise ValueError("ordered cluster draw count exceeds max_draws")

    histogram = Counter()
    for draw in product(gains, repeat=count):
        histogram[sum(draw) / count] += 1
    return dict(histogram)
