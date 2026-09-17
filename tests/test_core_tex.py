"""Inline-TeX validation rules shared by every layer."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.tex import (
    fraction_position_errors,
    fraction_positions,
    fraction_size_corrections,
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


def test_frac_in_body_is_reported_not_rejected() -> None:
    """A mis-sized fraction is a data-quality finding, not a parse error.

    The store re-validates every record on read, so rejecting ``\frac`` here
    would stop legacy papers from loading at all. The renderer normalises the size
    and the audit reports it; see :func:`fraction_position_errors`.
    """

    validate_inline_tex(r"$\frac{1}{2}$", "field")
    assert fraction_position_errors(r"$\frac{1}{2}$")
    assert not fraction_position_errors(r"$\dfrac{1}{2}$")


def test_dfrac_accepted() -> None:
    validate_inline_tex(r"$\dfrac{1}{2}$", "field")


def test_a_fraction_size_must_match_its_position() -> None:
    r"""A fraction is sized by the style TeX sets it in.

    Both a script slot and a fraction's own numerator/denominator are already one
    level down, so ``\dfrac`` there overflows the line; in body text ``\frac``
    looks shrunken beside display maths.
    """

    # Script positions: \frac is correct, \dfrac/\tfrac are too large.
    assert not fraction_position_errors(r"$x^{\frac{1}{2}}$")
    assert not fraction_position_errors(r"$\int_0^{\frac{\pi}{2}}f$")
    assert fraction_position_errors(r"$x^{\dfrac{1}{2}}$")
    assert fraction_position_errors(r"$\int_0^{\dfrac{\pi}{2}}f$")
    # Body position: \dfrac is correct, \frac is not.
    assert not fraction_position_errors(r"$\dfrac{a}{b}$")
    assert fraction_position_errors(r"$\frac{a}{b}$")
    # A fraction argument is a reduced style too -- and a fraction takes *two*
    # arguments, so the denominator must be classified like the numerator. That
    # makes `\dfrac{a}{\frac{b}{c}}` correct as written (display outside,
    # script inside) while an inner `\dfrac` overflows.
    assert not fraction_position_errors(r"$\dfrac{a}{\frac{b}{c}}$")
    assert fraction_position_errors(r"$\dfrac{a}{\dfrac{b}{c}}$")
    assert fraction_position_errors(r"$\dfrac{\arctan\dfrac{1}{x}}{\sec x}$")
    assert not fraction_position_errors(r"$\dfrac{\arctan\frac{1}{x}}{\sec x}$")


def test_fraction_positions_classifies_every_nesting() -> None:
    """The position of each fraction, including nested ones, is reported."""

    assert [p for _, p, _ in fraction_positions(r"$\dfrac{a}{b}$")] == ["body"]
    assert [p for _, p, _ in fraction_positions(r"$x^{\dfrac{a}{b}}$")] == ["script"]
    assert [p for _, p, _ in fraction_positions(r"$\dfrac{a}{\frac{b}{c}}$")] == ["body", "nested"]
    assert [p for _, p, _ in fraction_positions(r"$\dfrac{\dfrac{a}{b}}{\dfrac{c}{d}}$")] == ["body", "nested", "nested"]


def test_fraction_size_corrections_are_bidirectional() -> None:
    """The shared helper both shrinks and grows, and is a no-op when correct."""

    assert fraction_size_corrections(r"$\dfrac{a}{b}$") == {}
    assert fraction_size_corrections(r"$\frac{a}{b}$") == {1: "dfrac"}
    assert fraction_size_corrections(r"$x^{\dfrac{a}{b}}$") == {4: "frac"}
    assert fraction_size_corrections(r"$x^{\frac{a}{b}}$") == {}


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
