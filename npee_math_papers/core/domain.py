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

#: 间距（spacing）：**只决定解答题怎么排**，与打印无关。
#:
#: ``compact`` = 全卷自然连排；``spaced`` = 解答题独占页面（17–18 共用一页，
#: 之后每题一页），给作答留出书写空间。两种间距共用同一套正文排版（字号、
#: 行高、小题间距都相同），差别只在解答题的版面策略。
SPACINGS: tuple[str, ...] = ("compact", "spaced")

#: 留白（print）：与间距正交的独立开关。
#:
#: 打开后每套卷补足到整页（A4 至少 4 页）、封面后加一张空白页、目录凑成偶数页，
#: 使双面打印时每套卷都从右手页开始。它不改动任何题面排版 —— 打印的核心就是留白。
PRINT_VALUES: tuple[bool, ...] = (True, False)

#: 旧的“打印版”写法：把「紧凑 + 留白」写成单个间距值。历史组卷包仍在用，
#: 读取时归一化为 ``spacing="compact"`` 加 ``print=True``，行为与当年一致。
LEGACY_PRINT_SPACINGS: tuple[str, ...] = ("print", "a4-blank")

#: 存储层可能出现的全部间距值（含仅用于兼容读取的旧写法）。
STORED_SPACINGS: tuple[str, ...] = SPACINGS + LEGACY_PRINT_SPACINGS

#: 产品线提供给使用者的间距取值，按展示顺序。
PRODUCT_SPACINGS: tuple[str, ...] = SPACINGS

#: Chinese label for each spacing mode; also the `{spacing_label}` filename token.
SPACING_LABELS: dict[str, str] = {
    "compact": "紧凑版",
    "spaced": "宽松版",
}

#: 默认间距与默认留白：产品线出的是「紧凑 + 留白」，也就是沿用下来的打印版。
DEFAULT_SPACING = "compact"
DEFAULT_PRINT = True

#: Supported solution-flow structures.
SOLUTION_STRUCTURES: tuple[str, ...] = ("pair-first", "natural", "full-page")

#: 间距限制纸张的规则表，格式 ``{spacing: layout}``。
#:
#: 留白与间距拆开后为空：留白对两种纸张都合法（A3 本身就按 4 个逻辑页起算）。
#: 该表保留为「唯一声明处」，将来若有间距只对某种纸张成立，改这里即可。
SPACING_LAYOUT_REQUIREMENTS: dict[str, str] = {}


def split_spacing_axes(spacing: str, print_flag: bool | None = None) -> tuple[str, bool]:
    """把存储值归一化成 ``(间距, 留白)`` 两个正交的轴。

    旧组卷包把「紧凑 + 留白」写成一个值（``print`` / ``a4-blank``），这里统一折算；
    间距值本身只接受 ``compact`` / ``spaced``，其它值原样返回给调用方报错。

    缺省 ``print_flag`` 视为**不留白**：历史组卷包只写间距，没写留白，不该因此
    多出空白页。新组卷由 ``DEFAULT_PRINT`` 显式写入想用的值。
    """

    if spacing in LEGACY_PRINT_SPACINGS:
        return "compact", True
    return spacing, bool(print_flag)


def target_label(spacing: str, print_flag: bool) -> str:
    """目标版式的中文标签，同时用于产物文件名。"""

    if print_flag:
        return "打印版" if spacing == "compact" else f"{SPACING_LABELS.get(spacing, spacing)}留白"
    return SPACING_LABELS.get(spacing, spacing)

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
    "LEGACY_PRINT_SPACINGS",
    "PAPER_ORDERS",
    "PRINT_VALUES",
    "PRODUCT_SPACINGS",
    "PAPER_ORDER_KEYS",
    "SECTION_LABELS",
    "SECTIONS",
    "SOLUTION_STRUCTURES",
    "SPACING_LABELS",
    "SPACING_LAYOUT_REQUIREMENTS",
    "SPACINGS",
    "STORED_SPACINGS",
    "SUBJECTS",
    "SUBJECT_CODES",
    "SUBJECT_LABELS",
    "SUBJECT_TEMPLATE",
    "THEMES",
    "DEFAULT_PAPER_ORDER",
    "DEFAULT_PRINT",
    "DEFAULT_SPACING",
    "is_valid_id",
    "normalize_paper_order",
    "split_spacing_axes",
    "subject_code",
    "subject_label",
    "target_label",
]
