"""Independent stdlib-only gate-level statevector Grover simulator (no numpy).

Convention (stated by QGrid's docstring, re-implemented here from first principles):
  start   H^n |0>
  oracle  O = I - 2 sum_{m in marked} |m><m|
  diffuse D = H^n (I - 2|0><0|) H^n   (built gate by gate, never via the mean)
  one Grover iteration = D @ O  (= minus the textbook reflection; global phase (-1)^k)
Qubit q is bit q of the basis-state index. No quantum advantage is claimed: this is a classical simulation.
"""
import math
from operator import index as integer_index

_R2 = 1 / math.sqrt(2)


def hadamard(state, q):
    """Apply H to qubit q: pairs (i, i|bit) -> ((a+b)/sqrt2, (a-b)/sqrt2)."""
    bit = 1 << q
    out = list(state)
    for i in range(len(state)):
        if not i & bit:
            a, b = state[i], state[i | bit]
            out[i] = (a + b) * _R2
            out[i | bit] = (a - b) * _R2
    return out


def hadamard_all(state, n):
    for q in range(n):
        state = hadamard(state, q)
    return state


def _marked_indices(basis_states, size):
    indices = set()
    for state in basis_states:
        try:
            index = integer_index(state)
        except TypeError as error:
            raise ValueError(f"marked state {state!r} is not an integer index") from error
        if not 0 <= index < size:
            raise ValueError(f"marked state {state!r} out of range")
        indices.add(index)
    return indices


def phase_flip(state, basis_states):
    """O = I - 2 sum |m><m| on the given basis states (duplicates count once)."""
    out = list(state)
    for m in _marked_indices(basis_states, len(state)):
        out[m] = -out[m]
    return out


def diffuser(state, n):
    """H^n, (I - 2|0><0|), H^n."""
    s = hadamard_all(state, n)
    s[0] = -s[0]
    return hadamard_all(s, n)


def grover_iteration(state, n, marked):
    return diffuser(phase_flip(state, marked), n)


def initial_state(n):
    s = [0j] * (1 << n)
    s[0] = 1 + 0j
    return hadamard_all(s, n)


def grover_states(n, marked, k):
    """Statevectors after 0..k iterations with one fixed marked set."""
    if n < 1 or k < 0:
        raise ValueError("need n >= 1 and k >= 0")
    marked = _marked_indices(marked, 1 << n)
    state = initial_state(n)
    out = [state]
    for _ in range(k):
        state = grover_iteration(state, n, marked)
        out.append(state)
    return out


def marked_probability(state, marked):
    return sum(abs(state[m]) ** 2 for m in _marked_indices(marked, len(state)))


def optimal_iterations(N, M):
    if M <= 0 or M >= N:
        return 0
    return int(math.floor(math.pi / 4 * math.sqrt(N / M)))


def closed_form(N, M, k):
    """sin^2((2k+1) theta), theta = asin(sqrt(M/N))."""
    return math.sin((2 * k + 1) * math.asin(math.sqrt(M / N))) ** 2
