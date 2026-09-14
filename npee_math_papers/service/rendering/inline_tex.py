"""Inline-TeX validation and historical-write repair.

This is the layer that makes old records render correctly. Published extraction runs
wrote some constructs wrongly (a doubled row separator before a command, a lost
backslash before a command name, a text-mode ``array``, a unit exponent written
directly after ``^``). Rather than rewrite the storage format, rendering repairs
those on the way out; keeping the rules in one module makes them auditable.

The rules are deliberately conservative: each one only rewrites a pattern that is
unambiguously broken, so a correct document passes through byte-for-byte.
"""

from __future__ import annotations

import re
from typing import Any

from npee_math_papers.core.tex import (
    BLOCK_MATH_RE,
    CJK_MATH_CHAR_RE,
    LITERAL_UNICODE_BACKSLASH_RE,
    TEXT_IN_MATH_COMMANDS,
    TIKZ_DOUBLE_COMMAND_RE,
    AlignmentEnvironment,
)
from npee_math_papers.service.rendering.errors import fail
from npee_math_papers.service.rendering.text import nonempty_string

#: Environments in which ``\\`` is a row separator rather than a line break.
ALIGNMENT_ENVIRONMENTS = set(AlignmentEnvironment)

# Generated sources let the class own the ``\\limits`` placement.  Strip any
# source-level limits here so a record containing ``\\max\\limits`` does not
# become a double-limits operator after the class wrapper is applied.
OPERATOR_LIMIT_RE = re.compile(
    r"\\(limsup|liminf|iiiint|iiint|iint|oiiint|oiint|max|min|sup|inf|lim|sum|prod|bigcap|bigcup)(?![A-Za-z@])"
    r"(?:\\limits)*"
)

DOUBLE_SLASH_MATH_COMMANDS = (
    "ne",
    "le",
    "ge",
    "frac",
    "dfrac",
    "Delta",
    "lambda",
    "chi",
    "alpha",
    "beta",
    "gamma",
    "Phi",
    "Sigma",
    "Gamma",
    "Omega",
    "rho",
    "hat",
    "mu",
    "nu",
    "sigma",
    "sim",
    "xrightarrow",
    "ddots",
    "vdots",
    "ldots",
    "cdots",
    "infty",
    "eta",
    "cup",
    "triangle",
)
INLINE_TEX_COMMANDS = {
    "alpha", "arccos", "arcsin", "arctan", "begin", "beta", "boldsymbol",
    "cos", "dfrac", "displaystyle", "eta", "frac", "gamma", "infty", "int",
    "lambda", "left", "lim", "ln", "mathbb", "mathbf", "mathcal", "mathrm",
    "mathsf", "operatorname", "right", "sin", "sqrt", "sum", "tan", "text",
    "theta", "varphi",
}
# Any known TeX command that may legitimately appear right after a row separator
# as ``\\\cmd``. ``repair_alignment_rows`` must NOT strip a backslash from these,
# otherwise a valid row separator (``\\``) plus command (``\hline``/``\vdots``)
# collapses into ``\\hline`` (row separator plus literal text) and breaks both
# the compile (``Misplaced \noalign``) and the rendered output. Broadened from the
# original inline-command list so row-level commands and every other real command
# are preserved; this is checked by membership only, never by pattern.
ALIGNMENT_ROW_COMMANDS = frozenset(INLINE_TEX_COMMANDS) | {
    "cline", "hdashline", "hline", "vdots", "ddots", "cdots", "ldots",
    "Phi", "Psi", "Omega", "Lambda", "Gamma", "Delta", "Theta", "Sigma",
    "Xi", "Pi", "Upsilon", "times", "cdot", "neq", "leq", "geq", "pm", "mp",
    "quad", "qquad", "dfrac", "left", "right", "text", "mathrm", "mathbf",
    "boldsymbol", "overline", "underline", "hat", "bar", "vec", "dot", "ddot",
    "subset", "supset", "subseteq", "supseteq", "cup", "cap", "emptyset",
    "to", "rightarrow", "leftarrow", "mapsto", "forall", "exists", "in",
    "notin", "infty", "partial", "nabla", "prod", "limsup", "liminf",
    "max", "min", "sup", "inf", "log", "exp", "cot", "sec", "csc", "sinh",
    "cosh", "tanh", "triangle", "sim", "simeq", "approx", "equiv", "propto",
    "xrightarrow", "overset", "underset", "mathbb", "mathcal", "mathsf",
    "mathtt", "operatorname", "tfrac", "smallmatrix", "quad",
}
ALIGNMENT_ENVIRONMENTS = set(AlignmentEnvironment)
QUESTION_KEYS = {"number", "section", "points", "latex", "choices", "subparts", "figures"}
FIGURE_KEYS = {"kind", "latex", "path", "description", "exception_reason"}
# Generated sources let the class own the ``\\limits`` placement.  Strip any
# source-level limits here so a record containing ``\\max\\limits`` does not
# become a double-limits operator after the class wrapper is applied.
OPERATOR_LIMIT_RE = re.compile(
    r"\\(limsup|liminf|iiiint|iiint|iint|oiiint|oiint|max|min|sup|inf|lim|sum|prod|bigcap|bigcup)(?![A-Za-z@])"
    r"(?:\\limits)*"
)


def balanced_group_end(value: str, start: int) -> int | None:
    depth = 0
    offset = start
    while offset < len(value):
        if value[offset] == "\\":
            offset += 2
            continue
        if value[offset] == "{":
            depth += 1
        elif value[offset] == "}":
            depth -= 1
            if depth == 0:
                return offset + 1
        offset += 1
    return None


def cjk_math_characters(value: str) -> list[str]:
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
            delimiter = None if delimiter == "dollar" else "dollar" if delimiter is None else delimiter
            offset += 1
            continue
        if delimiter is not None and CJK_MATH_CHAR_RE.match(value[offset]):
            start = offset
            while offset < len(value) and CJK_MATH_CHAR_RE.match(value[offset]):
                offset += 1
            findings.append(value[start:offset])
            continue
        offset += 1
    return findings


def validate_inline_tex(value: Any, field: str) -> str:
    text = nonempty_string(value, field)
    if LITERAL_UNICODE_BACKSLASH_RE.search(text):
        fail(f"{field} contains a literal Unicode backslash escape; normalize the source paper.json first")
    text = text.replace(r"\bb", r"\mathbb")
    text = re.sub(r"(?<!\\)\\\\%", r"\%", text)
    text = re.sub(
        r"(?<!\\)\\([A-Z0-9])(?![A-Za-z])",
        lambda match: r"\\" + match.group(1),
        text,
    )
    text = re.sub(
        rf"(?<!\\)\\\\({'|'.join(DOUBLE_SLASH_MATH_COMMANDS)})(?![A-Za-z])",
        lambda match: "\\" + match.group(1),
        text,
    )
    text = re.sub(r"(?<!\\)\\n(?![A-Za-z])", r"\\NPEEQuestionContinuation ", text)
    text = repair_repeated_escaped_braces(text)
    text = repair_alignment_rows(text)
    text = repair_text_arrays(text)
    text = repair_text_mode_unit_exponents(text)
    text = repair_quoted_math_runs(text)
    text = re.sub(r"\\Exam(Selection|Blank)(?=[\u3400-\u9fff])", r"\\Exam\1{}", text)
    text = repair_cases_rows(text, field)
    text = OPERATOR_LIMIT_RE.sub(lambda match: f"\\{match.group(1)}", text)
    if "tikzpicture" in text and TIKZ_DOUBLE_COMMAND_RE.search(text):
        fail(f"{field} contains a doubled TikZ command slash; normalize the source paper.json first")
    unsafe_cjk = cjk_math_characters(text)
    if unsafe_cjk:
        fail(f"{field} contains CJK punctuation in math mode: {', '.join(unsafe_cjk)}; wrap it in \\text{{...}}")
    if BLOCK_MATH_RE.search(text):
        fail(f"{field} contains display math; use inline math only")
    if re.search(r"(?<!d)\\frac\b", text):
        fail(f"{field} uses \\frac; use \\dfrac")
    # A few imported records end a final math placeholder as ``$x=\ExamBlank``
    # or contain a choice such as ``$4``.  Close only an odd, inline delimiter
    # count; this keeps the source data readable while preventing a TeX mode
    # leak into the next choice or paper.
    if text.count("$") % 2:
        placeholder = re.search(r"\\Exam(?:Selection|Blank)([^$]*)$", text)
        if placeholder:
            text = text[:placeholder.end(0) - len(placeholder.group(1))] + "$" + placeholder.group(1)
        else:
            text += "$"
    return text


def repair_repeated_escaped_braces(text: str) -> str:
    """Collapse doubled escaped braces outside matrix-like environments."""

    environment_pattern = re.compile(r"\\(begin|end)\{([A-Za-z*]+)\}")
    repeated_brace_pattern = re.compile(r"(?<!\\)\\\\([{}])")
    output: list[str] = []
    offset = 0
    alignment_depth = 0

    for token in environment_pattern.finditer(text):
        segment = text[offset : token.start()]
        if alignment_depth == 0:
            segment = repeated_brace_pattern.sub(lambda match: "\\" + match.group(1), segment)
        output.append(segment)
        output.append(token.group(0))
        environment = token.group(2)
        if environment in ALIGNMENT_ENVIRONMENTS:
            if token.group(1) == "begin":
                alignment_depth += 1
            elif alignment_depth:
                alignment_depth -= 1
        offset = token.end()

    tail = text[offset:]
    if alignment_depth == 0:
        tail = repeated_brace_pattern.sub(lambda match: "\\" + match.group(1), tail)
    output.append(tail)
    return "".join(output)


def repair_alignment_rows(text: str) -> str:
    """Restore single-slash row starts inside common math alignments."""

    pattern = re.compile(
        r"\\begin\{(?P<environment>cases|matrix|pmatrix|bmatrix|Bmatrix|vmatrix|Vmatrix|smallmatrix|array)\}"
        r"(?P<body>.*?)"
        r"\\end\{(?P=environment)\}",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        body = re.sub(
            # Capture only letters, so the token is a real command name. A greedy
            # ``[A-Za-z0-9]+`` would swallow the argument of a command that follows
            # a row separator (``\\\dfrac38`` -> ``dfrac38``) and then wrongly strip
            # one backslash, turning a valid row separator plus ``\dfrac38`` into
            # ``\\dfrac38`` — i.e. a row separator plus the literal text ``dfrac38``.
            r"(?<!\\)\\\\\\([A-Za-z]+)",
            lambda item: item.group(0)
            if item.group(1) in ALIGNMENT_ROW_COMMANDS
            else r"\\" + item.group(1),
            match.group("body"),
        )
        body = re.sub(
            r"(?<!\\)\\([0-9])|(?<!\\)\\([A-Za-z])(?![A-Za-z])|(?<!\\)\\([\(\[\-])",
            lambda item: r"\\" + next(group for group in item.groups() if group),
            body,
        )
        body = re.sub(
            r"(?<=[A-Za-z0-9}\)])\\([A-Z][A-Z0-9]*)\s*&",
            lambda item: r"\\" + item.group(1) + "&",
            body,
        )
        return f"\\begin{{{match.group('environment')}}}{body}\\end{{{match.group('environment')}}}"

    return pattern.sub(replace, text)


def repair_text_arrays(text: str) -> str:
    """Convert a single-column array used in text mode into a minipage."""

    pattern = re.compile(r"\\begin\{array\}\{l\}(.*?)\\end\{array\}", re.DOTALL)
    offset = 0
    repaired: list[str] = []
    for match in pattern.finditer(text):
        repaired.append(text[offset : match.start()])
        if text[: match.start()].count("$") % 2:
            repaired.append(match.group(0))
        else:
            repaired.append(
                r"\par\begin{minipage}{\linewidth}"
                + match.group(1)
                + r"\end{minipage}\par"
            )
        offset = match.end()
    repaired.append(text[offset:])
    return "".join(repaired)


def repair_text_mode_unit_exponents(text: str) -> str:
    """Render plain-text unit exponents without entering math mode."""

    unit_pattern = re.compile(r"\b([A-Za-z]+/[A-Za-z]+)\^([0-9]+)\b")
    fragments = re.split(r"(?<!\\)\$", text)
    for index in range(0, len(fragments), 2):
        fragments[index] = unit_pattern.sub(
            lambda match: f"{match.group(1)}\\textsuperscript{{{match.group(2)}}}",
            fragments[index],
        )
    return "$".join(fragments)


def repair_quoted_math_runs(text: str) -> str:
    """Close a math run before a quoted Chinese connective when it was omitted."""

    return re.sub(
        r"(\$[^$]*?\\[A-Za-z]+[^$]*?)(”[\u3400-\u9fff]{1,8}“)\$",
        r"\1$\2$",
        text,
    )


def repair_cases_rows(text: str, field: str) -> str:
    """Restore omitted row separators only inside a cases environment."""

    start_token = r"\begin{cases}"
    end_token = r"\end{cases}"
    offset = 0
    repaired: list[str] = []
    while True:
        start = text.find(start_token, offset)
        if start < 0:
            repaired.append(text[offset:])
            return "".join(repaired)
        end = text.find(end_token, start + len(start_token))
        if end < 0:
            fail(f"{field} has an unclosed cases environment")
        repaired.append(text[offset : start + len(start_token)])
        body = text[start + len(start_token) : end]
        cells = body.split("&")
        if len(cells) > 2:
            for index in range(1, len(cells) - 1):
                segment = cells[index]
                if r"\\" in segment:
                    continue
                boundary = first_top_level_comma(segment)
                if boundary < 0:
                    fail(f"{field} has a cases row without a recoverable separator")
                prefix = segment[: boundary + 1]
                suffix = segment[boundary + 1 :]
                leading = len(suffix) - len(suffix.lstrip())
                expression = suffix[leading:]
                command = re.match(r"\\([A-Za-z]+)", expression)
                # A row that begins with a real command needs the row separator
                # (``\\``) inserted before it; a bare word is instead treated as
                # the start of an inline expression at the row head.  Use the
                # broadened command set so row-level commands (``\hline`` etc.)
                # are recognised here too, matching ``repair_alignment_rows``.
                if command and command.group(1) not in ALIGNMENT_ROW_COMMANDS:
                    expression = "\\" + expression
                else:
                    expression = r"\\" + expression
                cells[index] = prefix + suffix[:leading] + expression
        repaired.append("&".join(cells))
        repaired.append(end_token)
        offset = end + len(end_token)


def first_top_level_comma(value: str) -> int:
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(value):
        if char in depths:
            depths[char] += 1
        elif char in closing and depths[closing[char]]:
            depths[closing[char]] -= 1
        elif char == "," and not any(depths.values()):
            return index
    return -1
