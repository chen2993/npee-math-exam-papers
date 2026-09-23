"""Rendering questions into the class's question environments.

A render question carries inline TeX plus optional figures. Figures are emitted as
standalone TikZ blocks; choices are emitted as labels so the class controls the
four-column layout. Circled markers (①…⑩) are normalized to the class macro so they
survive inside and outside math mode.

Four normalizations live here because the class owns the final typography and the
stored records cannot be rewritten on the fly. Each one drops a piece of source
paper furniture that the class already prints, so a stored copy would double it:

* a stem must not carry a copied section heading (``一、选择题：…``) or a
  publisher's public-account stamp (``（公众号：…）``): the class prints the
  heading itself, and the stamp is page furniture.
* a solution stem must not print its own ``（本题满分 X 分）`` label, because the
  class derives that label from the registered ``points``; a stored label is
  stripped so legacy records do not print the score twice.
* a choice stem must not carry its own ``（ ）`` / ``\\left(\\quad\\right)``, because
  ``\\ExamSelection`` prints the placeholder itself.
* a subpart must not carry its own ``（I）`` ordinal, because the class numbers each
  subpart; an in-text cross reference such as ``在第（I）问的基础上`` is kept.
* a proposition sequence (``①``…``④``) starts each proposition on its own hanging
  line via ``\\ExamStatementMarker``. Markers written at the head of an inline math
  run (``$①x>0$``) are pulled out of math mode first, because the marker is a
  paragraph-level command. Markers inside an alignment environment, or in the
  middle of a formula, stay inline.
"""

from __future__ import annotations

import re
from typing import Any

from npee_math_papers.core.domain import SECTION_LABELS
from npee_math_papers.service.rendering.text import tex_literal

#: section -> Chinese heading, used when the class is not driving the headings.
SECTIONS = SECTION_LABELS

#: Circled digits that the source data uses for numbered options.
CIRCLED_DIGITS = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5", "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9", "⑩": "10"}

#: Environments whose body is a grid: a marker there belongs to a cell, never to
#: the paragraph, so it must stay inline even when it looks like a proposition head.
_ALIGNMENT_ENVIRONMENTS = (
    "array",
    "matrix",
    "pmatrix",
    "bmatrix",
    "Bmatrix",
    "vmatrix",
    "Vmatrix",
    "smallmatrix",
    "cases",
)
_ALIGNMENT_TOKEN_RE = re.compile(r"\\(begin|end)\{([A-Za-z*]+)\}")

#: A leading solution score label, e.g. ``（本题满分 12 分）`` or ``本题满分 $10$ 分。``.
#: The class prints the score from ``points``, so a stored copy is redundant.
_SCORE_LABEL_RE = re.compile(
    r"^\s*[（(]?\s*本题满分\s*(?:[0-9０-９]|\$[^$]*\$|\{[^{}]*\})+\s*分\s*[）)]?\s*[。.．]?\s*"
)

#: A blank answer placeholder: ``\left(\quad\right)`` in math, or ``（ ）`` in text.
_BLANK_PLACEHOLDER = (
    r"(?:\\left\s*\(\s*(?:\\(?:quad|qquad|,|;|!| )\s*)*\\right\s*\)"
    r"|[（(]\s*(?:\\(?:quad|qquad)\s*|\s|　)*[）)])"
)

#: A redundant blank written just before ``\ExamSelection``. The class macro prints
#: the choice placeholder itself, so a stored copy would print the parentheses twice.
_REDUNDANT_CHOICE_BLANK_RE = re.compile(_BLANK_PLACEHOLDER + r"(?P<closer>\$?)\s*(?=\\ExamSelection)")

#: A section heading copied from the source page, e.g.
#: ``一、选择题：1～10 小题，每小题 5 分，共 50 分。下列每题给出的四个选项中，只有一个选项是最符合题目要求的。``
#: The class prints the heading (and the same instruction) itself, so a stored
#: copy would print the whole block twice.
_SECTION_HEADING_RE = re.compile(
    r"^\s*[一二三四五六七八九十]\s*[、.．]\s*(?:选择题|填空题|解答题)\s*[:：]?\s*"
    r"[0-9０-９~～\-—－\s]+(?:小题|题)[，,、]?\s*"
    r"(?:每小题\s*[0-9０-９]+\s*分[，,]?\s*)?"
    r"(?:共\s*[0-9０-９]+\s*分)?[。.．]?\s*"
    r"(?:下列每题给出的四个选项中[，,]?\s*只有一个选项是最符合[^。.．]{0,8}要求的[。.．]?\s*"
    r"|解答应写出文字说明[、,]?\s*证明过程或演算步骤[。.．]?\s*)?"
)

#: A publisher's public-account stamp, e.g. ``（公众号：风中羽小易）``. It is page
#: furniture, not question text.
_WATERMARK_RE = re.compile(r"[（(]\s*(?:公众号|微信公众号|微信号)\s*[:：][^）)]*[）)]\s*")

def strip_section_heading(text: str) -> str:
    """Drop a section heading copied into the stem.

    The class prints ``一、选择题：…`` (with the instruction sentence) itself, so
    a stored copy renders the heading twice -- once from the class, once from the
    stem. Only a heading *at the start of the stem* is removed.
    """

    return _SECTION_HEADING_RE.sub("", text, count=1).lstrip()

def strip_watermark(text: str) -> str:
    """Drop a publisher's public-account stamp wherever it appears."""

    if "公众号" not in text and "微信号" not in text:
        return text
    return _WATERMARK_RE.sub("", text).strip()

#: A leading subpart label such as ``（I）``, ``（$\mathrm{II}$）`` or ``(1)``. The class
#: numbers subparts itself, so a stored label would print the ordinal twice.
_LEADING_SUBPART_LABEL_RE = re.compile(
    r"^\s*[（(]\s*\$?\s*(?:\\mathrm\{)?\s*(?:I{1,3}|IV|V|[0-9]{1,2})\s*\}?\s*\$?\s*[）)]\s*"
)


def strip_solution_score_label(text: str) -> str:
    """Drop a redundant ``（本题满分 X 分）`` prefix from a solution stem.

    The class re-prints the score from the question's registered ``points``, so a
    stored label would render the score twice. A stem that contained nothing but
    the label keeps an empty (but valid) body; the class label and the subparts
    still carry the question. Returns ``{}`` for that case so the render-model
    contract (non-empty inline TeX) holds without printing a stray character.
    """

    stripped = _SCORE_LABEL_RE.sub("", text, count=1).strip()
    if not stripped:
        return "{}"
    return stripped


def strip_redundant_choice_blank(text: str) -> str:
    """Drop a blank placeholder that would double the ``\\ExamSelection`` blank.

    Source papers print ``（ ）`` themselves, so some records store it next to the
    class macro. ``\\ExamSelection`` already emits the placeholder, so the stored
    copy is removed; a closing math delimiter immediately after it is preserved so
    the remaining formula still terminates.
    """

    return _REDUNDANT_CHOICE_BLANK_RE.sub(lambda match: match.group("closer"), text)


def strip_leading_subpart_label(text: str) -> str:
    """Drop a stored ``（I）`` ordinal from a subpart.

    The class numbers subparts itself, so a stored ordinal would print twice
    (``(1) （I）``). An in-text cross reference such as ``在第（I）问的基础上`` is not
    at the start of the line and is therefore untouched.
    """

    stripped = _LEADING_SUBPART_LABEL_RE.sub("", text, count=1).strip()
    return stripped or "{}"


def render_figure(figure: dict[str, Any]) -> str:
    if figure["kind"] == "tikz":
        return f"\\ExamIncludeTikz{{{figure['latex']}}}"
    return f"\\ExamIncludeFigure[width=\\linewidth,alt={{{tex_literal(figure['description'], 'figure.description')}}}]{{{figure['path']}}}"


def score_option(points: Any) -> str:
    if points is None:
        return ""
    if isinstance(points, float) and points.is_integer():
        points = int(points)
    return f",points={points}"


def repair_math_led_markers(text: str) -> str:
    """Lift a marker written at the head of an inline math run out of math mode.

    ``\\ExamStatementMarker`` is a paragraph-level command and cannot run inside
    ``$...$``. A stored proposition sometimes starts its inline math with the
    marker, in two shapes:

    ``$①x>0$``   -> ``①$x>0$``   (marker leaves math, the formula re-opens)
    ``$\\ ①$连续`` -> ``①连续``     (the run held only the marker; drop the wrapper)

    Only a marker immediately after ``$`` (modulo spaces and a thin-space command)
    is moved, so a marker in the middle of a formula, an alignment cell, or a
    choice text is untouched. The empty-run case is applied first so the
    content-bearing case cannot re-wrap a marker the first rule already freed.
    """

    if not any(marker in text for marker in CIRCLED_DIGITS):
        return text
    marker_class = "".join(CIRCLED_DIGITS)
    lead = r"(?:\\[ ,;:!]|[ \t])*"
    text = re.sub(rf"\$\s*{lead}([{marker_class}])\s*\$", r"\1", text)
    text = re.sub(rf"\$\s*{lead}([{marker_class}])", r"\1$", text)
    return text


def _alignment_mask(text: str) -> list[bool]:
    """Flag each index that lies inside an alignment environment body."""

    mask = [False] * len(text)
    depth = 0
    for token in _ALIGNMENT_TOKEN_RE.finditer(text):
        if token.group(2) not in _ALIGNMENT_ENVIRONMENTS:
            continue
        if token.group(1) == "begin":
            depth += 1
        elif depth:
            depth -= 1
        if depth:
            for index in range(token.end(), len(mask)):
                mask[index] = True
    return mask


def _sequence_markers(text: str) -> set[int]:
    """Return the indices of markers that begin a proposition in a sequence.

    A proposition sequence is two or more markers that each head a block: a marker
    at the start of a text-mode run (which, after :func:`repair_math_led_markers`,
    includes markers lifted out of a math run). A marker in the middle of a formula
    or inside an alignment environment heads nothing and is left inline. Fewer than
    two such heads is not a sequence, so a lone marker stays inline.
    """

    in_alignment = _alignment_mask(text)
    heads: set[int] = set()
    math_mode = False
    for index, char in enumerate(text):
        if char == "$" and (index == 0 or text[index - 1] != "\\"):
            math_mode = not math_mode
            continue
        if char in CIRCLED_DIGITS and not math_mode and not in_alignment[index]:
            heads.add(index)
    return heads if len(heads) >= 2 else set()


#: ``\textcircled{N}`` as copied from word-processor sources, either bare or
#: wrapped in math mode (``$\text{\textcircled{1}}$``). Both spell the same
#: thing as a raw U+246x circled digit, so they are folded into one form before
#: any layout decision is made; otherwise the two spellings would render
#: differently even though the source prints them identically.
_TEXTCIRCLED_MATH_RE = re.compile(r"\$\s*\\text\s*\{\s*\\textcircled\s*\{\s*(\d{1,2})\s*\}\s*\}\s*\$")
_TEXTCIRCLED_RE = re.compile(r"\\textcircled\s*\{\s*(\d{1,2})\s*\}")

def normalize_textcircled(text: str) -> str:
    """Rewrite ``\textcircled{N}`` as the equivalent raw circled digit."""

    def glyph(match: re.Match[str]) -> str:
        value = int(match.group(1))
        return chr(0x2460 + value - 1) if 1 <= value <= 10 else match.group(0)

    if "textcircled" not in text:
        return text
    return _TEXTCIRCLED_RE.sub(glyph, _TEXTCIRCLED_MATH_RE.sub(glyph, text))

def format_circled_markers(text: str, *, statement_lines: bool = False) -> str:
    """Use the class circled-number API and break proposition sequences cleanly."""

    text = normalize_textcircled(text)
    if not any(marker in text for marker in CIRCLED_DIGITS):
        return text
    if not statement_lines:
        # Choices and subparts stay in the running line; only the glyph changes.
        return "".join(
            f"\\ExamCircledNumber{{{CIRCLED_DIGITS[char]}}}" if char in CIRCLED_DIGITS else char
            for char in text
        )

    text = repair_math_led_markers(text)
    heads = _sequence_markers(text)
    return "".join(
        f"\\ExamStatementMarker{{{CIRCLED_DIGITS[char]}}}"
        if index in heads
        else f"\\ExamCircledNumber{{{CIRCLED_DIGITS[char]}}}" if char in CIRCLED_DIGITS else char
        for index, char in enumerate(text)
    )


def render_question(question: dict[str, Any], occurrence: int) -> str:
    qid = f"p{occurrence:03d}-q{question['number']}"
    section = question["section"]
    options = f"id={qid}{score_option(question['points'])}"
    if section in {"choice", "fill"}:
        # Objective-question scores remain available to totals and QA, but are
        # intentionally omitted from the printed question line.
        options += ",show-points=false"
    if section == "choice":
        begin = f"\\begin{{ExamChoiceQuestion}}[{options}]"
        end = "\\end{ExamChoiceQuestion}"
    elif section == "fill":
        begin = f"\\begin{{ExamFillQuestion}}[{options}]"
        end = "\\end{ExamFillQuestion}"
    else:
        solution_options = f"id={qid}"
        if question["points"] is None:
            solution_options += ",show-points=false"
        # Response-cell geometry is selected by npee-math-exam.cls from the
        # solution-section structure.  Keep generated paper sources focused
        # on content and metadata; never leak a physical answer height here.
        begin = f"\\begin{{ExamSolutionQuestion}}[{solution_options}]"
        if question["points"] is not None:
            begin += f"{{{question['points']}}}"
        end = "\\end{ExamSolutionQuestion}"

    stem_latex = question["latex"]
    # Source-page furniture the class already prints, or that is not question
    # text at all. Stripping is idempotent, so a clean record passes through.
    stem_latex = strip_watermark(stem_latex)
    stem_latex = strip_section_heading(stem_latex)
    if section == "solution":
        stem_latex = strip_solution_score_label(stem_latex)
    elif section == "choice":
        stem_latex = strip_redundant_choice_blank(stem_latex)
    # A stem can consist solely of stripped furniture (a watermark alone, say).
    # The render-model contract requires a non-empty body, and ``{}`` prints
    # nothing.
    if not stem_latex.strip():
        stem_latex = "{}"
    lines = [begin, format_circled_markers(stem_latex, statement_lines=True)]
    # Diagrams belong to the stem block.  Emit them before subparts and choices
    # so a reader encounters the visual prompt before selecting an answer.
    lines.extend(render_figure(figure) for figure in question["figures"])
    for index, part in enumerate(question["subparts"], 1):
        subpart_latex = strip_leading_subpart_label(part["latex"])
        lines.append(f"\\ExamSubpart{{{qid}-s{index}}}{format_circled_markers(subpart_latex)}")
    if section == "choice":
        choices = [format_circled_markers(item) for item in question["choices"]]
        command = "ExamGraphicChoices" if any("tikzpicture" in item for item in choices) else "ExamChoices"
        lines.append(f"\\{command}{{{choices[0]}}}{{{choices[1]}}}{{{choices[2]}}}{{{choices[3]}}}")
    lines.append(end)
    return "\n".join(lines)


def render_body(questions: list[dict[str, Any]], occurrence: int) -> str:
    lines: list[str] = ["% Generated body fragment; do not edit by hand."]
    previous: str | None = None
    for question in questions:
        section = question["section"]
        if section != previous:
            command = "ExamSection" if previous is None else "ExamSectionContinue"
            lines.extend([f"\\{command}{{{SECTIONS[section]}}}", ""])
            previous = section
        lines.append(render_question(question, occurrence))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
