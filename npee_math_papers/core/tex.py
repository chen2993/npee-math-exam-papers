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
#: A fraction's size must match the math position it sits in: ``\frac`` is wrong in
#: *body* text (too small beside display maths) and ``\dfrac`` is wrong in a
#: *script* slot (too large: it re-inflates a fraction TeX deliberately shrank,
#: which overflows the line). The position, not the command, decides -- see
#: :func:`fraction_position_errors`, which classifies each occurrence.
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


def fraction_positions(text: str) -> list[tuple[str, str, int]]:
    r"""Classify every explicit fraction by the math style it will be set in.

    Returns ``(command, position, offset)`` for each ``\dfrac`` / ``\tfrac`` / bare
    ``\frac``, where *position* is:

    ``"script"``
        inside a superscript or subscript group;
    ``"nested"``
        inside another fraction's numerator or denominator;
    ``"body"``
        anywhere else.

    TeX sizes a fraction from the *current math style*, and both a script slot and
    a fraction's numerator/denominator are already one level down. Writing
    ``\dfrac`` there re-inflates the fraction instead of matching its surroundings,
    so the line grows: measured on this class, ``x^{\dfrac{a}{b}}`` is 24.3pt tall
    against 13.3pt for ``x^{\frac{a}{b}}``, and
    ``\dfrac{\arctan\dfrac{1}{x}}{\sec x}`` is 30.6pt against 23.5pt with an inner
    ``\frac``. Body text is the opposite case, where ``\frac`` looks shrunken
    beside display maths.

    The scan tracks, per open brace, what opened it -- ``^``/``_`` or a fraction
    argument. ``\dfrac`` takes *two* arguments, and those arguments may themselves
    contain fractions, so the outstanding-argument counters form a stack rather
    than a single counter (a single counter is clobbered by the first nested
    fraction, which then mis-classifies the outer denominator).
    """

    findings: list[tuple[str, str, int]] = []
    groups: list[str] = []          # per open brace: "script" | "frac" | "other"
    arg_counts: list[int] = []      # outstanding brace arguments, innermost last
    pending_script = False          # this brace is a ^/_ argument
    offset = 0
    while offset < len(text):
        char = text[offset]
        if char == "\\":
            match = re.match(r"\\([A-Za-z]+)", text[offset:])
            if match:
                name = match.group(1)
                if name in {"dfrac", "tfrac", "frac"} and not (name == "frac" and text[offset - 1:offset] in {"d", "t"}):
                    if any(kind == "script" for kind in groups):
                        position = "script"
                    elif any(kind == "frac" for kind in groups):
                        position = "nested"
                    else:
                        position = "body"
                    findings.append((name, position, offset))
                    arg_counts.append(2)
                offset += match.end()
                pending_script = False
                continue
            offset += 2
            continue
        if char in "^_":
            pending_script = True
            offset += 1
            continue
        if char == "{":
            if arg_counts and arg_counts[-1] > 0:
                groups.append("frac")
                arg_counts[-1] -= 1
                if arg_counts[-1] == 0:
                    arg_counts.pop()
            elif pending_script:
                groups.append("script")
            else:
                groups.append("other")
            pending_script = False
            offset += 1
            continue
        if char == "}":
            if groups:
                groups.pop()
            offset += 1
            continue
        if not char.isspace():
            # A single-token argument (``^2``, ``^\alpha``) ends here.
            pending_script = False
        offset += 1
    return findings

def fraction_position_errors(text: str) -> list[str]:
    r"""Return one human-readable message per mis-sized fraction.

    ``\frac`` is correct in a reduced slot (a script or another fraction's
    argument) and ``\dfrac`` is correct in body text; either one used in the
    other's place changes how tall the expression sets.
    """

    errors: list[str] = []
    for command, position, _offset in fraction_positions(text):
        if position == "body":
            if command == "frac":
                errors.append("\\frac in a body position; use \\dfrac (a script-size fraction looks shrunken next to display math)")
            continue
        where = "a superscript or subscript" if position == "script" else "another fraction's numerator or denominator"
        if command in {"dfrac", "tfrac"}:
            errors.append(
                f"\\{command} is inside {where}; use \\frac there "
                "(that slot is already a reduced style, so a display-size fraction overflows it)"
            )
    return errors

def fraction_size_corrections(text: str) -> dict[int, str]:
    """Return ``{offset: replacement command}`` for every mis-sized fraction.

    Shared by the render repair and the frontend's TypeScript twin, so both
    surfaces normalise a stored expression identically.
    """

    corrections: dict[int, str] = {}
    for command, position, offset in fraction_positions(text):
        if position == "body":
            if command == "frac":
                corrections[offset] = "dfrac"
        elif command in {"dfrac", "tfrac"}:
            corrections[offset] = "frac"
    return corrections

def validate_inline_tex(value: Any, context: str) -> str:
    """Validate and return one inline-TeX string.

    Rejects block math, unresolved ``[待核]`` markers, literal Unicode backslash
    escapes and unguarded CJK in math. A fraction whose size does not match its
    position is *not* rejected here: see :func:`fraction_position_errors`.
    """

    text = nonempty_string(value, context)
    if LITERAL_UNICODE_BACKSLASH_RE.search(text):
        fail(f"{context} contains a literal Unicode backslash escape; normalize the source paper.json first")
    if BLOCK_MATH_RE.search(text):
        fail(f"{context} contains block math; use inline math only")
    if PENDING_MARKER_RE.search(text):
        fail(f"{context} still contains a pending visual-review marker")
    # Fraction *size* is not enforced here. The store re-validates on read, so a
    # hard rejection would stop legacy records from loading at all; the renderer
    # normalises the size (repair_fraction_sizes) and the audit reports it as a
    # data-quality finding instead. See fraction_position_errors().
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
