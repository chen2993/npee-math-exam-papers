"""Domain vocabulary is defined once and used consistently."""

from __future__ import annotations

from npee_math_papers.core import domain


def test_subjects_are_ordered_and_labelled() -> None:
    assert domain.SUBJECTS == ("math1", "math2", "math3")
    assert set(domain.SUBJECT_LABELS) == set(domain.SUBJECTS)
    assert set(domain.SUBJECT_CODES) == set(domain.SUBJECTS)


def test_sections_have_labels() -> None:
    assert set(domain.SECTION_LABELS) == set(domain.SECTIONS)


def test_spacing_labels_cover_spacings() -> None:
    assert set(domain.SPACING_LABELS) == set(domain.SPACINGS)

def test_spacing_covers_only_the_two_question_rhythms() -> None:
    """间距只描述解答题怎么排，因此只有 compact / spaced 两个值。

    ``print`` / ``a4-blank`` 曾经把「紧凑 + 留白」挤在同一个 token 里；拆开之后它们
    只作为**历史存储值**被接受（{@link split_spacing_axes} 把旧包折算成
    compact + 留白），不再出现在间距词表里。
    """

    assert domain.SPACINGS == ("compact", "spaced")
    assert set(domain.PRODUCT_SPACINGS) == set(domain.SPACINGS)
    assert "print" in domain.STORED_SPACINGS
    assert "a4-blank" in domain.STORED_SPACINGS
    assert "print" not in domain.SPACINGS
    assert "a4-blank" not in domain.SPACINGS


def test_legacy_print_spacings_convert_to_compact_with_blank_space() -> None:
    """旧组卷包的 ``print`` / ``a4-blank`` 等价于「紧凑 + 留白」。"""

    assert domain.split_spacing_axes("print") == ("compact", True)
    assert domain.split_spacing_axes("a4-blank") == ("compact", True)
    # 间距本身不再隐式打开留白：历史包只写间距时不会平白多出空白页。
    assert domain.split_spacing_axes("compact") == ("compact", False)
    assert domain.split_spacing_axes("spaced") == ("spaced", False)
    assert domain.split_spacing_axes("compact", True) == ("compact", True)


def test_default_product_is_compact_with_blank_space() -> None:
    """默认产品沿用「打印版」：紧凑连排 + 留白。"""

    assert domain.DEFAULT_SPACING == "compact"
    assert domain.DEFAULT_PRINT is True
    assert domain.SPACING_LABELS["compact"] == "紧凑版"
    assert domain.SPACING_LABELS["spaced"] == "宽松版"
    assert domain.target_label("compact", True) == "打印版"
    assert domain.target_label("spaced", False) == "宽松版"

def test_no_spacing_is_layout_restricted() -> None:
    """Every accepted spacing works on every stock.

    The print deliverable used to be A4-only; it no longer is, and the
    table that expresses such a rule is now empty. Naming it here keeps the
    assumption explicit instead of leaving it implied by an empty dict.
    """

    assert domain.SPACING_LAYOUT_REQUIREMENTS == {}
    assert set(domain.SPACING_LAYOUT_REQUIREMENTS) <= set(domain.SPACINGS)


def test_is_valid_id_accepts_and_rejects() -> None:
    assert domain.is_valid_id("demo-2024")
    assert domain.is_valid_id("a1")
    assert not domain.is_valid_id("Demo")
    assert not domain.is_valid_id("-leading")
    assert not domain.is_valid_id("has space")
    assert not domain.is_valid_id("")
    assert not domain.is_valid_id(None)
    assert not domain.is_valid_id("x" * 100)


def test_subject_helpers_are_total() -> None:
    assert domain.subject_label("math1") == "数学一"
    assert domain.subject_code("math3") == "303"
    assert domain.subject_label("unknown") == "unknown"
    assert domain.subject_code("unknown") == ""
