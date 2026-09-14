"""Text helpers: single-line strings and TeX-escaped metadata literals."""

from __future__ import annotations

from typing import Any

from npee_math_papers.service.rendering.errors import fail

#: Characters that must be escaped when a value is emitted as visible text
#: rather than as question LaTeX.
TEX_TEXT_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def nonempty_string(value: Any, field: str) -> str:
    """Return ``value`` if it is a non-empty, single-line string, else fail."""

    if not isinstance(value, str) or not value.strip():
        fail(f"{field} must be a non-empty string")
    if "\n" in value or "\r" in value:
        fail(f"{field} must be a single line")
    return value


def tex_literal(value: Any, field: str) -> str:
    """Escape visible metadata, while leaving question LaTeX untouched."""

    text = nonempty_string(value, field)
    return "".join(TEX_TEXT_ESCAPES.get(char, char) for char in text)


def require_keys(value: dict[str, Any], required: set[str], field: str) -> None:
    """Fail unless ``value`` has exactly the ``required`` keys."""

    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing:
        fail(f"{field} is missing fields: {', '.join(missing)}")
    if extra:
        fail(f"{field} has unsupported fields: {', '.join(extra)}")
