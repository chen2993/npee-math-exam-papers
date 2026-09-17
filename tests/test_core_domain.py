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

def test_product_spacings_are_a_subset_of_the_accepted_ones() -> None:
    """The shipping product line is smaller than what the schema accepts.

    ``spaced`` (宽松版) is retired but must keep validating, because
    composition packages written before the change still name it. Keeping
    the two sets distinct is what lets a payload read while the UI offers
    only the modes that are actually compiled.
    """

    assert set(domain.PRODUCT_SPACINGS) < set(domain.SPACINGS)
    assert "spaced" in domain.SPACINGS
    assert "spaced" not in domain.PRODUCT_SPACINGS

def test_print_spacing_is_labelled_like_a_deliverable() -> None:
    """It reads 打印版 rather than being tied to one paper size.

    The mode is layout-agnostic (A3 already floors at four logical pages),
    so a label naming A4 would misdescribe what it produces on A3.
    """

    assert domain.SPACING_LABELS["a4-blank"] == "打印版"

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
