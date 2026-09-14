"""Inline-TeX validation rules shared by every layer."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.tex import (
    cjk_text_in_math,
    validate_inline_tex,
    validate_tikz,
)


@pytest.mark.parametrize(
    "text",
    [
        r"设 $f(x)=\dfrac{1}{2}$。",
        r"求 $\int_0^1 x\,\mathrm{d}x$。",
        r"判断 $x\leq 0$ 时的符号。",
    ],
)
def test_valid_inline_tex_passes(text: str) -> None:
    assert validate_inline_tex(text, "field") == text


def test_block_math_rejected() -> None:
    with pytest.raises(ValidationError, match="block math"):
        validate_inline_tex(r"$$x$$", "field")


def test_frac_rejected() -> None:
    with pytest.raises(ValidationError, match="dfrac"):
        validate_inline_tex(r"$\frac{1}{2}$", "field")


def test_dfrac_accepted() -> None:
    validate_inline_tex(r"$\dfrac{1}{2}$", "field")


def test_pending_marker_rejected() -> None:
    with pytest.raises(ValidationError, match="pending"):
        validate_inline_tex("题干 [待核]", "field")


def test_empty_string_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_inline_tex("   ", "field")


def test_literal_unicode_backslash_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_inline_tex(r"\u005cfrac", "field")


def test_cjk_in_math_outside_text_rejected() -> None:
    with pytest.raises(ValidationError, match="CJK"):
        validate_inline_tex("$中文$", "field")


def test_cjk_inside_text_command_allowed() -> None:
    validate_inline_tex(r"$x>0 \text{时}$", "field")


def test_cjk_text_in_math_reports_fragments() -> None:
    assert cjk_text_in_math("$中文$") == ["中文"]
    assert cjk_text_in_math(r"$x \text{中文}$") == []


def test_validate_tikz_requires_environment() -> None:
    with pytest.raises(ValidationError):
        validate_tikz(r"$\draw (0,0)--(1,1);$", "field")


def test_validate_tikz_accepts_a_drawing() -> None:
    tikz = r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}"
    assert validate_tikz(tikz, "field") == tikz
