"""Rendering questions into the class's question environments.

A render question carries inline TeX plus optional figures. Figures are emitted as
standalone TikZ blocks; choices are emitted as labels so the class controls the
four-column layout. Circled markers (①…⑩) are normalized to the class macro so they
survive inside and outside math mode.
"""

from __future__ import annotations

from typing import Any

from npee_math_papers.core.domain import SECTION_LABELS
from npee_math_papers.service.rendering.text import tex_literal

#: section -> Chinese heading, used when the class is not driving the headings.
SECTIONS = SECTION_LABELS

#: Circled digits that the source data uses for numbered options.
CIRCLED_DIGITS = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5", "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9", "⑩": "10"}

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


def format_circled_markers(text: str, *, statement_lines: bool = False) -> str:
    """Use the class circled-number API and break proposition sequences cleanly."""

    if not any(marker in text for marker in CIRCLED_DIGITS):
        return text

    math_mode = False
    outside_count = 0
    outside_total = 0
    for index, char in enumerate(text):
        if char == "$" and (index == 0 or text[index - 1] != "\\"):
            math_mode = not math_mode
        elif char in CIRCLED_DIGITS and not math_mode:
            outside_total += 1
    math_mode = False
    output: list[str] = []
    for index, char in enumerate(text):
        if char == "$" and (index == 0 or text[index - 1] != "\\"):
            math_mode = not math_mode
            output.append(char)
            continue
        if char not in CIRCLED_DIGITS:
            output.append(char)
            continue
        number = CIRCLED_DIGITS[char]
        if math_mode or not statement_lines:
            output.append(f"\\ExamCircledNumber{{{number}}}")
            continue
        # Every text-mode marker in a proposition sequence starts its own
        # hanging line.  The math-mode state is tracked above, so a closing
        # delimiter before ① is never mistaken for a wrapper around it.
        should_break = statement_lines and outside_total > 1
        output.append(
            f"\\ExamStatementMarker{{{number}}}"
            if should_break
            else f"\\ExamCircledNumber{{{number}}}"
        )
        outside_count += 1
    return "".join(output)


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

    lines = [begin, format_circled_markers(question["latex"], statement_lines=True)]
    # Diagrams belong to the stem block.  Emit them before subparts and choices
    # so a reader encounters the visual prompt before selecting an answer.
    lines.extend(render_figure(figure) for figure in question["figures"])
    for index, part in enumerate(question["subparts"], 1):
        lines.append(f"\\ExamSubpart{{{qid}-s{index}}}{format_circled_markers(part['latex'])}")
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
