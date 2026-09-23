"""The golden snapshot must match exactly.

Any behavioural change to inline-TeX repair or question rendering shows up here
as a diff, so refactors that only move code are provably safe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.golden import capture

GOLDEN_PATH = Path(__file__).parent / "golden" / "rendering.json"


def test_rendering_matches_golden_snapshot() -> None:
    expected = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(capture(), ensure_ascii=False))
    assert actual == expected, "generated TeX changed; review the diff and update the snapshot deliberately"


def test_snapshot_covers_repairs() -> None:
    """Guard against a snapshot that no longer exercises the repair rules."""

    snapshot = capture()
    joined = "\n".join(snapshot["inline"])
    for marker in ("\\hline", "\\vdots", "\\begin{cases}", "\\begin{vmatrix}", "m/s"):
        assert marker in joined or marker in snapshot["body"], f"snapshot no longer covers {marker!r}"


def test_snapshot_covers_score_label_and_circled_sequence() -> None:
    """The content normalizations must stay visible in the snapshot."""

    body = capture()["body"]
    # A stored score label is stripped, so the class label is the only one printed.
    assert "（本题满分" not in body
    assert body.count("\\begin{ExamSolutionQuestion}[id=p001-q20]{10}") == 1
    # A stored subpart ordinal is stripped; the cross reference is preserved.
    assert "\\ExamSubpart{p001-q20-s1}求 " in body
    assert "\\ExamSubpart{p001-q20-s2}在第（I）问的基础上" in body
    # Math-led proposition heads become statements; alignment markers stay inline.
    assert "\\ExamStatementMarker{1}$x_2\\ln x_2>x_1\\ln x_1$" in body
    assert "\\begin{array}{ll}\\ExamCircledNumber{1}" in body
