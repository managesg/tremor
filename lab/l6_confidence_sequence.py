"""A public L6 reference bound for a single Bernoulli violation stream."""

from dataclasses import dataclass
import json
import math


@dataclass(frozen=True)
class Execution:
    attempt_id: str
    scope: str
    sequence: int


@dataclass(frozen=True)
class Verification:
    attempt_id: str
    scope: str
    available_sequence: int
    violation: bool


def _counts(violations, trials):
    if type(violations) is not int or type(trials) is not int or not 0 <= violations <= trials:
        raise ValueError("invalid Bernoulli counts")


def _alpha(alpha):
    if type(alpha) not in (int, float) or not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between zero and one")


def _log_marginal(violations, trials):
    # Uniform Beta(1,1) prior: integrated likelihood of a single ordered history.
    return -math.log(trials + 1) - math.log(math.comb(trials, violations))


def _log_likelihood(violations, trials, p):
    safe = trials - violations
    if (p == 0 and violations) or (p == 1 and safe):
        return -math.inf
    return (violations * math.log(p) if violations else 0) + (safe * math.log1p(-p) if safe else 0)


def log_e_value(violations, trials, p):
    """Log mixture likelihood ratio for testing a constant Bernoulli parameter."""
    _counts(violations, trials)
    if type(p) not in (int, float) or not 0 <= p <= 1:
        raise ValueError("candidate parameter must be between zero and one")
    return _log_marginal(violations, trials) - _log_likelihood(violations, trials, p)


def upper_bound(violations, trials, *, alpha):
    """Upper endpoint of the inverted uniform-mixture confidence sequence."""
    _counts(violations, trials)
    _alpha(alpha)
    if trials == violations:
        return 1.0
    marginal = _log_marginal(violations, trials)
    threshold = -math.log(alpha)
    lower, upper = violations / trials, 1.0
    for _ in range(64):
        middle = (lower + upper) / 2
        if middle in (lower, upper):
            break
        if marginal - _log_likelihood(violations, trials, middle) >= threshold:
            upper = middle
        else:
            lower = middle
    return math.nextafter(upper, 1.0)


def snapshot(executions, receipts, *, scope, as_of, alpha):
    """Compute only the contiguous verified prefix of one executed scope."""
    _alpha(alpha)
    if not isinstance(scope, str) or not scope or type(as_of) is not int or as_of < 0:
        raise ValueError("scope and nonnegative observation sequence are required")
    by_id = {}
    positions = set()
    for action in executions:
        if (not isinstance(action, Execution) or not isinstance(action.attempt_id, str) or not action.attempt_id
                or not isinstance(action.scope, str) or not action.scope
                or type(action.sequence) is not int or action.sequence < 0
                or action.attempt_id in by_id or action.sequence in positions):
            raise ValueError("invalid or duplicate execution")
        by_id[action.attempt_id] = action
        positions.add(action.sequence)

    observed = {}
    for receipt in receipts:
        if not isinstance(receipt, Verification) or not isinstance(receipt.attempt_id, str):
            raise ValueError("invalid verification record")
        action = by_id.get(receipt.attempt_id)
        if (action is None or action.scope != receipt.scope or type(receipt.violation) is not bool
                or type(receipt.available_sequence) is not int or receipt.available_sequence <= action.sequence
                or receipt.attempt_id in observed):
            raise ValueError("unmatched, premature or duplicate verification")
        observed[receipt.attempt_id] = receipt

    run = sorted((action for action in by_id.values() if action.scope == scope and action.sequence <= as_of),
                 key=lambda action: action.sequence)
    trials = violations = unresolved = buffered = 0
    for action in run:
        reply = observed.get(action.attempt_id)
        if reply is None or reply.available_sequence > as_of:
            unresolved += 1
        elif unresolved:
            buffered += 1
        else:
            trials += 1
            violations += int(reply.violation)
    return {"trials": trials, "violations": violations, "unresolved": unresolved,
            "buffered_verified": buffered, "upper_bound": upper_bound(violations, trials, alpha=alpha)}


def demo():
    alpha = 0.05
    executions = [Execution("a", "scratch", 1), Execution("b", "scratch", 2),
                  Execution("other", "separate", 3), Execution("c", "scratch", 4)]
    receipts = [Verification("b", "scratch", 5, True), Verification("other", "separate", 6, True),
                Verification("a", "scratch", 7, False)]
    return {"scientific_result": False, "method": "uniform_beta_bernoulli_unpooled", "fixture_alpha": alpha,
            "before_delayed_receipt": snapshot(executions, receipts, scope="scratch", as_of=6, alpha=alpha),
            "after_delayed_receipt": snapshot(executions, receipts, scope="scratch", as_of=7, alpha=alpha),
            "zero_violation_upper": {n: upper_bound(0, n, alpha=alpha) for n in (0, 20, 100, 1000)}}


if __name__ == "__main__":
    print(json.dumps(demo(), sort_keys=True, indent=2))
