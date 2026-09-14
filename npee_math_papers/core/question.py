"""The NPEE question model (schema 3.0).

The previous shape put a flat ``figures`` array on the question and, for graphic
multiple-choice options, embedded a whole ``tikzpicture`` inside the option string.
That made figure ownership ambiguous and forced authors to hand-escape TeX inside
JSON. Schema 3.0 replaces it with explicit, typed blocks:

    {
      "number": 7,
      "section": "choice",
      "points": 5,
      "stem":     { "text": "...", "figures": [ Figure, ... ] },
      "choices":  [ { "label": "A", "text": "...", "figures": [ ... ] }, ... ],
      "subparts": [ { "text": "...", "figures": [ ... ] }, ... ]
    }

Benefits:

- A figure always belongs to exactly one place (stem, a labelled choice, or a
  subpart) instead of living in a shared array with an implicit anchor.
- Choices carry an explicit label, so the renderer never has to infer "A".
- Stem, choices and subparts share one :class:`Block` shape, so the renderer and
  the frontend use a single code path.

A :class:`Figure` is either an embedded TikZ drawing or an approved asset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from npee_math_papers.core.domain import ASSET_EXTENSIONS, CHOICE_LABELS, SECTIONS
from npee_math_papers.core.questions import validate_figure as _validate_figure_v2
from npee_math_papers.core.tex import fail, nonempty_string, validate_inline_tex as _validate_inline_tex

QUESTION_SCHEMA_VERSION = "3.0"
BLOCK_KEYS = {"text", "figures"}
CHOICE_KEYS = {"label", "text", "figures"}
SUBPART_KEYS = {"text", "figures"}
FIGURE_KEYS = {"kind", "latex", "path", "description", "exception_reason"}

# A choice string whose meaningful content is a TikZ drawing, used by the v2 -> v3
# converter. The drawing may carry a preamble such as ``\tdplotsetmaincoords``
# before ``\begin{tikzpicture}``.
_TIKZ_BEGIN = r"\begin{tikzpicture}"
_TIKZ_END = r"\end{tikzpicture}"


def _extract_choice_tikz(text: str) -> str | None:
    """Return the TikZ body of a choice that is entirely a drawing, else ``None``.

    The choice is wrapped in ``$...$`` and may embed a preamble command before the
    environment. Prose choices (including inline math with a drawing) return
    ``None`` so they are left untouched.
    """

    stripped = text.strip()
    if stripped.startswith("$") and stripped.endswith("$") and stripped.count("$") == 2:
        stripped = stripped[1:-1].strip()
    if _TIKZ_BEGIN not in stripped or _TIKZ_END not in stripped:
        return None
    # Reject if there is prose outside the drawing: only the drawing plus a
    # preamble command may remain.
    end = stripped.rindex(_TIKZ_END) + len(_TIKZ_END)
    if stripped[end:].strip():
        return None
    return stripped


def _require_keys(value: Mapping[str, Any], allowed: set[str], required: set[str], context: str) -> None:
    if not isinstance(value, Mapping):
        fail(f"{context} must be an object")
    missing = sorted(required - set(value))
    if missing:
        fail(f"{context} is missing fields: {', '.join(missing)}")
    extra = sorted(set(value) - allowed)
    if extra:
        fail(f"{context} has unsupported fields: {', '.join(extra)}")


@dataclass(frozen=True)
class Figure:
    """One figure: an embedded TikZ drawing or an approved asset."""

    kind: str
    latex: str | None = None
    path: str | None = None
    description: str = ""
    exception_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "latex": self.latex,
            "path": self.path,
            "description": self.description,
            "exception_reason": self.exception_reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], context: str) -> "Figure":
        validated = _validate_figure_v2(dict(value), context, allow_asset_exception=True)
        return cls(
            kind=validated["kind"],
            latex=validated["latex"],
            path=validated["path"],
            description=validated["description"],
            exception_reason=validated["exception_reason"],
        )


@dataclass(frozen=True)
class Block:
    """A run of inline TeX optionally followed by figures.

    Used for the stem, for each choice and for each subpart so the renderer has a
    single code path.
    """

    text: str = ""
    figures: tuple[Figure, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"text": self.text}
        if self.figures:
            payload["figures"] = [figure.to_dict() for figure in self.figures]
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], context: str) -> "Block":
        _require_keys(value, BLOCK_KEYS, {"text"}, context)
        text = _validate_inline_tex(value.get("text", ""), f"{context}.text") if str(value.get("text", "")).strip() else ""
        figures_raw = value.get("figures", [])
        if not isinstance(figures_raw, list):
            fail(f"{context}.figures must be an array")
        figures = tuple(Figure.from_dict(item, f"{context}.figures[{index}]") for index, item in enumerate(figures_raw))
        return cls(text=text, figures=figures)

    def is_empty(self) -> bool:
        return not self.text.strip() and not self.figures


@dataclass(frozen=True)
class Choice:
    """One labelled multiple-choice option."""

    label: str
    text: str = ""
    figures: tuple[Figure, ...] = ()

    @property
    def block(self) -> Block:
        return Block(text=self.text, figures=self.figures)

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "text": self.text, "figures": [figure.to_dict() for figure in self.figures]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], context: str) -> "Choice":
        _require_keys(value, CHOICE_KEYS, {"text"}, context)
        label = str(value.get("label") or "").strip().upper()
        if label not in CHOICE_LABELS:
            fail(f"{context}.label must be one of {', '.join(CHOICE_LABELS)}")
        text = value.get("text", "")
        text = _validate_inline_tex(text, f"{context}.text") if str(text).strip() else ""
        figures_raw = value.get("figures", [])
        if not isinstance(figures_raw, list):
            fail(f"{context}.figures must be an array")
        figures = tuple(Figure.from_dict(item, f"{context}.figures[{index}]") for index, item in enumerate(figures_raw))
        return cls(label=label, text=text, figures=figures)

@dataclass(frozen=True)
class Question:
    """One exam question in schema 3.0."""

    number: int
    section: str
    points: float | None
    stem: Block
    choices: tuple[Choice, ...] = ()
    subparts: tuple[Block, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "number": self.number,
            "section": self.section,
            "points": self.points,
            "stem": self.stem.to_dict(),
        }
        if self.choices:
            payload["choices"] = [choice.to_dict() for choice in self.choices]
        if self.subparts:
            payload["subparts"] = [subpart.to_dict() for subpart in self.subparts]
        return payload

    def to_summary(self) -> dict[str, Any]:
        """Return a compact projection for list and search views."""

        return {
            "number": self.number,
            "section": self.section,
            "points": self.points,
            "has_choices": bool(self.choices),
            "has_subparts": bool(self.subparts),
            "figure_count": len(self.stem.figures) + sum(len(choice.figures) for choice in self.choices) + sum(len(part.figures) for part in self.subparts),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], context: str) -> "Question":
        allowed = {"number", "section", "points", "stem", "choices", "subparts"}
        _require_keys(value, allowed, {"number", "section", "points", "stem"}, context)
        number = value["number"]
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            fail(f"{context}.number must be a positive integer")
        section = value["section"]
        if section not in SECTIONS:
            fail(f"{context}.section must be one of {', '.join(SECTIONS)}")
        points = value["points"]
        if points is not None and (isinstance(points, bool) or not isinstance(points, (int, float)) or points < 0):
            fail(f"{context}.points must be a non-negative number or null")
        stem = Block.from_dict(value["stem"], f"{context}.stem")
        if stem.is_empty():
            fail(f"{context}.stem must contain text or a figure")

        choices_raw = value.get("choices", [])
        if not isinstance(choices_raw, list):
            fail(f"{context}.choices must be an array")
        choices = tuple(Choice.from_dict(item, f"{context}.choices[{index}]") for index, item in enumerate(choices_raw))
        if section == "choice":
            if len(choices) != 4:
                fail(f"{context}.choice requires exactly four options")
            labels = [choice.label for choice in choices]
            if labels != list(CHOICE_LABELS):
                fail(f"{context}.choice labels must be A, B, C, D in order")
        elif choices:
            fail(f"{context} non-choice questions must not carry choices")

        subparts_raw = value.get("subparts", [])
        if not isinstance(subparts_raw, list):
            fail(f"{context}.subparts must be an array")
        subparts = tuple(Block.from_dict(item, f"{context}.subparts[{index}]") for index, item in enumerate(subparts_raw))
        return cls(number=number, section=section, points=points, stem=stem, choices=choices, subparts=subparts)


def validate_questions(value: Any, context: str) -> list[Question]:
    """Validate a full question array and return it sorted by number."""

    if not isinstance(value, list) or not value:
        fail(f"{context} must be a non-empty question array")
    questions: list[Question] = []
    seen: set[int] = set()
    for index, raw in enumerate(value):
        question = Question.from_dict(raw, f"{context}[{index}]") if isinstance(raw, Mapping) else None
        if question is None:
            fail(f"{context}[{index}] must be an object")
        if question.number in seen:
            fail(f"{context}[{index}].number {question.number} is duplicated")
        seen.add(question.number)
        questions.append(question)
    return sorted(questions, key=lambda item: item.number)


def convert_v2_question(value: Mapping[str, Any]) -> dict[str, Any]:
    """Convert one schema-2.0 question dict into a schema-3.0 question dict.

    Graphic choices that embedded a ``tikzpicture`` string are lifted into a
    proper :class:`Figure` on the choice. Stem figures move into ``stem.figures``.
    """

    number = value.get("number")
    section = value.get("section")
    points = value.get("points")
    stem_figures: list[dict[str, Any]] = []
    for figure in value.get("figures") or []:
        if isinstance(figure, Mapping):
            stem_figures.append(dict(figure))

    choices: list[dict[str, Any]] = []
    for index, raw in enumerate(value.get("choices") or []):
        label = CHOICE_LABELS[index] if index < len(CHOICE_LABELS) else str(index + 1)
        text = str(raw)
        figures: list[dict[str, Any]] = []
        tikz = _extract_choice_tikz(text)
        if tikz is not None:
            figures.append(
                {
                    "kind": "tikz",
                    "latex": tikz,
                    "path": None,
                    "description": "选择题图形选项",
                    "exception_reason": None,
                }
            )
            text = ""
        choices.append({"label": label, "text": text, "figures": figures})

    subparts: list[dict[str, Any]] = []
    for raw in value.get("subparts") or []:
        if isinstance(raw, Mapping):
            subparts.append({"text": str(raw.get("latex", "")), "figures": []})

    payload: dict[str, Any] = {
        "number": number,
        "section": section,
        "points": points,
        "stem": {"text": str(value.get("latex", "")), "figures": stem_figures},
    }
    if choices:
        payload["choices"] = choices
    if subparts:
        payload["subparts"] = subparts
    return payload


def has_schema_v3(value: Mapping[str, Any]) -> bool:
    """Return whether a raw question dict already uses the 3.0 block shape."""

    return isinstance(value.get("stem"), Mapping) and "latex" not in value
