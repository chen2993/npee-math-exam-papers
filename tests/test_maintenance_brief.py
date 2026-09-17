"""提取简报生成：结构与派生事实必须可复核。

这份工具的存在意义是让「每个 bundle 的提取事实」不再靠手写，因此测试关注两件事：

1. 简报必须覆盖子代理真正需要的每一节（少一节就会有人漏读边界）；
2. 从题库派生出来的数字（题数、分值、记号计数）必须与题库实际一致——
   简报的价值就在于它是**事实**，如果它自己会漂，那还不如手写。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from npee_math_papers.core.domain import SECTIONS  # noqa: E402
from npee_math_papers.maintenance.extraction_brief import (  # noqa: E402
    DEFAULT_COUNTS,
    DEFAULT_POINTS,
    derive_structure,
    format_points,
    measure_notation,
)
from npee_math_papers.service import NpeeService  # noqa: E402

def _service() -> NpeeService:
    return NpeeService.create()

def test_derive_structure_uses_the_dominant_shape() -> None:
    """个别套卷的分值缺记不得改变结论（题库里确实存在 points=null）。"""

    good = [{"section": "choice", "points": 5}] * 10 + [{"section": "fill", "points": 5}] * 6
    poor = [{"section": "choice", "points": None}] * 10 + [{"section": "fill", "points": None}] * 6
    counts, points, key = derive_structure([
        ("demo", 2024, "math1", 1, good),
        ("demo", 2024, "math1", 2, good),
        ("demo", 2024, "math1", 3, poor),
    ])
    assert counts["choice"] == 10
    assert counts["fill"] == 6
    assert points["choice"] == (5,)
    # The natural key must use the canonical spelling, not a hand-built order.
    assert key == "2024/math1/demo/1"

def test_derive_structure_falls_back_and_says_so() -> None:
    """没有同类对照时退回库级默认，并返回空参照（调用方据此加警告）。"""

    counts, points, key = derive_structure([])
    assert counts == DEFAULT_COUNTS
    assert points == DEFAULT_POINTS
    assert key == ""

def test_format_points_reads_naturally() -> None:
    assert format_points((5,)) == "每题 5 分"
    assert format_points((10, 12)) == "10 / 12 分"

def test_measure_notation_matches_the_store() -> None:
    """记号计数必须来自题库实际，而不是记在代码里的常数。"""

    import re

    rows = measure_notation(_service())
    assert rows, "expected the store to use at least one of the probe tokens"
    assert [count for _, _, count in rows] == sorted((c for _, _, c in rows), reverse=True)

    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / ".npee-math-papers" / "papers").glob("*/*.yaml"))
    )
    for token, _note, count in rows:
        assert len(re.findall(re.escape(token), blob)) == count, token

def test_brief_covers_every_section_a_subagent_needs() -> None:
    """少一节就会有人漏读边界或调用顺序，因此逐节断言。"""

    from npee_math_papers.maintenance.extraction_brief import build

    service = _service()
    bundle = service.library.list_bundles()[0]
    brief = build(service, bundle["series_key"], bundle["year"], bundle["subject"])

    for heading in (
        "## 一、任务边界",
        "## 二、每套卷的结构",
        "## 三、schema 3.0 题目形状",
        "### 排版约定",
        "## 四、执行流程",
        "## 五、校验失败对照",
    ):
        assert heading in brief, heading

    # Boundaries that must never be dropped.
    assert "只来自页面 PNG 的视觉观察" in brief
    assert "禁止" in brief and "OCR" in brief
    assert "replace=false" in brief
    # The schema shape must be shown, not just described.
    assert '"choices"' in brief and '"subparts"' in brief
    for name in SECTIONS:
        assert name in brief
