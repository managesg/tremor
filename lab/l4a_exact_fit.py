"""Exact least-squares fitting for the L4-A development comparison."""

from fractions import Fraction


def _number(value):
    if type(value) not in (int, Fraction):
        raise ValueError("expected an exact integer or Fraction")
    return Fraction(value)


def _dot(left, right):
    return sum((a * b for a, b in zip(left, right, strict=True)), Fraction())


def _least_squares(columns, response):
    # The two- and three-column normal equations are solved in exact arithmetic.
    equations = [[*(_dot(column, other) for other in columns), _dot(column, response)]
                 for column in columns]
    size = len(columns)
    for index in range(size):
        pivot = next((row for row in range(index, size) if equations[row][index]), None)
        if pivot is None:
            raise ValueError("fit requires full column rank")
        equations[index], equations[pivot] = equations[pivot], equations[index]
        scale = equations[index][index]
        equations[index] = [value / scale for value in equations[index]]
        for row in range(size):
            if row != index:
                factor = equations[row][index]
                equations[row] = [value - factor * term
                                  for value, term in zip(equations[row], equations[index], strict=True)]

    coefficients = tuple(row[-1] for row in equations)
    residuals = [actual - _dot(design, coefficients)
                 for actual, design in zip(response, zip(*columns, strict=True), strict=True)]
    return {"coefficients": coefficients, "rss": _dot(residuals, residuals)}


def fit(points, *, knots):
    """Fit the straight line and the best supported hinge on training points."""
    parsed = []
    for point in points:
        if type(point) not in (tuple, list) or len(point) != 2:
            raise ValueError("each training point must be an (x, y) pair")
        parsed.append(tuple(map(_number, point)))
    if not parsed:
        raise ValueError("fit requires training points")
    ordered_knots = sorted(map(_number, knots))
    if not ordered_knots or len(set(ordered_knots)) != len(ordered_knots):
        raise ValueError("fit requires distinct candidate knots")

    x, response = zip(*parsed, strict=True)
    distinct_x = set(x)
    straight_columns = ((Fraction(1),) * len(x), x)
    line = _least_squares(straight_columns, response)
    candidates = []
    for knot in ordered_knots:
        left = sum(value < knot for value in distinct_x)
        right = sum(value > knot for value in distinct_x)
        if min(left, right) < 2:
            raise ValueError("candidate knot needs two distinct measured values strictly on each side")
        hinge_column = tuple(max(Fraction(), value - knot) for value in x)
        candidates.append({"knot": knot, **_least_squares((*straight_columns, hinge_column), response)})

    best = min(candidates, key=lambda candidate: candidate["rss"])
    candidate_rss = tuple((candidate["knot"], candidate["rss"]) for candidate in candidates)
    return {"line": line, "hinge": best, "candidate_rss": candidate_rss,
            "tied_knots": tuple(knot for knot, rss in candidate_rss if rss == best["rss"])}


def predict(model, x):
    """Evaluate a returned straight or hinge model on one exact coordinate."""
    x = _number(x)
    features = (Fraction(1), x)
    if "knot" in model:
        features += (max(Fraction(), x - model["knot"]),)
    return _dot(features, model["coefficients"])
