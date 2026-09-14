"""Inline-TeX and TikZ validation.

These rules were previously implemented twice: once in
``agent/tools/import-paper-extraction.py`` for publishing and once in
``python -m npee_math_papers.service.tex_builder`` for rendering. Both callers now import this
module, so a question that passes publish validation cannot later fail rendering
for a reason the publisher never checked.
"""

from __future__ import annotations

import re
from typing import Any

from npee_math_papers.core.errors import ValidationError

BLOCK_MATH_RE = re.compile(
    r"(?:\$\$|\\\[|\\\]|\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?|flalign\*?|displaymath)\})"
)
FRAC_RE = re.compile(r"(?<!d)\\frac\b")
TIKZ_DOUBLE_COMMAND_RE = re.compile(
    r"(?<!\\)\\{2,}(?=(?:addplot|begin|clip|coordinate|draw|end|fill|filldraw|foreach|graph|matrix|node|path|pgfonlayer|pic|scope|shade|tikzset|tikzstyle|useasboundingbox)(?![A-Za-z]))"
)
CJK_IDEOGRAPH_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
CJK_MATH_CHAR_RE = re.compile(
    r"[\u3001\u3002\u300a\u300b\u300c\u300d\u300e\u300f\uff01\uff08\uff09\uff0c\uff1a\uff1b\uff1f\uff3b\uff3d\uff5b\uff5d]"
)
LITERAL_UNICODE_BACKSLASH_RE = re.compile(r"\\u005[cC]")
PENDING_MARKER_RE = re.compile(r"\[待核\]|\[待审\]")

#: Environments in which ``\\`` is a row separator rather than a line break.
AlignmentEnvironment = ("cases", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix", "Vmatrix", "smallmatrix", "array")

# Prose-bearing commands that legitimately contain CJK inside math mode.
TEXT_IN_MATH_COMMANDS = {
    "emph",
    "hbox",
    "mbox",
    "text",
    "textbf",
    "textit",
    "textnormal",
    "textrm",
    "textsc",
    "textsf",
    "textsl",
    "texttt",
    "textup",
}


def fail(message: str) -> None:
    """Raise a :class:`ValidationError` with an actionable message."""

    raise ValidationError(message)


def nonempty_string(value: Any, context: str) -> str:
    """Return ``value`` if it is a non-empty string, else fail."""

    if not isinstance(value, str) or not value.strip():
        fail(f"{context} must be a non-empty string")
    return value


def balanced_group_end(value: str, start: int) -> int | None:
    """Return the offset after a balanced braced group starting at ``start``."""

    depth = 0
    offset = start
    while offset < len(value):
        char = value[offset]
        if char == "\\":
            offset += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return offset + 1
        offset += 1
    return None


def cjk_text_in_math(value: str) -> list[str]:
    """Return CJK fragments rendered directly by a Unicode math font.

    CJK inside ``\\text{...}`` and similar prose commands is allowed; anything
    else is reported so the publisher can wrap it in a text command instead of
    relying on whatever font the math renderer happens to select.
    """

    findings: list[str] = []
    delimiter: str | None = None
    offset = 0
    while offset < len(value):
        if value[offset] == "\\":
            if delimiter is None and value.startswith(r"\(", offset):
                delimiter = "paren"
                offset += 2
                continue
            if delimiter == "paren" and value.startswith(r"\)", offset):
                delimiter = None
                offset += 2
                continue
            command = re.match(r"\\([A-Za-z]+)\*?", value[offset:])
            if delimiter is not None and command and command.group(1) in TEXT_IN_MATH_COMMANDS:
                group_start = offset + len(command.group(0))
                while group_start < len(value) and value[group_start].isspace():
                    group_start += 1
                if group_start < len(value) and value[group_start] == "{":
                    group_end = balanced_group_end(value, group_start)
                    if group_end is not None:
                        offset = group_end
                        continue
            offset += 2
            continue
        if value[offset] == "$":
            if delimiter is None:
                delimiter = "dollar"
            elif delimiter == "dollar":
                delimiter = None
            offset += 1
            continue
        if delimiter is not None and (
            CJK_IDEOGRAPH_RE.match(value[offset]) or CJK_MATH_CHAR_RE.match(value[offset])
        ):
            start = offset
            while offset < len(value) and (
                CJK_IDEOGRAPH_RE.match(value[offset]) or CJK_MATH_CHAR_RE.match(value[offset])
            ):
                offset += 1
            findings.append(value[start:offset])
            continue
        offset += 1
    return findings


def validate_inline_tex(value: Any, context: str) -> str:
    """Validate and return one inline-TeX string.

    Rejects block math, unresolved ``[待核]`` markers, ``\\frac`` (which must be
    ``\\dfrac``), literal Unicode backslash escapes and unguarded CJK in math.
    """

    text = nonempty_string(value, context)
    if LITERAL_UNICODE_BACKSLASH_RE.search(text):
        fail(f"{context} contains a literal Unicode backslash escape; normalize the source paper.json first")
    if BLOCK_MATH_RE.search(text):
        fail(f"{context} contains block math; use inline math only")
    if PENDING_MARKER_RE.search(text):
        fail(f"{context} still contains a pending visual-review marker")
    if FRAC_RE.search(text):
        fail(f"{context} uses \\frac; use \\dfrac explicitly")
    unsafe_cjk = list(dict.fromkeys(cjk_text_in_math(text)))
    if unsafe_cjk:
        fragments = ", ".join(repr(fragment) for fragment in unsafe_cjk)
        fail(
            f"{context} contains CJK text or punctuation in math mode outside a text command: {fragments}; "
            "wrap prose in \\text{...}"
        )
    return text


def validate_tikz(value: Any, context: str) -> str:
    """Validate and return one self-contained TikZ figure body."""

    text = validate_inline_tex(value, context)
    if "tikzpicture" not in text:
        fail(f"{context} must contain a tikzpicture environment")
    if TIKZ_DOUBLE_COMMAND_RE.search(text):
        fail(f"{context} contains a doubled TikZ command slash; normalize the source paper.json first")
    return text
