"""Exact one-generation count control for the scripted L2 well-mixed null."""

from fractions import Fraction
import json
from math import comb


def first_generation_null(*, population, immune, draws):
    """Count eligible targets in an equally likely subset drawn without replacement.

    The source is outside the target roster. Every non-immune target in the
    subset contributes one count by construction. There are no later rounds.
    """
    if any(type(value) is not int or value < 0 for value in (population, immune, draws)):
        raise ValueError("population, immune count and draw count need nonnegative integers")
    if immune > population or draws > population:
        raise ValueError("immune count and draw count cannot exceed the population")

    eligible = population - immune
    total = comb(population, draws)
    lower, upper = max(0, draws - immune), min(draws, eligible)
    pmf = {
        count: Fraction(comb(eligible, count) * comb(immune, draws - count), total)
        for count in range(lower, upper + 1)
    }
    mean = Fraction(draws * eligible, population) if population else Fraction(0)
    return {"pmf": pmf, "mean": mean}


def _ratio(value):
    if not isinstance(value, Fraction):
        raise TypeError("expected a Fraction to serialize")
    return {"numerator": value.numerator, "denominator": value.denominator}


def demo():
    """Return the exact five-target fixture and its two boundary controls."""
    cases = {}
    for name, immune in (("no_immunity", 0), ("two_immune", 2), ("all_immune", 5)):
        inputs = {"population": 5, "immune": immune, "draws": 2}
        result = first_generation_null(**inputs)
        cases[name] = {**inputs, "pmf": {str(count): _ratio(value) for count, value in result["pmf"].items()},
                       "mean": _ratio(result["mean"])}
    return {
        "scope": "scripted_count_only", "scientific_result": False,
        "rule": "All fixed-size target subsets are equally likely. Each eligible target counts once.",
        "limitations": "One generation only. No payloads, transmission dynamics, or claims about agents.",
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
