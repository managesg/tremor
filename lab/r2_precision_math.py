"""Exact arithmetic for the proposed R2 cluster precision calculation."""

from collections.abc import Mapping
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from math import ceil
import re


DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
PRECISION_DIVISOR = Fraction(14, 5)


def _number(value):
    if type(value) is not str or DECIMAL.fullmatch(value) is None:
        raise ValueError("precision inputs must use exact decimal strings")
    return Fraction(Decimal(value))


def _fields(value, requested):
    if not isinstance(value, Mapping) or value.keys() != set(requested.split()):
        raise ValueError("unexpected precision evidence fields")


def _integer(value, minimum):
    if type(value) is not int or value < minimum:
        raise ValueError("invalid cluster count or rerun count")
    return value


def _ratio(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def _variance(pilot):
    _fields(pilot, "method sd icc reruns_per_cluster")
    reruns = _integer(pilot["reruns_per_cluster"], 3)
    sd = _number(pilot["sd"])
    if sd < 0:
        raise ValueError("pilot SD must be nonnegative")
    method = pilot["method"]
    if method == "cluster_mean":
        if pilot["icc"] is not None:
            raise ValueError("cluster-mean SD must not apply a second design effect")
        variance = sd**2
    elif method == "balanced_icc":
        icc = _number(pilot["icc"])
        if not 0 <= icc <= 1:
            raise ValueError("pilot ICC must be between zero and one")
        variance = sd**2 * (1 + (reruns - 1) * icc) / reruns
    else:
        raise ValueError("unknown pilot variance method")
    return variance, reruns


def _projected_se(variance, clusters):
    projected_variance = variance / clusters
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        ratio = Decimal(projected_variance.numerator) / Decimal(projected_variance.denominator)
        return format(ratio.sqrt(), ".12g")


def _target(expected_effect, kill_boundary):
    effect, kill = _number(expected_effect), _number(kill_boundary)
    if not 0 < kill < effect:
        raise ValueError("the expected effect must exceed a positive kill boundary")
    return min(kill, effect - kill) / PRECISION_DIVISOR


def _capacity(capacity):
    if capacity is None:
        return None, None
    _fields(capacity, "max_clusters reruns_per_cluster")
    return _integer(capacity["max_clusters"], 0), _integer(capacity["reruns_per_cluster"], 3)


def _result(target, variance, pilot_reruns, max_clusters, capacity_reruns):
    result = {"status": "missing_pilot", "target_se": _ratio(target), "variance_per_cluster": None,
              "required_clusters": None, "projected_se": None, "reachable": None, "scientific_result": False}
    if capacity_reruns is not None and pilot_reruns is not None and pilot_reruns != capacity_reruns:
        raise ValueError("pilot and capacity reruns per cluster must align")
    if variance is None:
        return result
    if variance == 0:
        return result | {"status": "degenerate_pilot"}
    required = ceil(variance / target**2)
    result.update(status="missing_capacity", variance_per_cluster=_ratio(variance), required_clusters=required)
    if max_clusters is None:
        return result
    return result | {
        "status": "calculated",
        "projected_se": _projected_se(variance, max_clusters) if max_clusters else None,
        "reachable": max_clusters >= required,
    }


def calculate(*, expected_effect, kill_boundary, pilot=None, capacity=None):
    """Compute the proposed SE target and compare it to supplied cluster capacity."""
    target = _target(expected_effect, kill_boundary)
    max_clusters, capacity_reruns = _capacity(capacity)
    variance, pilot_reruns = (None, None) if pilot is None else _variance(pilot)
    return _result(target, variance, pilot_reruns, max_clusters, capacity_reruns)


def calculate_from_cluster_variance(*, expected_effect, kill_boundary, variance, reruns_per_cluster, capacity=None):
    """Accept an exact variance of cluster means without applying a design effect."""
    target = _target(expected_effect, kill_boundary)
    max_clusters, capacity_reruns = _capacity(capacity)
    reruns = _integer(reruns_per_cluster, 3)
    if variance is not None and (type(variance) is not Fraction or variance < 0):
        raise ValueError("cluster-mean variance must be a nonnegative Fraction or null")
    return _result(target, variance, reruns, max_clusters, capacity_reruns)
