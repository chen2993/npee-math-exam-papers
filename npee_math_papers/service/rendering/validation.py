"""Validation of the builder's render model.

The builder consumes a normalized "render question" shape (see
:mod:`npee_math_papers.core.render_model`) rather than the stored schema, so a paper is
validated once more at the rendering boundary. This keeps a malformed record from
reaching LaTeX with a confusing error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from npee_math_papers.core.domain import SECTIONS
from npee_math_papers.service.rendering.errors import fail
from npee_math_papers.service.rendering.inline_tex import validate_inline_tex
from npee_math_papers.service.rendering.text import nonempty_string, require_keys

#: Keys accepted on a render-model question / figure.
QUESTION_KEYS = {"number", "section", "points", "latex", "choices", "subparts", "figures"}
FIGURE_KEYS = {"kind", "latex", "path", "description", "exception_reason"}

def validate_figure(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    require_keys(value, FIGURE_KEYS, field)
    kind = value["kind"]
    description = nonempty_string(value["description"], f"{field}.description")
    if kind == "tikz":
        latex = validate_inline_tex(value["latex"], f"{field}.latex")
        if "tikzpicture" not in latex or value["path"] is not None or value["exception_reason"] is not None:
            fail(f"{field} is not a valid TikZ figure")
        return {"kind": kind, "latex": latex, "path": None, "description": description, "exception_reason": None}
    if kind != "asset":
        fail(f"{field}.kind must be tikz or asset")
    if value["latex"] is not None:
        fail(f"{field}.latex must be null for an asset")
    path = nonempty_string(value["path"], f"{field}.path")
    if Path(path).is_absolute() or "\\" in path or any(part in {"", ".", ".."} for part in Path(path).parts):
        fail(f"{field}.path must be a safe repository-relative path")
    asset = repository_path(path, f"{field}.path")
    if not asset.is_file():
        fail(f"{field}.path does not exist: {path}")
    reason = nonempty_string(value["exception_reason"], f"{field}.exception_reason")
    return {"kind": kind, "latex": None, "path": path, "description": description, "exception_reason": reason}


def validate_questions(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail(f"{field} must be a non-empty question array")
    clean: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, raw in enumerate(value):
        context = f"{field}.questions[{index}]"
        if not isinstance(raw, dict):
            fail(f"{context} must be an object")
        require_keys(raw, QUESTION_KEYS, context)
        number = raw["number"]
        if isinstance(number, bool) or not isinstance(number, int) or number < 1 or number in seen:
            fail(f"{context}.number must be a unique positive integer")
        seen.add(number)
        section = raw["section"]
        if section not in SECTIONS:
            fail(f"{context}.section is invalid")
        points = raw["points"]
        if points is not None and (isinstance(points, bool) or not isinstance(points, (int, float)) or points < 0):
            fail(f"{context}.points must be a non-negative number or null")
        latex = validate_inline_tex(raw["latex"], f"{context}.latex")
        choices = raw["choices"]
        if not isinstance(choices, list) or any(not isinstance(item, str) or not item.strip() for item in choices):
            fail(f"{context}.choices must be an array of strings")
        if section == "choice" and len(choices) != 4:
            fail(f"{context}.choice must have four choices")
        if section != "choice" and choices:
            fail(f"{context}.choices must be empty for non-choice questions")
        clean_subparts: list[dict[str, str]] = []
        if not isinstance(raw["subparts"], list):
            fail(f"{context}.subparts must be an array")
        for part_index, part in enumerate(raw["subparts"]):
            part_context = f"{context}.subparts[{part_index}]"
            if not isinstance(part, dict):
                fail(f"{part_context} must be an object")
            require_keys(part, {"latex"}, part_context)
            clean_subparts.append({"latex": validate_inline_tex(part["latex"], f"{part_context}.latex")})
        if not isinstance(raw["figures"], list):
            fail(f"{context}.figures must be an array")
        clean_figures = [validate_figure(item, f"{context}.figures[{i}]") for i, item in enumerate(raw["figures"])]
        clean.append(
            {
                "number": number,
                "section": section,
                "points": points,
                "latex": latex,
                "choices": [validate_inline_tex(item, f"{context}.choices[{i}]") for i, item in enumerate(choices)],
                "subparts": clean_subparts,
                "figures": clean_figures,
            }
        )
    return sorted(clean, key=lambda item: item["number"])
