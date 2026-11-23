"""Evidence leases (Line 6 technique; PROPOSAL-RESIDENCY-V3.md, "Technique: evidence leases").

A grant has a scope and an expiry. Scope widens when an anytime-valid confidence bound on the
violation rate, with a prior pooled across similar scopes, falls below a target; it shrinks with idle
rounds and is revoked on a violation, taking effect on the next action. Irreversible actions are never
widened automatically. Readout: over-grant exposure, rounds in which a grant was held and not used.
Idle expiry and immediate revocation follow lab/evidence_lease_control.py.

Reading: the bound is a caller-supplied `bound(scope_counts, pooled_counts) -> upper bound`; this module
fixes no statistical method. Counts are (violations, trials).
Reading: "similar scopes" are given by a caller-supplied `group` mapping (scope -> group key); pooled
counts sum over the scope's group. With no mapping each scope is its own group (the no-pooling baseline).
Reading: shrinking removes a scope whose grant stayed unused for `idle_rounds` consecutive rounds.
Reading: a shrunk or revoked scope widens again only after a new observation for it.
"""


class EvidenceLease:
    def __init__(self, *, target, idle_rounds, bound, irreversible=frozenset(), group=None):
        if isinstance(target, bool) or not isinstance(target, (int, float)) or not 0 < target < 1:
            raise ValueError("target must be a number strictly between 0 and 1")
        if isinstance(idle_rounds, bool) or not isinstance(idle_rounds, int) or idle_rounds < 1:
            raise ValueError("idle_rounds must be a positive integer")
        if not callable(bound):
            raise ValueError("bound must be callable")
        self.target, self.idle_rounds, self.bound = target, idle_rounds, bound
        self.irreversible = frozenset(irreversible)
        self.group = dict(group or {})
        self.counts = {}   # scope -> [violations, trials]
        self.idle = {}     # granted scope -> consecutive unused rounds
        self.exposure = 0  # rounds summed over scopes held and not used
        self.stale = set()  # shrunk or revoked, waiting for new evidence

    def allowed(self, scope):
        return scope in self.idle

    def observe(self, scope, violation):
        """Record one verified action outcome; a violation revokes the grant before the next action."""
        if not isinstance(violation, bool):
            raise ValueError("violation must be a bool")
        c = self.counts.setdefault(scope, [0, 0])
        c[0] += violation
        c[1] += 1
        if violation:
            self.idle.pop(scope, None)
            self.stale.add(scope)
        else:
            self.stale.discard(scope)

    def _pooled(self, scope):
        key = self.group.get(scope, ("solo", scope))
        members = [s for s in self.counts if self.group.get(s, ("solo", s)) == key]
        return (sum(self.counts[s][0] for s in members), sum(self.counts[s][1] for s in members))

    def end_round(self, used):
        """Close a round: account exposure, shrink idle grants, then widen eligible scopes."""
        used = set(used)
        for scope in list(self.idle):
            if scope in used:
                self.idle[scope] = 0
                continue
            self.exposure += 1
            self.idle[scope] += 1
            if self.idle[scope] >= self.idle_rounds:
                del self.idle[scope]
                self.stale.add(scope)
        for scope, (v, n) in self.counts.items():
            if scope in self.idle or scope in self.irreversible or scope in self.stale:
                continue
            ub = self.bound((v, n), self._pooled(scope))
            if ub is not None and ub < self.target:
                self.idle[scope] = 0
