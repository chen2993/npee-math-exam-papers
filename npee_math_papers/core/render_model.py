"""Adapter from the stored question model to the LaTeX builder's render model.

The builder in ``python -m npee_math_papers.service.tex_builder`` already renders a stable,
well-tested shape: a question with ``latex``, ``choices`` (list of strings),
``subparts`` (list of ``{latex}``) and a top-level ``figures`` array. Graphic
choices are detected there by looking for ``tikzpicture`` inside a choice string.

Rather than rewrite that renderer, this module is the one boundary that converts
the schema-3.0 block model into the render model. Storage and rendering can then
evolve independently, and the renderer keeps a single input contract.

The conversion is the inverse of :func:`npee_math_papers.core.question.convert_v2_question` for
stem figures. Choice figures are re-embedded as an inline ``$...$`` TikZ string so
the builder's existing graphic-choice branch handles them unchanged.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _figure_to_render(figure: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": figure.get("kind"),
        "latex": figure.get("latex"),
        "path": figure.get("path"),
        "description": figure.get("description") or "",
        "exception_reason": figure.get("exception_reason"),
    }


def _choice_to_render(choice: Mapping[str, Any], figures: Sequence[Mapping[str, Any]]) -> str:
    """Return a choice as either inline text or an inline TikZ string.

    A graphic choice becomes ``$<tikz>$`` so the builder's graphic-choice branch
    triggers exactly as it did before the schema change.
    """

    text = str(choice.get("text") or "")
    if not figures:
        return text
    drawings = [str(figure.get("latex") or "") for figure in figures if figure.get("kind") == "tikz"]
    if drawings and not text.strip():
        return "$" + "".join(drawings) + "$"
    # Mixed text + figure: keep the text and append the drawings inline.
    suffix = "".join(f"${drawing}$" for drawing in drawings)
    return f"{text}{suffix}"


def question_to_render(question: Mapping[str, Any]) -> dict[str, Any]:
    """Convert one schema-3.0 question into the builder's render shape."""

    stem = question.get("stem") or {}
    choices_raw = question.get("choices") or []
    subparts_raw = question.get("subparts") or []

    stem_figures = [figure for figure in (stem.get("figures") or []) if isinstance(figure, Mapping)]
    render_choices: list[str] = []
    for choice in choices_raw:
        if not isinstance(choice, Mapping):
            continue
        figures = [figure for figure in (choice.get("figures") or []) if isinstance(figure, Mapping)]
        render_choices.append(_choice_to_render(choice, figures))

    render_subparts = [{"latex": str(part.get("text") or "")} for part in subparts_raw if isinstance(part, Mapping)]

    return {
        "number": int(question.get("number")),
        "section": str(question.get("section")),
        "points": question.get("points"),
        "latex": str(stem.get("text") or ""),
        "choices": render_choices,
        "subparts": render_subparts,
        "figures": [_figure_to_render(figure) for figure in stem_figures],
    }


def to_render_questions(questions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert a full schema-3.0 question array into the render shape, sorted."""

    return sorted((question_to_render(question) for question in questions), key=lambda item: item["number"])
