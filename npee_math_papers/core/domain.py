"""Domain vocabulary: the single definition of every shared term.

These values (subjects, sections, choice labels, identifier grammar, layout
options) were previously re-declared in more than half a dozen modules, so a
change had to be made in every copy or the layers could silently disagree.
This module is now the only place they are written down; every other module
imports from here.

Nothing in this module depends on the filesystem or on any third-party package.
"""

from __future__ import annotations

import re

# --- subjects --------------------------------------------------------------

#: The three exam subjects, in canonical display order.
SUBJECTS: tuple[str, ...] = ("math1", "math2", "math3")

#: Chinese display name for each subject.
SUBJECT_LABELS: dict[str, str] = {"math1": "数学一", "math2": "数学二", "math3": "数学三"}

#: Official subject code printed on the paper.
SUBJECT_CODES: dict[str, str] = {"math1": "301", "math2": "302", "math3": "303"}

#: A subject placeholder inside a composition that expands to every subject.
SUBJECT_TEMPLATE = "$subject"

def subject_label(subject: str) -> str:
    """Return the Chinese display name for ``subject`` (identity if unknown)."""

    return SUBJECT_LABELS.get(subject, subject)


def subject_code(subject: str) -> str:
    """Return the official code for ``subject`` (empty string if unknown)."""

    return SUBJECT_CODES.get(subject, "")


# --- question sections -----------------------------------------------------

#: Every question section, in canonical order.
SECTIONS: tuple[str, ...] = ("choice", "fill", "solution")

#: Chinese section heading for each section.
SECTION_LABELS: dict[str, str] = {"choice": "选择题", "fill": "填空题", "solution": "解答题"}

#: The four multiple-choice labels, in order.
CHOICE_LABELS: tuple[str, ...] = ("A", "B", "C", "D")


# --- identifiers -----------------------------------------------------------

#: Grammar shared by composition ids, series keys, capture ids and asset ids:
#: lowercase ASCII, digits and hyphens, starting with a letter or digit.
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

#: Longest identifier accepted.
ID_MAX_LENGTH = 64


def is_valid_id(value: object) -> bool:
    """Return whether ``value`` is a well-formed identifier."""

    return isinstance(value, str) and len(value) <= ID_MAX_LENGTH and ID_RE.fullmatch(value) is not None


# --- composition layout ----------------------------------------------------

#: Supported page layouts.
LAYOUTS: tuple[str, ...] = ("a3", "a4")

#: Supported colour themes.
THEMES: tuple[str, ...] = ("print", "cream")

#: Every spacing mode the composition schema accepts.
#:
#: This is the set of *stored* values, not the shipping product line: ``spaced``
#: is retired and no longer offered, but composition packages written before the
#: change still name it and must keep validating.
SPACINGS: tuple[str, ...] = ("compact", "spaced", "a4-blank")

#: The spacing modes that make up the shipping product line, in display order.
#:
#: ``a4-blank`` is the *print deliverable*: a compact natural flow in which every
#: paper is padded to at least four sheets, so a handout always begins on a fresh
#: one. It is deliberately layout-agnostic -- A3 already floors at four logical
#: pages, so there it is exactly ``compact`` -- which is why its label is 打印版
#: rather than anything tied to A4. Its key keeps the historical spelling because
#: that is the value already written into composition files.
PRODUCT_SPACINGS: tuple[str, ...] = ("compact", "a4-blank")

#: Chinese label for each spacing mode; also the `{spacing_label}` filename token.
SPACING_LABELS: dict[str, str] = {"compact": "紧凑版", "spaced": "宽松版", "a4-blank": "打印版"}

#: The spacing mode a new composition compiles with.
#:
#: The product line ships the print deliverable by default, so a caller that
#: does not choose a rhythm gets the one the library is actually produced in.
DEFAULT_SPACING = "a4-blank"

#: Supported solution-flow structures.
SOLUTION_STRUCTURES: tuple[str, ...] = ("pair-first", "natural", "full-page")

#: Spacing modes restricted to one layout, as ``{spacing: layout}``.
#:
#: Currently empty: no spacing mode is layout-restricted. The print deliverable
#: used to be A4-only, but it is now layout-agnostic (A3 already floors at four
#: logical pages). The table stays as the single place to declare such a rule if
#: a future mode needs one, so consumers never hardcode a spacing name.
SPACING_LAYOUT_REQUIREMENTS: dict[str, str] = {}

#: Injection points a composition package may hook.
HOOK_PHASES: tuple[str, ...] = (
    "preamble",
    "before_collection",
    "before_group",
    "after_group",
    "after_collection",
    "before_end_document",
)

# --- capture / sources -----------------------------------------------------

#: Capture lifecycle states.
CAPTURE_STATUSES: tuple[str, ...] = ("prepared", "returned", "reviewed")

#: Asset file extensions accepted for a paper figure.
ASSET_EXTENSIONS: frozenset[str] = frozenset({"png", "jpg", "jpeg", "svg", "pdf"})

# --- paper listing ---------------------------------------------------------

#: Ordering modes accepted by the paper list endpoint and tool.
#:
#: The identifiers are part of the HTTP/MCP contract, so they are declared here
#: once instead of being repeated as string literals across the service and the
#: adapters. ``series`` is the store's natural order and the default.
PAPER_ORDERS: tuple[str, ...] = (
    "series",
    "year-desc",
    "year-asc",
    "questions-desc",
    "questions-asc",
)

#: Ordering used when the caller does not ask for one.
DEFAULT_PAPER_ORDER = "series"

#: Sort key per ordering mode, applied to a paper summary mapping.
#:
#: The first component is the primary key; the remaining ones are stable
#: tie-breakers so the same query always returns the same window.
PAPER_ORDER_KEYS: dict[str, tuple[tuple[str, bool], ...]] = {
    "series": (("series_key", False), ("year", False), ("subject", False), ("paper_no", False)),
    "year-desc": (("year", True), ("series_key", False), ("subject", False), ("paper_no", False)),
    "year-asc": (("year", False), ("series_key", False), ("subject", False), ("paper_no", False)),
    "questions-desc": (("question_count", True), ("series_key", False), ("year", False), ("paper_no", False)),
    "questions-asc": (("question_count", False), ("series_key", False), ("year", False), ("paper_no", False)),
}

def normalize_paper_order(order: str | None) -> str:
    """Return a known ordering mode, falling back to the default.

    Ordering is a presentation choice, so an unknown or stale value (say, from a
    bookmarked URL written by an older release) degrades to the natural order
    instead of failing the request.
    """

    return order if order in PAPER_ORDER_KEYS else DEFAULT_PAPER_ORDER


__all__ = [
    "ASSET_EXTENSIONS",
    "CAPTURE_STATUSES",
    "CHOICE_LABELS",
    "HOOK_PHASES",
    "ID_MAX_LENGTH",
    "ID_RE",
    "LAYOUTS",
    "PAPER_ORDERS",
    "PRODUCT_SPACINGS",
    "PAPER_ORDER_KEYS",
    "SECTION_LABELS",
    "SECTIONS",
    "SOLUTION_STRUCTURES",
    "SPACING_LABELS",
    "SPACING_LAYOUT_REQUIREMENTS",
    "SPACINGS",
    "SUBJECTS",
    "SUBJECT_CODES",
    "SUBJECT_LABELS",
    "SUBJECT_TEMPLATE",
    "THEMES",
    "DEFAULT_PAPER_ORDER",
    "DEFAULT_SPACING",
    "is_valid_id",
    "normalize_paper_order",
    "subject_code",
    "subject_label",
]
