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
