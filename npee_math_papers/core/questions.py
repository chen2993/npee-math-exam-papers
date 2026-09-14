"""Question and figure validation, plus fragment merging.

Publishing (``import-paper-extraction.py``) and rendering
(``build-composition.py``) previously carried separate copies of these rules.
They now share one implementation so a question accepted at publish time is
accepted at render time, and a rejection message is identical everywhere.

The rules here are intentionally strict but structural: they enforce the record
contract, not editorial quality. Editorial review stays in the human visual-QA
gate described in ``agent/contracts/AGENT.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from npee_math_papers.core.domain import ASSET_EXTENSIONS, SECTIONS, SUBJECTS
from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.tex import fail, nonempty_string, validate_inline_tex, validate_tikz

QUESTION_KEYS = {"number", "section", "points", "latex", "choices", "subparts", "figures"}
FIGURE_KEYS = {"kind", "latex", "path", "description", "exception_reason"}


def require_exact_keys(value: Mapping[str, Any], required: set[str], context: str) -> None:
    """Fail unless ``value`` has exactly ``required`` keys."""

    names = set(value)
    missing = sorted(required - names)
    extra = sorted(names - required)
    if missing:
        fail(f"{context} is missing fields: {', '.join(missing)}")
    if extra:
        fail(f"{context} has unsupported fields: {', '.join(extra)}")


def validate_repo_relative(path: Any, context: str) -> str:
    """Validate a repository-relative POSIX asset path."""

    if not isinstance(path, str):
        fail(f"{context} must be a repository-relative path string")
    if "\\" in path:
        fail(f"{context} must use '/' separators")
    if not path or path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")):
        fail(f"{context} must be repository-relative without '.', '..' or repeated separators")
    if len(path) > 1 and path[1] == ":":
        fail(f"{context} must be repository-relative")
    return path


def validate_figure(
    figure: Any,
    context: str,
    *,
    allow_asset_exception: bool = False,
    asset_base: Path | None = None,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Validate and return one normalized figure object.

    ``kind: tikz`` figures must embed a ``tikzpicture`` and carry no path or
    exception reason. ``kind: asset`` figures require a repository-relative path
    with an approved extension and a concrete exception reason; they are rejected
    unless ``allow_asset_exception`` is set, which only the reviewer may enable.
    """

    if not isinstance(figure, dict):
        fail(f"{context} must be an object")
    require_exact_keys(figure, FIGURE_KEYS, context)
    kind = figure["kind"]
    if kind not in {"tikz", "asset"}:
        fail(f"{context}.kind must be 'tikz' or 'asset'")
    description = nonempty_string(figure["description"], f"{context}.description")
    latex = figure["latex"]
    path = figure["path"]
    reason = figure["exception_reason"]
    if kind == "tikz":
        if path is not None:
            fail(f"{context}.path must be null for TikZ figures")
        if reason is not None:
            fail(f"{context}.exception_reason must be null for TikZ figures")
        latex = validate_tikz(latex, f"{context}.latex")
    else:
        if not isinstance(path, str) or not path.strip():
            fail(f"{context}.path is required for asset figures")
        if not isinstance(reason, str) or not reason.strip():
            fail(f"{context}.exception_reason is required for non-TikZ figures")
        if latex is not None:
            fail(f"{context}.latex must be null for asset figures")
        path = validate_repo_relative(path, f"{context}.path")
        extension = Path(path).suffix.lower().lstrip(".")
        if extension not in ASSET_EXTENSIONS:
            fail(f"{context}.path must end in png, jpg, jpeg, svg or pdf")
        if asset_base is not None:
            candidates = [(asset_base / Path(path)).resolve()]
            if repository_root is not None:
                repository_candidate = (repository_root / Path(path)).resolve()
                if repository_candidate not in candidates:
                    candidates.append(repository_candidate)
            if not any(candidate.is_file() for candidate in candidates):
                fail(f"{context}.path does not exist relative to the extraction input or repository: {path!r}")
        if not allow_asset_exception:
            fail(f"{context} is a non-TikZ asset exception; rerun with --allow-asset-exception after human review")
    return {
        "kind": kind,
        "latex": latex,
        "path": path,
        "description": description,
        "exception_reason": reason,
    }


def validate_question(
    value: Any,
    context: str,
    *,
    allow_asset_exception: bool = False,
    asset_base: Path | None = None,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    """Validate and return one normalized question object."""

    if not isinstance(value, dict):
        fail(f"{context} must be an object")
    require_exact_keys(value, QUESTION_KEYS, context)
    number = value["number"]
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        fail(f"{context}.number must be a positive integer")
    section = value["section"]
    if section not in SECTIONS:
        fail(f"{context}.section is invalid")
    points = value["points"]
    if points is not None and (isinstance(points, bool) or not isinstance(points, (int, float)) or points < 0):
        fail(f"{context}.points must be a non-negative number or null")
    latex = validate_inline_tex(value["latex"], f"{context}.latex")
    choices = value["choices"]
    if not isinstance(choices, list) or len(choices) > 4 or any(not isinstance(item, str) or not item.strip() for item in choices):
        fail(f"{context}.choices must be an array of at most four non-empty strings")
    clean_choices = [validate_inline_tex(item, f"{context}.choices[{i}]") for i, item in enumerate(choices)]
    if section == "choice" and len(clean_choices) != 4:
        fail(f"{context}.choice requires exactly four options")
    if section != "choice" and clean_choices:
        fail(f"{context} non-choice questions must have an empty choices array")
    subparts = value["subparts"]
    if not isinstance(subparts, list):
        fail(f"{context}.subparts must be an array")
    clean_subparts: list[dict[str, str]] = []
    for part_index, part in enumerate(subparts):
        part_context = f"{context}.subparts[{part_index}]"
        if not isinstance(part, dict):
            fail(f"{part_context} must be an object")
        require_exact_keys(part, {"latex"}, part_context)
        clean_subparts.append({"latex": validate_inline_tex(part["latex"], f"{part_context}.latex")})
    figures = value["figures"]
    if not isinstance(figures, list):
        fail(f"{context}.figures must be an array")
    clean_figures = [
        validate_figure(
            item,
            f"{context}.figures[{i}]",
            allow_asset_exception=allow_asset_exception,
            asset_base=asset_base,
            repository_root=repository_root,
        )
        for i, item in enumerate(figures)
    ]
    return {
        "number": number,
        "section": section,
        "points": points,
        "latex": latex,
        "choices": clean_choices,
        "subparts": clean_subparts,
        "figures": clean_figures,
    }


def validate_questions(
    value: Any,
    field: str,
    *,
    allow_asset_exception: bool = False,
    asset_base: Path | None = None,
    repository_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Validate a full question array and return it sorted by question number."""

    if not isinstance(value, list) or not value:
        fail(f"{field} must be a non-empty question array")
    clean: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, raw in enumerate(value):
        question = validate_question(
            raw,
            f"{field}[{index}]",
            allow_asset_exception=allow_asset_exception,
            asset_base=asset_base,
            repository_root=repository_root,
        )
        if question["number"] in seen:
            fail(f"{field}[{index}].number {question['number']} is duplicated")
        seen.add(question["number"])
        clean.append(question)
    return sorted(clean, key=lambda item: item["number"])


def validate_paper_meta(value: Any, context: str = "paper") -> dict[str, Any]:
    """Validate and return the ``paper`` metadata object."""

    if not isinstance(value, dict):
        fail(f"{context} must be an object")
    require_exact_keys(value, {"year", "subject", "series_key", "paper_no"}, context)
    year = value["year"]
    if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 2200:
        fail(f"{context}.year must be an integer from 1900 to 2200")
    subject = value["subject"]
    if subject not in SUBJECTS:
        fail(f"{context}.subject must be math1, math2 or math3")
    series_key = value["series_key"]
    if not isinstance(series_key, str) or not series_key:
        fail(f"{context}.series_key must be a non-empty lowercase ASCII ID")
    import re

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", series_key):
        fail(f"{context}.series_key must be a lowercase ASCII ID")
    paper_no = value["paper_no"]
    if isinstance(paper_no, bool) or not isinstance(paper_no, int) or paper_no < 1:
        fail(f"{context}.paper_no must be a positive integer")
    return {"year": year, "subject": subject, "series_key": series_key, "paper_no": paper_no}


def merge_question_fragments(
    documents: Iterable[dict[str, Any]],
    *,
    allow_asset_exception: bool = False,
    asset_base: Path | None = None,
    repository_root: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge one or more ``paper.json`` / JSONL fragments into a single record.

    This supports cross-page questions split across fragments. Fragments must
    agree on paper metadata; repeated question numbers are merged field by field
    and conflicting sections, points or choices fail loudly instead of silently
    picking one side.
    """

    metadata: dict[str, Any] | None = None
    merged: dict[int, dict[str, Any]] = {}
    for doc_index, document in enumerate(documents):
        context = f"document[{doc_index}]"
        if not isinstance(document, dict):
            fail(f"{context} must be an object")
        require_exact_keys(document, {"schema_version", "paper", "questions"}, context)
        if document["schema_version"] != "2.0":
            fail(f"{context}.schema_version must be '2.0'")
        paper = validate_paper_meta(document["paper"], f"{context}.paper")
        if metadata is None:
            metadata = paper
        elif paper != metadata:
            fail("All JSONL fragments must have identical paper metadata")
        questions = document["questions"]
        if not isinstance(questions, list) or not questions:
            fail(f"{context}.questions must be a non-empty array")
        for index, raw_question in enumerate(questions):
            question = validate_question(
                raw_question,
                f"{context}.questions[{index}]",
                allow_asset_exception=allow_asset_exception,
                asset_base=asset_base,
                repository_root=repository_root,
            )
            number = question["number"]
            if number not in merged:
                merged[number] = question
                continue
            current = merged[number]
            if current["section"] != question["section"]:
                fail(f"Question {number} has conflicting sections across fragments")
            if current["points"] is not None and question["points"] is not None and current["points"] != question["points"]:
                fail(f"Question {number} has conflicting points across fragments")
            if question["points"] is not None:
                current["points"] = question["points"]
            if question["latex"] != current["latex"]:
                current["latex"] = current["latex"] + "\n" + question["latex"]
            if question["choices"]:
                if current["choices"] and current["choices"] != question["choices"]:
                    fail(f"Question {number} has conflicting choices across fragments")
                current["choices"] = question["choices"]
            for field in ("subparts", "figures"):
                for item in question[field]:
                    if item not in current[field]:
                        current[field].append(item)
    if metadata is None:
        fail("No paper metadata found")
    questions = [merged[number] for number in sorted(merged)]
    return metadata, questions
