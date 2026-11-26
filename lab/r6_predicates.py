"""R6 lemma predicates: whitelist parser and step-limited evaluator (trust boundary).

A predicate is ONE Python expression over small ints. It is parsed with `ast`, checked
against a strict node whitelist, then run by our own tree walker (never exec/eval/compile).
Fail closed: every error, unknown node or limit hit raises PredicateRefused; no value returned.
Standard library only.

Limits: AST nesting is capped (MAX_DEPTH), so a left-deep sum of more than 60 terms
(x + 1 + 1 ... with 61 additions) is refused; split long sums into sum(... for ...).

Extension point: parse(source, registry) accepts {name: (arity, func)} of named PURE functions
with fixed arity (empty by default). Arguments are checked as ints and the result must be an int
within MAX_BITS. Reserved for later whitelisting of M1 table lookups; circuit-size lemmas wait for
that library, which does not exist yet.
"""
import ast
import re

MAX_SOURCE = 2000       # characters
MAX_BITS = 64           # |int| < 2**64 everywhere (constants and every result)
MAX_DEPTH = 60          # AST nesting
MAX_RANGE = 1 << 16     # elements in one range()
MAX_STEPS = 1 << 22     # ceiling on any caller-supplied step_limit

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")  # ASCII only, no leading underscore => no dunders
_BIN = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
    ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b,
    ast.BitAnd: lambda a, b: a & b, ast.BitOr: lambda a, b: a | b, ast.BitXor: lambda a, b: a ^ b,
    ast.LShift: lambda a, b: a << b, ast.RShift: lambda a, b: a >> b,
}
_CMP = {
    ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
}
_UN = {ast.Not: lambda a: not a, ast.USub: lambda a: -a, ast.UAdd: lambda a: +a,
       ast.Invert: lambda a: ~a}
_FUNCS = {
    "popcount": lambda x: bin(x).count("1") if x >= 0 else _refuse("popcount of negative"),
    "bit": lambda x, i: (x >> i) & 1 if 0 <= i < MAX_BITS else _refuse("bit index"),
    "abs": abs, "min": min, "max": max,
}
_AGG = {"all": all, "any": any, "sum": sum, "min": min, "max": max}
HELPERS = frozenset(_FUNCS) | frozenset(_AGG) | {"range"}


class PredicateRefused(Exception):
    """Predicate rejected at parse time or aborted at run time. No value is produced."""
    env = None    # set by check_lemma: the failing domain element
    steps = None  # set by check_lemma: steps used before it


class StepLimitExceeded(PredicateRefused):
    pass


def _refuse(why):
    raise PredicateRefused(why)


def _check(node, depth, bound, reg):
    """Validate one node recursively; `bound` = comprehension variables in scope."""
    if depth > MAX_DEPTH:
        _refuse("nesting too deep")
    t = type(node)  # exact type: subclasses are not whitelisted
    if t is ast.Constant:
        if type(node.value) not in (int, bool):
            _refuse("constant type")
        if node.value.bit_length() > MAX_BITS:
            _refuse("integer too large")
        return
    if t is ast.Name:
        if not _NAME.match(node.id) or type(node.ctx) is not ast.Load:
            _refuse("bad name")
        if node.id in HELPERS or node.id in reg:
            _refuse("helper used as a value")
        return
    kids = []
    if t is ast.BoolOp:
        kids = node.values
    elif t is ast.UnaryOp:
        if type(node.op) not in _UN:
            _refuse("unary op")
        kids = [node.operand]
    elif t is ast.BinOp:
        if type(node.op) not in _BIN:
            _refuse("binary op")
        kids = [node.left, node.right]
    elif t is ast.Compare:
        if any(type(o) not in _CMP for o in node.ops):
            _refuse("comparison op")
        kids = [node.left, *node.comparators]
    elif t is ast.IfExp:
        kids = [node.test, node.body, node.orelse]
    elif t is ast.Call:
        if type(node.func) is not ast.Name or node.keywords:
            _refuse("call form")
        f = node.func.id
        if f in _AGG and len(node.args) == 1 and type(node.args[0]) in (ast.GeneratorExp, ast.ListComp):
            _check_comp(node.args[0], depth + 1, bound, reg)
            return
        if f in _FUNCS or f in _AGG:
            if any(type(a) in (ast.Starred, ast.GeneratorExp, ast.ListComp) for a in node.args):
                _refuse("argument form")
            if f in _AGG and f not in ("min", "max"):
                _refuse("aggregate needs a comprehension")
            kids = node.args
        elif f in reg:
            if len(node.args) != reg[f][0] or any(
                    type(a) in (ast.Starred, ast.GeneratorExp, ast.ListComp) for a in node.args):
                _refuse("registry call arity or argument form")
            kids = node.args
        else:
            _refuse("call to non-whitelisted function")
    else:
        _refuse("node type " + t.__name__)
    for k in kids:
        _check(k, depth + 1, bound, reg)


def _check_comp(node, depth, bound, reg):
    if len(node.generators) != 1:
        _refuse("one generator only")
    g = node.generators[0]
    if g.is_async or type(g.target) is not ast.Name or not _NAME.match(g.target.id):
        _refuse("comprehension target")
    v = g.target.id
    it = g.iter
    if (type(it) is not ast.Call or type(it.func) is not ast.Name or it.func.id != "range"
            or it.keywords or not 1 <= len(it.args) <= 2):
        _refuse("iteration only over range()")
    if v in HELPERS or v in reg:
        _refuse("shadowed helper")
    for a in it.args:
        _check(a, depth + 1, bound, reg)
    inner = bound | {v}
    for c in g.ifs:
        _check(c, depth + 1, inner, reg)
    _check(node.elt, depth + 1, inner, reg)


def _free(node, bound, out):
    t = type(node)
    if t is ast.Name:
        if node.id not in bound:
            out.add(node.id)
    elif t in (ast.GeneratorExp, ast.ListComp):
        g = node.generators[0]
        for a in g.iter.args:
            _free(a, bound, out)
        inner = bound | {g.target.id}
        for c in [*g.ifs, node.elt]:
            _free(c, inner, out)
    elif t is ast.Call:
        for a in node.args:
            _free(a, bound, out)
    else:
        for k in ast.iter_child_nodes(node):
            _free(k, bound, out)


class Predicate:
    def __init__(self, source, tree, names, registry=None):
        self.source, self._tree, self.names = source, tree, frozenset(names)
        self._reg = dict(registry or {})
        self.last_steps = 0

    def run(self, env, step_limit):
        """Return (bool, steps_used) or raise PredicateRefused."""
        self.last_steps = None
        try:
            if type(step_limit) is not int or not 0 <= step_limit <= MAX_STEPS:
                _refuse("bad step limit")
            if not isinstance(env, dict):
                _refuse("env must be a dict")
            scope = {}
            for n in sorted(self.names):
                v = env.get(n)
                if type(v) not in (int, bool) or v.bit_length() > MAX_BITS:
                    _refuse("missing or invalid variable " + n)
                scope[n] = int(v)
            st = [0, step_limit]
            res = self._ev(self._tree, scope, st)
            if type(res) is not bool:
                _refuse("predicate did not yield a bool")
            self.last_steps = st[0]
            return res, st[0]
        except PredicateRefused:
            raise
        except BaseException as e:  # fail closed, including RecursionError/MemoryError
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            raise PredicateRefused("runtime error: " + type(e).__name__) from None

    def evaluate(self, env, step_limit):
        return self.run(env, step_limit)[0]

    def _int(self, v):
        if type(v) not in (int, bool) or v.bit_length() > MAX_BITS:
            _refuse("integer too large")
        return v

    def _ev(self, n, sc, st):
        st[0] += 1
        if st[0] > st[1]:
            raise StepLimitExceeded("step limit")
        t = type(n)
        if t is ast.Constant:
            return n.value
        if t is ast.Name:
            return sc[n.id]
        if t is ast.BoolOp:
            is_and = type(n.op) is ast.And
            v = None
            for x in n.values:
                v = self._ev(x, sc, st)
                if bool(v) != is_and:
                    return v
            return v
        if t is ast.UnaryOp:
            return self._int(_UN[type(n.op)](self._ev(n.operand, sc, st)))
        if t is ast.BinOp:
            a = self._ev(n.left, sc, st)
            b = self._ev(n.right, sc, st)
            if type(n.op) is ast.LShift and not 0 <= b <= MAX_BITS:
                _refuse("shift amount")
            if type(n.op) is ast.RShift and b < 0:
                _refuse("shift amount")
            return self._int(_BIN[type(n.op)](a, b))
        if t is ast.Compare:
            left = self._ev(n.left, sc, st)
            for op, c in zip(n.ops, n.comparators):
                right = self._ev(c, sc, st)
                if not _CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if t is ast.IfExp:
            return self._ev(n.body if self._ev(n.test, sc, st) else n.orelse, sc, st)
        if t is ast.Call:
            f = n.func.id
            if len(n.args) == 1 and type(n.args[0]) in (ast.GeneratorExp, ast.ListComp):
                return self._int(_AGG[f](self._comp(n.args[0], sc, st)))
            args = [self._ev(a, sc, st) for a in n.args]
            if f in self._reg:
                if any(type(a) not in (int, bool) for a in args):
                    _refuse("registry argument type")
                return self._int(self._reg[f][1](*map(int, args)))
            return self._int(_FUNCS[f](*args))
        _refuse("unexpected node")  # unreachable after _check; fail closed anyway

    def _comp(self, n, sc, st):
        g = n.generators[0]
        bounds = [self._ev(a, sc, st) for a in g.iter.args]
        r = range(*bounds)
        if len(r) > MAX_RANGE:
            _refuse("range too long")
        v = g.target.id
        inner = dict(sc)
        for i in r:
            st[0] += 1
            if st[0] > st[1]:
                raise StepLimitExceeded("step limit")
            inner[v] = i
            if all(self._ev(c, inner, st) for c in g.ifs):
                yield self._ev(n.elt, inner, st)


def _registry(registry):
    reg = {}
    for k, v in (registry or {}).items():
        if (type(k) is not str or not _NAME.match(k) or k in HELPERS or type(v) is not tuple
                or len(v) != 2 or type(v[0]) is not int or not 0 <= v[0] <= 8 or not callable(v[1])):
            _refuse("bad registry entry")
        reg[k] = v
    return reg


def parse(source, registry=None):
    """Parse and validate `source`; return a Predicate or raise PredicateRefused.

    registry: optional {name: (arity, pure_func)}; see the module docstring."""
    reg = _registry(registry)
    if type(source) is not str or not source.strip() or len(source) > MAX_SOURCE:
        _refuse("bad source size or type")
    if not source.isascii() or "\x00" in source:
        _refuse("non-ASCII source")
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        raise PredicateRefused("syntax: " + type(e).__name__) from None
    try:
        _check(tree.body, 0, frozenset(), reg)
        names = set()
        _free(tree.body, frozenset(), names)
    except PredicateRefused:
        raise
    except BaseException as e:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        raise PredicateRefused("validation: " + type(e).__name__) from None
    return Predicate(source, tree.body, names, reg)


def check_lemma(predicate, domain_iter, step_limit, total_steps):
    """First env on which the predicate is False, else None.

    step_limit bounds one element; total_steps bounds the whole run (sum over elements).
    A refusal propagates with .env (failing element) and .steps (steps used before it)."""
    if type(total_steps) is not int or total_steps < 0:
        _refuse("bad total step budget")
    used = 0
    for env in domain_iter:
        remaining = total_steps - used
        try:
            res, n = predicate.run(env, min(step_limit, remaining))
        except PredicateRefused as e:
            if isinstance(e, StepLimitExceeded) and remaining < step_limit:
                e = StepLimitExceeded("total step budget exceeded")
            e.env, e.steps = env, used
            raise e
        used += n
        if not res:
            return env
    return None
