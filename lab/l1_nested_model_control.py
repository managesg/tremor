"""Exact least-squares rehearsal for the L1 nested-model design."""

from fractions import Fraction
import json


ROW_FIELDS = {"id", "response", "mean", "team_size", "activity", "dose_counts"}
NUISANCE_FIELDS = ("mean", "team_size", "activity")


def _number(value):
    if type(value) not in (int, Fraction):
        raise ValueError("expected an exact integer or Fraction")
    return Fraction(value)


def _dot(left, right):
    return sum((a * b for a, b in zip(left, right, strict=True)), Fraction(0))


def count_scale_slope(dose_counts):
    """Return the OLS count-scale slope including an intercept."""
    try:
        iterator = iter(dose_counts)
    except TypeError as error:
        raise ValueError("expected an iterable of exact (dose, count) pairs") from error
    points = []
    for pair in iterator:
        if type(pair) not in (tuple, list) or len(pair) != 2:
            raise ValueError("expected an ordered (dose, count) pair")
        dose, count = pair
        points.append((_number(dose), _number(count)))
    if len({dose for dose, _ in points}) < 3:
        raise ValueError("susceptibility needs at least three distinct doses")
    doses, counts = zip(*points, strict=True)
    mean_dose, mean_count = sum(doses) / len(doses), sum(counts) / len(counts)
    centered_doses = [dose - mean_dose for dose in doses]
    centered_counts = [count - mean_count for count in counts]
    return _dot(centered_doses, centered_counts) / _dot(centered_doses, centered_doses)


def _validated_rows(rows):
    parsed = {}
    try:
        iterator = iter(rows)
    except TypeError as error:
        raise ValueError("expected an iterable of nested-model rows") from error
    for row in iterator:
        if type(row) is not dict or row.keys() != ROW_FIELDS:
            raise ValueError("unexpected nested-model row fields")
        identifier = row["id"]
        if type(identifier) is not str or not identifier.strip() or identifier in parsed:
            raise ValueError("nested-model row IDs must be nonempty and unique")
        parsed[identifier] = {field: _number(row[field]) for field in ("response", *NUISANCE_FIELDS)}
        parsed[identifier]["susceptibility"] = count_scale_slope(row["dose_counts"])
    if not parsed:
        raise ValueError("nested-model rows must be nonempty")
    return parsed


def _residual(column, basis):
    """Project out each unnormalized, mutually orthogonal basis vector."""
    residual = column
    for direction in basis:
        coefficient = _dot(residual, direction) / _dot(direction, direction)
        residual = [value - coefficient * component for value, component in zip(residual, direction, strict=True)]
    return residual


def _basis(columns):
    basis = []
    for column in columns:
        direction = _residual(column, basis)
        if any(direction):
            basis.append(direction)
    return basis


def nested_rehearsal(rows):
    """Rehearse adding one predictor to an intercept and three nuisance terms."""
    parsed = _validated_rows(rows)
    ordered = [parsed[identifier] for identifier in sorted(parsed)]
    count = len(ordered)
    nuisance = [[Fraction(1)] * count]
    nuisance.extend([row[field] for row in ordered] for field in NUISANCE_FIELDS)
    basis = _basis(nuisance)
    reduced_error = _residual([row["response"] for row in ordered], basis)
    reduced_rss = _dot(reduced_error, reduced_error)
    summary = {
        "status": "undefined", "reason": "nuisance_rank_deficient", "row_count": count,
        "susceptibility_by_id": {identifier: parsed[identifier]["susceptibility"] for identifier in sorted(parsed)},
        "reduced_rank": len(basis), "full_rank": None, "rss_reduced": reduced_rss, "rss_full": None,
        "partial_r2": None, "f_statistic": None, "df_numerator": None, "df_denominator": None,
    }
    if len(basis) != len(nuisance):
        return summary
    added = _residual([row["susceptibility"] for row in ordered], basis)
    if not any(added):
        return summary | {"reason": "susceptibility_rank_deficient", "full_rank": len(basis),
                          "rss_full": reduced_rss, "df_numerator": 0, "df_denominator": count - len(basis)}

    full_error = _residual(reduced_error, [added])
    full_rss = _dot(full_error, full_error)
    improvement = reduced_rss - full_rss
    df_denominator = count - len(basis) - 1
    summary.update(full_rank=len(basis) + 1, rss_full=full_rss, df_numerator=1, df_denominator=df_denominator,
                   partial_r2=improvement / reduced_rss if reduced_rss else None)
    if df_denominator == 0:
        return summary | {"reason": "no_residual_degrees_of_freedom"}
    if full_rss == 0:
        return summary | {"reason": "perfect_fit_f_undefined"}
    return summary | {"status": "computed", "reason": None, "f_statistic": improvement / (full_rss / df_denominator)}


def _walsh_rows(beta, *, collinear=False):
    for index in range(8):
        x1, x2, x3, x4, x5 = ((-1) ** ((index & mask).bit_count()) for mask in (1, 2, 3, 4, 5))
        susceptibility = 2 + (x2 if collinear else x4)
        yield {
            "id": f"row-{index}", "response": 20 + 2 * x1 + 3 * x2 + 4 * x3 + beta * x4 + x5,
            "mean": Fraction(2 + x1, 4), "team_size": 8 + x2, "activity": 3 + x3,
            "dose_counts": [(dose, 5 + dose * susceptibility) for dose in (0, 1, 2)],
        }


def _json_ratio(value):
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    raise TypeError("expected a Fraction to serialize")


def demo():
    """Return a JSON-ready exact positive, null, and collinear control."""
    report = {"scientific_result": False, "scope": "L1_nested_model_development", "cases": {
        "positive": nested_rehearsal(_walsh_rows(2)),
        "null": nested_rehearsal(_walsh_rows(0)),
        "collinear": nested_rehearsal(_walsh_rows(2, collinear=True)),
    }}
    return json.loads(json.dumps(report, default=_json_ratio))


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2, allow_nan=False))
