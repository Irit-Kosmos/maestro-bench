import pytest

from core.steps import split_step, step_key


@pytest.mark.parametrize(
    ("step", "parsed"), [("12", (12, 1)), ("12#2", (12, 2)), (12, (12, 1))]
)
def test_a_step_key_reads_as_its_agent_and_instance(step, parsed):
    assert split_step(step) == parsed
    assert step_key(*parsed) == str(step)


@pytest.mark.parametrize(
    "step", ["abc", "12#x", "012", " 12", "12#1", "12#", "12#0", "12#-3"]
)
def test_only_the_written_form_is_a_step_key(step):
    with pytest.raises(ValueError, match="Invalid step"):
        split_step(step)
