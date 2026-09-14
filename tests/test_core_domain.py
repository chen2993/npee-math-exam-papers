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
