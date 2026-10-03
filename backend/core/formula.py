"""
Formulas of aggregator agents.

An aggregator computes its output from other agents' outputs, dataset columns
and static values, with an ordered list of named formulas: ``score = w1 * a +
w2 * b`` then ``admis = score >= 3``. Each formula is a Python expression
restricted to arithmetic, comparisons, boolean logic, conditionals and a few
functions; anything else (attributes, indexing, arbitrary calls) is rejected
before it is ever evaluated.

Evaluation is strict: a missing value, a type mismatch, a division by zero or a
tied vote is an error, never a default.

Values are numbers, booleans, text, or lists of those (a score distribution).
Lists only go through min, max, sum, mean, len and vote; an output is never a
list.
"""

import ast
import keyword
import math
from collections import Counter
from collections.abc import Callable
from functools import lru_cache
from typing import Any


class FormulaError(ValueError):
    """A formula is invalid, or cannot be evaluated on the given values."""


Scalar = int | float | str | bool
Value = Scalar | list[Scalar]

# Exponents beyond this are a typo, not a score
MAX_EXPONENT = 100


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


def coerce_input(value: Any) -> Value:
    """Turn a mapped value into a formula value: "4" becomes 4, blanks are errors."""
    if isinstance(value, list):
        if not value:
            raise FormulaError("is an empty list")
        if any(isinstance(item, dict | list) for item in value):
            raise FormulaError("is a list of objects or lists, not of values")
        try:
            return [_coerce_scalar(item) for item in value]
        except FormulaError as e:
            raise FormulaError(f"has a list item that {e}") from e
    return _coerce_scalar(value)


def _coerce_scalar(value: Any) -> Scalar:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise FormulaError("has no value")
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        if not math.isfinite(value):
            raise FormulaError(f"is not a finite number ({value})")
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise FormulaError("is empty")
        return _parse_number(text)
    if isinstance(value, dict):
        raise FormulaError("is an object, not a single value: map one of its fields")
    raise FormulaError(f"has an unsupported value ({value!r})")


def _parse_number(text: str) -> Scalar:
    try:
        return int(text)
    except ValueError:
        pass
    try:
        number = float(text)
    except ValueError:
        return text
    return number if math.isfinite(number) else text


def _number(value: Any) -> int | float:
    if isinstance(value, list):
        raise FormulaError(
            "expected a number, got a list: reduce it with mean(), max(), sum()… "
            "or map one item with a path like score.0"
        )
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise FormulaError(f"expected a number, got {value!r}")
    return value


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise FormulaError(f"expected true or false, got {value!r}")
    return value


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def _round(x: Any, digits: Any = None) -> int | float:
    if digits is None:
        return round(_number(x))
    digits = _number(digits)
    if not float(digits).is_integer():
        raise FormulaError(f"round() digits must be a whole number, got {digits!r}")
    return round(_number(x), int(digits))


def _spread(values: tuple) -> list:
    """Arguments with lists unpacked: mean(score) and mean(a, b) read alike."""
    spread = []
    for value in values:
        spread.extend(value if isinstance(value, list) else [value])
    return spread


def _mean(*values: Any) -> float:
    numbers = [_number(v) for v in _spread(values)]
    return math.fsum(numbers) / len(numbers)


def _sum(*values: Any) -> int | float:
    numbers = [_number(v) for v in _spread(values)]
    return (
        sum(numbers) if all(isinstance(n, int) for n in numbers) else math.fsum(numbers)
    )


def _clamp(x: Any, low: Any, high: Any) -> int | float:
    x, low, high = _number(x), _number(low), _number(high)
    if low > high:
        raise FormulaError(f"clamp() lower bound {low} is above the upper bound {high}")
    return min(max(x, low), high)


def _vote(*values: Any) -> Scalar:
    ranked = Counter(_spread(values)).most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        tied = [repr(v) for v, n in ranked if n == ranked[0][1]]
        raise FormulaError(f"vote() is a tie between {', '.join(tied)}")
    return ranked[0][0]


# name -> (fewest arguments, most arguments or None, implementation)
FUNCTIONS: dict[str, tuple[int, int | None, Callable[..., Any]]] = {
    "min": (1, None, lambda *v: min(_number(x) for x in _spread(v))),
    "max": (1, None, lambda *v: max(_number(x) for x in _spread(v))),
    "abs": (1, 1, lambda x: abs(_number(x))),
    "round": (1, 2, _round),
    "mean": (1, None, _mean),
    "sum": (1, None, _sum),
    "clamp": (3, 3, _clamp),
    "vote": (1, None, _vote),
    "len": (1, 1, lambda x: len(x) if isinstance(x, list | str) else 1),
}


# ---------------------------------------------------------------------------
# Parsing and static checks
# ---------------------------------------------------------------------------

_BIN_OPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}

_ORDERINGS: dict[type, Callable[[Any, Any], bool]] = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}

_ALLOWED_NODES = (
    ast.Expression,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.BinOp,
    ast.UnaryOp,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.IfExp,
    ast.Call,
    *_BIN_OPS,
    *_ORDERINGS,
)


@lru_cache(maxsize=1024)
def _parse(formula: str) -> ast.Expression:
    """Parse and check one formula; raise FormulaError if it is not allowed."""
    if not formula.strip():
        raise FormulaError("formula is empty")
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"syntax error: {e.msg}") from e

    called: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise FormulaError(f"{type(node).__name__.lower()} is not allowed")
        if isinstance(node, ast.Constant) and not isinstance(
            node.value, int | float | str | bool
        ):
            raise FormulaError(f"{node.value!r} is not allowed")
        if isinstance(node, ast.Call):
            _check_call(node)
            called.add(id(node.func))
        if (
            isinstance(node, ast.Name)
            and id(node) not in called
            and node.id in FUNCTIONS
        ):
            raise FormulaError(f'"{node.id}" is a function: call it, e.g. {node.id}(…)')
    return tree


def _check_call(node: ast.Call) -> None:
    if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS:
        name = node.func.id if isinstance(node.func, ast.Name) else "?"
        known = ", ".join(FUNCTIONS)
        raise FormulaError(f'unknown function "{name}" (available: {known})')
    if node.keywords:
        raise FormulaError(f"{node.func.id}() takes no keyword arguments")
    if any(isinstance(arg, ast.Starred) for arg in node.args):
        raise FormulaError("starred arguments are not allowed")
    fewest, most, _ = FUNCTIONS[node.func.id]
    count = len(node.args)
    if count < fewest or (most is not None and count > most):
        expected = (
            f"{fewest}"
            if fewest == most
            else f"{fewest} to {most}"
            if most is not None
            else f"at least {fewest}"
        )
        raise FormulaError(
            f"{node.func.id}() takes {expected} argument(s), got {count}"
        )


def _names(tree: ast.Expression) -> list[str]:
    """Variables a formula reads, in order of first appearance."""
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    names: dict[str, None] = {}
    # ast.walk is breadth-first; sort by position to follow the text
    found = [
        n for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in called
    ]
    for node in sorted(found, key=lambda n: (n.lineno, n.col_offset)):
        names[node.id] = None
    return list(names)


def _check_name(name: Any, earlier: list[str]) -> str | None:
    if not isinstance(name, str) or not name.isidentifier() or keyword.iskeyword(name):
        return "output name must be a word made of letters, digits and _"
    if name in FUNCTIONS:
        return f'"{name}" is a function name'
    if name in earlier:
        return f'output "{name}" is defined twice'
    return None


def check_outputs(outputs: list[dict]) -> list[str | None]:
    """One error message per output, or None when it is valid."""
    names = [o.get("name") for o in outputs]
    errors: list[str | None] = []
    for index, output in enumerate(outputs):
        name = names[index]
        error = _check_name(name, names[:index])
        if error is None:
            try:
                for variable in _names(_parse(output.get("formula") or "")):
                    if variable == name:
                        raise FormulaError(f'"{name}" uses itself')
                    if variable in names[index + 1 :]:
                        raise FormulaError(
                            f'"{variable}" is defined below: move it above "{name}"'
                        )
            except FormulaError as e:
                error = str(e)
        errors.append(error)
    return errors


def free_variables(outputs: list[dict]) -> list[str]:
    """Variables to map: names the formulas read that no earlier output defines."""
    variables: dict[str, None] = {}
    defined: set[str] = set()
    for output in outputs:
        try:
            tree = _parse(output.get("formula") or "")
        except FormulaError:
            tree = None
        if tree is not None:
            for name in _names(tree):
                if name not in defined:
                    variables[name] = None
        if isinstance(output.get("name"), str):
            defined.add(output["name"])
    return list(variables)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate_outputs(outputs: list[dict], variables: dict[str, Value]) -> dict:
    """Evaluate the outputs in order; each one can read the ones before it."""
    for output, error in zip(outputs, check_outputs(outputs), strict=True):
        if error:
            raise FormulaError(f"{output.get('name') or '?'}: {error}")

    env = dict(variables)
    result: dict[str, Scalar] = {}
    for output in outputs:
        name = output["name"]
        try:
            value = _eval(_parse(output["formula"]).body, env)
            if isinstance(value, list):
                raise FormulaError(
                    "result is a list: reduce it with mean(), max(), sum()…"
                )
            if isinstance(value, float) and not math.isfinite(value):
                raise FormulaError("result is too large or not a number")
        except FormulaError as e:
            raise FormulaError(f"{name}: {e}") from e
        env[name] = value
        result[name] = value
    return result


def _eval(node: ast.AST, env: dict[str, Scalar]) -> Any:
    match node:
        case ast.Constant(value=value):
            return value
        case ast.Name(id=name):
            if name not in env:
                raise FormulaError(f'variable "{name}" has no value')
            return env[name]
        case ast.BinOp(left=left, op=op, right=right):
            a, b = _number(_eval(left, env)), _number(_eval(right, env))
            if isinstance(op, ast.Pow) and abs(b) > MAX_EXPONENT:
                raise FormulaError(f"exponent {b} is too large")
            try:
                return _BIN_OPS[type(op)](a, b)
            except ZeroDivisionError as e:
                raise FormulaError("division by zero") from e
            except OverflowError as e:
                raise FormulaError("result is too large") from e
        case ast.UnaryOp(op=ast.Not(), operand=operand):
            return not _boolean(_eval(operand, env))
        case ast.UnaryOp(op=ast.USub(), operand=operand):
            return -_number(_eval(operand, env))
        case ast.UnaryOp(op=ast.UAdd(), operand=operand):
            return +_number(_eval(operand, env))
        case ast.BoolOp(op=ast.And(), values=values):
            return all(_boolean(_eval(v, env)) for v in values)
        case ast.BoolOp(op=ast.Or(), values=values):
            return any(_boolean(_eval(v, env)) for v in values)
        case ast.Compare(left=left, ops=ops, comparators=comparators):
            a = _eval(left, env)
            for op, comparator in zip(ops, comparators, strict=True):
                b = _eval(comparator, env)
                if not _compare(op, a, b):
                    return False
                a = b
            return True
        case ast.IfExp(test=test, body=body, orelse=orelse):
            return _eval(body if _boolean(_eval(test, env)) else orelse, env)
        case ast.Call(func=ast.Name(id=name), args=args):
            return FUNCTIONS[name][2](*(_eval(a, env) for a in args))
    raise FormulaError(f"{type(node).__name__.lower()} is not allowed")


def _compare(op: ast.cmpop, a: Any, b: Any) -> bool:
    if isinstance(op, ast.Eq):
        return a == b
    if isinstance(op, ast.NotEq):
        return a != b
    both_numbers = all(
        isinstance(v, int | float) and not isinstance(v, bool) for v in (a, b)
    )
    if not both_numbers and not (isinstance(a, str) and isinstance(b, str)):
        raise FormulaError(f"cannot compare {a!r} with {b!r}")
    return _ORDERINGS[type(op)](a, b)
