# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Prompt template rendering engine.

Supports both Jinja2 syntax ({{ variable }}) and legacy <variable> syntax.
Renders system and user prompts with variables from dataset rows
and previous agent outputs.
"""

import re

from jinja2 import (
    BaseLoader,
    Environment,
    TemplateSyntaxError,
    Undefined,
    UndefinedError,
)
from jinja2.sandbox import ImmutableSandboxedEnvironment


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

# Same rendering, for templates that arrive from a request and are not run for real:
# attribute access that could reach the interpreter is refused
_sandboxed_env = ImmutableSandboxedEnvironment(
    loader=BaseLoader(),
    undefined=_LenientUndefined,
    autoescape=False,
    keep_trailing_newline=True,
)


def render_prompt(template: str, variables: dict, *, sandboxed: bool = False) -> str:
    """
    Render a prompt template with the given variables.

    Supports:
    - Jinja2 syntax: {{ variable_name }}
    - Legacy syntax: <variable_name>

    Args:
        template: The prompt template string
        variables: Dict of variable name → value
        sandboxed: Render in Jinja's sandbox, which raises ``SecurityError`` on unsafe access

    Returns:
        The rendered prompt string
    """
    if not template:
        return ""

    # Convert legacy <variable> placeholders to Jinja2 {{ variable }}
    converted = _convert_legacy_placeholders(template, variables)

    try:
        tpl = (_sandboxed_env if sandboxed else _jinja_env).from_string(converted)
        return tpl.render(**variables)
    except (TemplateSyntaxError, UndefinedError):
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

    Handles two forms:
    - <var_name></var_name>  → <var_name>{{ var_name }}</var_name>  (XML open+close pair, value goes between)
    - <var_name>             → {{ var_name }}  (standalone open tag, no close tag)
    Orphaned closing tags </var_name> are removed.

    Skips conversion entirely if template already contains Jinja2 {{ syntax
    (to avoid double-conversion of already-converted templates).
    """
    if "{{" in template:
        return template

    for var_name in variables:
        escaped = re.escape(var_name)
        # Replace empty <var></var> pair with <var>{{ var }}</var> (inject value inside tags)
        pair_pattern = re.compile(rf"<{escaped}>\s*</{escaped}>")
        new_template = pair_pattern.sub(f"<{var_name}>{{{{ {var_name} }}}}</{var_name}>", template)
        pair_was_found = new_template != template
        template = new_template
        # Replace standalone opening tag <var> (but not ones already converted by pair_pattern)
        open_pattern = re.compile(rf"<{escaped}>(?!\s*{{{{)")
        template = open_pattern.sub(f"{{{{ {var_name} }}}}", template)
        # Remove orphaned closing tags </var> only if no pair was found
        # (if a pair was found, the closing tag is kept as part of the XML structure)
        if not pair_was_found:
            close_pattern = re.compile(rf"</{escaped}>")
            template = close_pattern.sub("", template)
    return template


def build_messages(
    system_prompt: str | None,
    user_prompt: str | None,
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
