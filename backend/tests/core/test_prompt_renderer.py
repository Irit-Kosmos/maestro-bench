import pytest
from jinja2.exceptions import SecurityError

from core.prompt_renderer import render_prompt


def test_the_sandbox_renders_like_the_plain_environment():
    template = "{% for x in items %}{{ x | upper }} {% endfor %}{{ name }}"
    variables = {"items": ["a", "b"], "name": "n"}
    assert render_prompt(template, variables, sandboxed=True) == render_prompt(
        template, variables
    )


def test_the_sandbox_refuses_unsafe_attribute_access():
    with pytest.raises(SecurityError):
        render_prompt("{{ x.__class__.__mro__ }}", {"x": 1}, sandboxed=True)
