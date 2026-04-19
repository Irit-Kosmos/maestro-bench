"""
Prompt template rendering engine.

Supports both Jinja2 syntax ({{ variable }}) and legacy <variable> syntax.
Renders system and user prompts with variables from dataset rows
and previous agent outputs.
"""

import re
from typing import Optional

from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError, Undefined


class _LenientUndefined(Undefined):
    """Returns empty string for missing variables instead of raising."""

    def __str__(self) -> str:
        return ""

    def __iter__(self):
        return iter([])

    def __bool__(self) -> bool:
        return False


_jinja_env = Environment(
    loader=BaseLoader(),
    undefined=_LenientUndefined,
    autoescape=False,
    keep_trailing_newline=True,
)


def render_prompt(template: str, variables: dict) -> str:
    """
    Render a prompt template with the given variables.

    Supports:
    - Jinja2 syntax: {{ variable_name }}
    - Legacy syntax: <variable_name>

    Args:
        template: The prompt template string
        variables: Dict of variable name → value

    Returns:
        The rendered prompt string
    """
    if not template:
        return ""

    # Convert legacy <variable> placeholders to Jinja2 {{ variable }}
    converted = _convert_legacy_placeholders(template, variables)

    try:
        tpl = _jinja_env.from_string(converted)
        return tpl.render(**variables)
    except (TemplateSyntaxError, UndefinedError) as e:
        # Fallback: do simple string replacement if Jinja2 fails
        result = converted
        for key, value in variables.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result


def _convert_legacy_placeholders(template: str, variables: dict) -> str:
    """
    Convert <variable_name> placeholders to {{ variable_name }}
    Only converts placeholders whose names match known variable keys.
    """
    for var_name in variables:
        # Match <var_name> but not things like <div> or <br> (HTML tags)
        pattern = re.compile(rf"<{re.escape(var_name)}>")
        template = pattern.sub(f"{{{{ {var_name} }}}}", template)
    return template


def build_messages(
    system_prompt: Optional[str],
    user_prompt: Optional[str],
    variables: dict,
) -> list[dict]:
    """
    Build OpenAI-format chat messages from system/user prompts + variables.

    Args:
        system_prompt: System prompt template (may contain placeholders)
        user_prompt: User prompt template (may contain placeholders)
        variables: Variables to inject into prompts

    Returns:
        List of {"role": ..., "content": ...} messages
    """
    messages = []

    if system_prompt:
        rendered_system = render_prompt(system_prompt, variables)
        if rendered_system.strip():
            messages.append({"role": "system", "content": rendered_system})

    if user_prompt:
        rendered_user = render_prompt(user_prompt, variables)
        if rendered_user.strip():
            messages.append({"role": "user", "content": rendered_user})

    return messages
