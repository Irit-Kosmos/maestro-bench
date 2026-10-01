"""
Parsing of LLM outputs that are meant to be JSON.

Models often wrap JSON in markdown fences or leave a trailing comma before a
closing brace. Both are tolerated; anything else stays a string.
"""

import json
import re
from typing import Any

_FENCED = re.compile(r"^```(?:\w*)\n(.*?)```$", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) wrapping LLM output."""
    m = _FENCED.match(text.strip())
    if m:
        return m.group(1).strip()
    return text


def parse_json_output(text: Any) -> Any:
    """Parse text as JSON, tolerating fences and trailing commas.

    Returns the parsed value, or the original text when it is not JSON.
    """
    if not isinstance(text, str):
        return text
    candidate = strip_markdown_fences(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Only reached for invalid JSON, so valid strings are never rewritten
    try:
        return json.loads(_TRAILING_COMMA.sub(r"\1", candidate))
    except json.JSONDecodeError:
        return text
