"""E1.2 reuse hazard: power-law gaps against a memoryless exponential."""
import math

from . import ledger


def gaps(events):
    """Idle gaps in days between successive uses of each capability key."""
    last, out = {}, []
    for e in sorted((e for e in events if not e.denied), key=lambda e: e.t):  # a denied call is not a use
        if e.key in last and e.t > last[e.key]:
            out.append((e.t - last[e.key]) / ledger.DAY)
        last[e.key] = e.t
    return out


# shortcut: xmin is the smallest gap (not fitted), both models are conditioned on x>=xmin,
# p is a Vuong normal approximation (unreliable for n<~30, non-nested only), no lognormal
# or censoring of the final open gap; upgrade if E1.2 needs a third model.
def fit(gs):
    """-> {alpha, rate, llr, p, n}. alpha: density exponent f~x^-alpha; rate: exponential 1/day.
    llr>0 favours the power law; p is two-sided. llr and p are None when undefined."""
    xs = [x for x in gs if x > 0]
    n = len(xs)
    if n < 2:
        return dict(alpha=None, rate=None, llr=None, p=None, n=n)
    xm = min(xs)
    s = sum(math.log(x / xm) for x in xs)
    d = sum(x - xm for x in xs)
    if s == 0 or d == 0:
        return dict(alpha=None, rate=None, llr=None, p=None, n=n)
    a, lam = 1 + n / s, n / d
    diff = [math.log((a - 1) / xm) - a * math.log(x / xm) - math.log(lam) + lam * (x - xm) for x in xs]
    llr = sum(diff)
    m = llr / n
    sd = math.sqrt(sum((v - m) ** 2 for v in diff) / n)
    p = math.erfc(abs(m) * math.sqrt(n) / (sd * math.sqrt(2))) if sd else 0.0
    return dict(alpha=a, rate=lam, llr=llr, p=p, n=n)
