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


MISSING = object()


def get_path(obj: Any, path: str) -> Any:
    """Follow a dotted path through dicts and lists; return MISSING if absent."""
    if not path:
        return obj
    current = obj
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return MISSING
            current = current[segment]
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return MISSING
        else:
            return MISSING
    return current


def scalar_paths(value: Any, prefix: str = "") -> list[str]:
    """Dotted paths to the scalar leaves of a JSON value."""
    if isinstance(value, dict):
        paths = []
        for key, child in value.items():
            paths += scalar_paths(child, f"{prefix}.{key}" if prefix else str(key))
        return paths
    if isinstance(value, list):
        # Lists of scalars (e.g. score distributions) are not a single value
        return []
    return [prefix]


def list_paths(value: Any, prefix: str = "") -> list[str]:
    """Dotted paths to the lists of scalars (score distributions) in a JSON value."""
    if isinstance(value, dict):
        paths = []
        for key, child in value.items():
            paths += list_paths(child, f"{prefix}.{key}" if prefix else str(key))
        return paths
    if isinstance(value, list) and value and prefix:
        if not any(isinstance(item, dict | list) for item in value):
            return [prefix]
    return []
