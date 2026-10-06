import pytest

from core.formula import (
    FormulaError,
    check_outputs,
    coerce_input,
    evaluate_outputs,
    free_variables,
)


def score(formula: str) -> list[dict]:
    return [{"name": "score", "formula": formula}]


def evaluate(formula: str, **variables):
    return evaluate_outputs(score(formula), variables)["score"]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def test_weighted_mean():
    assert evaluate(
        "w1 * langue + w2 * contenu", w1=0.4, w2=0.6, langue=3, contenu=4
    ) == pytest.approx(3.6)


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("7 // 2", 3),
        ("7 % 2", 1),
        ("2 ** 3", 8),
        ("-x + +x", 0),
        ("1 < x <= 3", True),
        ("x == 2 and not x != 2", True),
        ("x > 5 or x < 3", True),
        ("0 if x < 3 else x", 0),
        ('"pass" if x >= 2 else "fail"', "pass"),
        ("min(x, 1, 5)", 1),
        ("max(x, 1, 5)", 5),
        ("abs(-x)", 2),
        ("round(2.456, 1)", 2.5),
        ("round(2.6)", 3),
        ("mean(x, 4)", 3),
        ("sum(x, 4, 1)", 7),
        ("clamp(x, 3, 5)", 3),
        ("clamp(x, 0, 1)", 1),
        ('vote("a", "b", "a")', "a"),
        ("vote(x, 2, 3)", 2),
    ],
)
def test_operators_and_functions(formula, expected):
    assert evaluate(formula, x=2) == expected


def test_later_outputs_read_earlier_ones():
    outputs = [
        {"name": "score", "formula": "(a + b) / 2"},
        {"name": "admis", "formula": "score >= 3"},
    ]
    assert evaluate_outputs(outputs, {"a": 2, "b": 5}) == {"score": 3.5, "admis": True}


@pytest.mark.parametrize(
    ("formula", "variables", "message"),
    [
        ("a / b", {"a": 1, "b": 0}, "division by zero"),
        ("a // b", {"a": 1, "b": 0}, "division by zero"),
        ("a % b", {"a": 1, "b": 0}, "division by zero"),
        ('vote("a", "b")', {}, "tie"),
        ("a + 1", {"a": "x"}, "number"),
        ("a + 1", {"a": True}, "number"),
        ("a and True", {"a": 1}, "true or false"),
        ("1 if a else 0", {"a": 1}, "true or false"),
        ('a < "b"', {"a": 1}, "compare"),
        ("2 ** 10000", {}, "exponent"),
        ("10.0 ** 400", {}, "too large"),
        ("clamp(1, 5, 0)", {}, "lower bound"),
    ],
)
def test_runtime_errors(formula, variables, message):
    with pytest.raises(FormulaError, match=message):
        evaluate(formula, **variables)


def test_error_names_the_output():
    outputs = [{"name": "score", "formula": "1"}, {"name": "ratio", "formula": "1 / 0"}]
    with pytest.raises(FormulaError, match=r"^ratio: "):
        evaluate_outputs(outputs, {})


def test_missing_variable_is_an_error():
    with pytest.raises(FormulaError, match='"b" has no value'):
        evaluate("a + b", a=1)


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("formula", "message"),
    [
        ("", "empty"),
        ("a +", "syntax"),
        ("a.b", "not allowed"),
        ("a[0]", "not allowed"),
        ("[a, b]", "not allowed"),
        ("lambda: 1", "not allowed"),
        ("__import__('os')", "unknown function"),
        ("open('x')", "unknown function"),
        ("min", "function"),
        ("min(x=1)", "keyword"),
        ("min(*a)", "not allowed"),
        ("None", "not allowed"),
        ("a := 1", "syntax"),
        ("abs(1, 2)", "argument"),
        ("max()", "argument"),
    ],
)
def test_rejects_invalid_formulas(formula, message):
    errors = check_outputs(score(formula))
    assert errors[0] is not None
    assert message in errors[0]


@pytest.mark.parametrize(
    ("outputs", "index", "message"),
    [
        ([{"name": "", "formula": "1"}], 0, "name"),
        ([{"name": "2x", "formula": "1"}], 0, "name"),
        ([{"name": "max", "formula": "1"}], 0, "function"),
        ([{"name": "a", "formula": "1"}, {"name": "a", "formula": "2"}], 1, "twice"),
        ([{"name": "a", "formula": "a + 1"}], 0, "itself"),
        ([{"name": "a", "formula": "b"}, {"name": "b", "formula": "1"}], 0, "below"),
    ],
)
def test_rejects_invalid_outputs(outputs, index, message):
    errors = check_outputs(outputs)
    assert errors[index] is not None
    assert message in errors[index]


def test_valid_outputs_have_no_errors():
    outputs = [
        {"name": "score", "formula": "w1 * a + w2 * b"},
        {"name": "admis", "formula": "score >= 3"},
    ]
    assert check_outputs(outputs) == [None, None]


def test_free_variables_in_order_of_appearance():
    outputs = [
        {"name": "score", "formula": "w1 * langue + w2 * contenu + mean(langue)"},
        {"name": "admis", "formula": "score >= seuil"},
    ]
    assert free_variables(outputs) == ["w1", "langue", "w2", "contenu", "seuil"]


def test_free_variables_skip_unparsable_formulas():
    outputs = [{"name": "a", "formula": "x +"}, {"name": "b", "formula": "y"}]
    assert free_variables(outputs) == ["y"]


# ---------------------------------------------------------------------------
# Input conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (4, 4),
        (4.5, 4.5),
        ("4", 4),
        (" 4.5 ", 4.5),
        ("correct", "correct"),
        (True, True),
    ],
)
def test_coerce_input(value, expected):
    assert coerce_input(value) == expected


def test_coerce_input_keeps_lists_of_values():
    assert coerce_input([0.1, "0.2", 3]) == [0.1, 0.2, 3]


@pytest.mark.parametrize(
    "value", [None, float("nan"), "", "  ", {"a": 1}, [], [{"a": 1}], [[1]], [None]]
)
def test_coerce_input_rejects(value):
    with pytest.raises(FormulaError):
        coerce_input(value)


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("mean(dist)", 0.25),
        ("max(dist)", 0.6),
        ("min(dist, 0.05)", 0.0),
        ("sum(dist)", pytest.approx(1.0)),
        ("len(dist)", 4),
        ("vote(labels)", "a"),
    ],
)
def test_lists_go_through_reducing_functions(formula, expected):
    variables = {"dist": [0.0, 0.1, 0.3, 0.6], "labels": ["a", "b", "a"]}
    assert evaluate(formula, **variables) == expected


@pytest.mark.parametrize(
    ("formula", "message"),
    [("dist * 2", "got a list"), ("dist", "result is a list")],
)
def test_lists_cannot_be_used_as_numbers(formula, message):
    with pytest.raises(FormulaError, match=message):
        evaluate(formula, dist=[0.1, 0.9])
