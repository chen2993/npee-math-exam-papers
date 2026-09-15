"""The rendering subpackage: paths, text, inline-TeX repair and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from npee_math_papers.service.rendering.errors import CompositionError, fail
from npee_math_papers.service.rendering.inline_tex import (
    repair_alignment_rows,
    repair_cases_rows,
    repair_integral_limits,
    validate_inline_tex,
)
from npee_math_papers.service.rendering.paths import (
    ROOT,
    package_path,
    package_tex_path,
    relative_tex_path,
    repository_path,
)
from npee_math_papers.service.rendering.text import nonempty_string, require_keys, tex_literal
from npee_math_papers.service.rendering.validation import validate_questions


# --- errors ----------------------------------------------------------------


def test_fail_raises_composition_error() -> None:
    with pytest.raises(CompositionError):
        fail("boom")


def test_composition_error_is_valueerror() -> None:
    assert issubclass(CompositionError, ValueError)


# --- paths -----------------------------------------------------------------


def test_repository_path_rejects_parent_traversal() -> None:
    with pytest.raises(CompositionError):
        repository_path("../secrets", "field")


def test_repository_path_resolves_inside_repo() -> None:
    resolved = repository_path("build/x", "field")
    assert resolved.is_relative_to(ROOT)


def test_package_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(CompositionError):
        package_path("../outside", tmp_path, "field")


def test_package_path_rejects_backslash(tmp_path: Path) -> None:
    with pytest.raises(CompositionError):
        package_path("a\\b", tmp_path, "field")


def test_package_tex_path_requires_tex_suffix(tmp_path: Path) -> None:
    (tmp_path / "cover.txt").write_text("x", encoding="utf-8")
    with pytest.raises(CompositionError):
        package_tex_path("cover.txt", tmp_path, "field")


def test_package_tex_path_accepts_tex(tmp_path: Path) -> None:
    (tmp_path / "cover.tex").write_text("x", encoding="utf-8")
    assert package_tex_path("cover.tex", tmp_path, "field").name == "cover.tex"


def test_relative_tex_path_is_posix() -> None:
    assert "\\" not in relative_tex_path(ROOT / "build" / "x")


# --- text ------------------------------------------------------------------


def test_nonempty_string_rejects_blank_and_multiline() -> None:
    with pytest.raises(CompositionError):
        nonempty_string("   ", "field")
    with pytest.raises(CompositionError):
        nonempty_string("a\nb", "field")
    assert nonempty_string(" a ", "field") == " a "


def test_tex_literal_escapes_inline_metadata() -> None:
    assert tex_literal("50% & up_cases", "field") == r"50\% \& up\_cases"


def test_require_keys_detects_missing_and_extra() -> None:
    with pytest.raises(CompositionError):
        require_keys({"a": 1}, {"a", "b"}, "field")
    with pytest.raises(CompositionError):
        require_keys({"a": 1, "c": 2}, {"a"}, "field")
    require_keys({"a": 1}, {"a"}, "field")


# --- inline-TeX repair -----------------------------------------------------


def test_row_separator_before_command_is_preserved() -> None:
    text = r"$\begin{array}{c}X&2\\\hline P\end{array}$"
    assert repair_alignment_rows(text) == text


def test_lost_backslash_before_inline_command_is_restored() -> None:
    assert validate_inline_tex(r"$\begin{pmatrix}\\lambda&0\end{pmatrix}$", "f") == (
        r"$\begin{pmatrix}\lambda&0\end{pmatrix}$"
    )


def test_builder_preserves_both_hline_spellings() -> None:
    """The builder never rewrites a row-level command.

    A missing row separator (``\\hline``) is a *data* defect fixed by
    ``maintenance.fix_tex``; the renderer must not guess, because the two
    spellings mean different things (``\\ `` row separator vs ``\\`` row
    separator plus command). It passes both through untouched.
    """

    broken = r"$\begin{array}{c}X&2\\hline P\end{array}$"
    correct = r"$\begin{array}{c}X&2\\\hline P\end{array}$"
    assert validate_inline_tex(broken, "f") == broken
    assert validate_inline_tex(correct, "f") == correct


def test_cases_row_separator_is_restored_from_comma() -> None:
    text = r"$\begin{cases}0,&x<0,\dfrac{1}{2},&x>0\end{cases}$"
    repaired = repair_cases_rows(text, "field")
    assert r"\\\dfrac{1}{2}" in repaired


def test_valid_inline_tex_is_unchanged() -> None:
    text = r"设 $f(x)=\dfrac{1}{2}$，求 $f'(1)$。"
    assert validate_inline_tex(text, "f") == text


# --- domain-integral limits ------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        r"$\int_L f$",
        r"$\int_{L} f$",
        r"$\int_{L_1} f$",
        r"$\int_{\Gamma} g$",
        r"$I=\int_C P\,\mathrm{d}x$",
    ],
)
def test_a_region_label_moves_below_the_integral(text: str) -> None:
    r"""A domain subscript reads as "the integral over L", so it sits below.

    The reference papers put a bound at the lower right only for a *numeric*
    range; an examination paper sets the region under the sign. This is the one
    placement the class leaves to the source, because ``\int`` is the only
    operator it does not force (see the ``operators/int-limits`` switch).
    """

    repaired = validate_inline_tex(text, "f")
    assert r"\limits" in repaired


@pytest.mark.parametrize(
    "text",
    [
        r"$\int_0^1 f$",
        r"$\int_a^b f$",
        r"$\int_{-\infty}^{+\infty} f$",
        r"$\int x\,\mathrm{d}x$",
        r"$F(x)=\int_a^x f(t)\,\mathrm{d}t$",
    ],
)
def test_a_numeric_bound_keeps_its_side_position(text: str) -> None:
    """Numeric bounds stay at the lower right, as the reference papers set them.

    Keeping them there is also what stops an integral nested in a fraction or a
    matrix cell from growing tall.
    """

    assert validate_inline_tex(text, "f") == text


def test_the_region_rule_is_idempotent() -> None:
    once = repair_integral_limits(r"$\int_L f$")
    assert repair_integral_limits(once) == once


@pytest.mark.parametrize("text", [r"$\oint_{\Gamma} h$", r"$\iint_D f$", r"$\iiint_\Omega g$"])
def test_the_class_owns_the_limits_of_the_other_operators(text: str) -> None:
    r"""The class forces ``\limits`` on every operator except ``\int``.

    A generated source therefore must not carry its own ``\limits`` for these:
    the repair layer strips it so a record cannot end up with a doubled
    ``\limits\limits`` once the class wrapper is applied. The region label has to
    survive that stripping.
    """

    repaired = validate_inline_tex(text, "f")
    assert r"\limits" not in repaired
    assert "_" in repaired


# --- render-model validation ----------------------------------------------


def _render_question() -> dict:
    return {
        "number": 1,
        "section": "choice",
        "points": 5,
        "latex": "题干",
        "choices": ["$0$", "$1$", "$2$", "$3$"],
        "subparts": [],
        "figures": [],
    }


def test_validate_questions_accepts_render_model() -> None:
    [question] = validate_questions([_render_question()], "ctx")
    assert question["number"] == 1


def test_validate_questions_rejects_unknown_key() -> None:
    bad = _render_question()
    bad["extra"] = 1
    with pytest.raises(CompositionError):
        validate_questions([bad], "ctx")


def test_validate_questions_sorts_by_number() -> None:
    a = _render_question()
    b = _render_question()
    b["number"] = 2
    ordered = validate_questions([b, a], "ctx")
    assert [q["number"] for q in ordered] == [1, 2]
