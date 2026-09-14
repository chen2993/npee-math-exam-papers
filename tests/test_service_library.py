"""Library use cases: browse, read, search and inventory."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ValidationError


def test_stats_counts_papers_and_questions(seeded) -> None:
    stats = seeded.library.stats()
    assert stats["papers"] == 3
    assert stats["bundles"] == 2


def test_list_series_groups_by_series(seeded) -> None:
    series = {item["series_key"]: item for item in seeded.library.list_series()}
    assert series["demo"]["paper_count"] == 2
    assert series["other"]["paper_count"] == 1


def test_list_bundles_filters_by_series(seeded) -> None:
    keys = [bundle["bundle"] for bundle in seeded.library.list_bundles(series_keys=["demo"])]
    assert keys == ["demo-2024-math1"]


def test_list_papers_paginates(seeded) -> None:
    page = seeded.library.list_papers(limit=2)
    assert page["total"] == 3
    assert page["count"] == 2
    rest = seeded.library.list_papers(offset=2, limit=2)
    assert rest["count"] == 1


def test_list_papers_rejects_bad_offset(seeded) -> None:
    with pytest.raises(ValidationError):
        seeded.library.list_papers(offset=-1)


def test_list_papers_searches_display_fields(seeded) -> None:
    """The list search matches the series name, key, year, subject and paper no."""

    assert seeded.library.list_papers(query="demo")["total"] == 2
    assert seeded.library.list_papers(query="other")["total"] == 1
    # Case-insensitive, and matched against the machine series key.
    assert seeded.library.list_papers(query="DEMO")["total"] == 2


def test_list_papers_search_matches_the_subject_label(seeded) -> None:
    """A human types 数学二, not math2, so the label must match too."""

    assert seeded.library.list_papers(query="数学二")["total"] == 1
    assert seeded.library.list_papers(query="math2")["total"] == 1


def test_list_papers_search_narrows_the_total_before_paging(seeded) -> None:
    """`total` describes the filtered set, otherwise the pager would lie."""

    page = seeded.library.list_papers(query="demo", limit=1)
    assert page["total"] == 2
    assert page["count"] == 1
    second = seeded.library.list_papers(query="demo", offset=1, limit=1)
    assert second["count"] == 1
    assert second["papers"][0]["natural_key"] != page["papers"][0]["natural_key"]


def test_list_papers_orders_by_year_and_question_count(seeded) -> None:
    by_year = seeded.library.list_papers(order="year-desc")["papers"]
    assert [paper["year"] for paper in by_year] == [2025, 2024, 2024]

    by_questions = seeded.library.list_papers(order="questions-desc")["papers"]
    counts = [paper["question_count"] for paper in by_questions]
    assert counts == sorted(counts, reverse=True)


def test_list_papers_treats_an_unknown_order_as_the_default(seeded) -> None:
    """A stale bookmark must degrade, not fail the request."""

    default = seeded.library.list_papers()["papers"]
    assert seeded.library.list_papers(order="nonsense")["papers"] == default


def test_get_paper_with_and_without_questions(seeded) -> None:
    full = seeded.library.get_paper("demo", 2024, "math1", 1)
    assert "questions" in full
    summary_only = seeded.library.get_paper("demo", 2024, "math1", 1, with_questions=False)
    assert "questions" not in summary_only
    assert summary_only["natural_key"] == "2024/math1/demo/1"


def test_get_question_returns_paper_context(seeded) -> None:
    result = seeded.library.get_question("demo", 2024, "math1", 1, 1)
    assert result["natural_key"] == "2024/math1/demo/1"
    assert result["question"]["number"] == 1


def test_get_question_missing_raises(seeded) -> None:
    with pytest.raises(ValidationError):
        seeded.library.get_question("demo", 2024, "math1", 1, 99)


def test_search_matches_stem_text(seeded) -> None:
    result = seeded.library.search("设")
    assert result["total"] >= 1


def test_search_respects_series_filter(seeded) -> None:
    demo = seeded.library.search("设", series_keys=["demo"])
    other = seeded.library.search("设", series_keys=["other"])
    assert demo["total"] + other["total"] == seeded.library.search("设")["total"]


def test_search_rejects_empty_query(seeded) -> None:
    with pytest.raises(ValidationError):
        seeded.library.search("   ")


def test_overview_contains_dashboard_sections(seeded) -> None:
    overview = seeded.library.overview()
    assert {"stats", "series", "bundles"} <= set(overview)


def test_resolve_natural_keys_splits_present_absent(seeded) -> None:
    result = seeded.library.resolve_natural_keys(["2024/math1/demo/1", "2024/math1/demo/9", "garbage"])
    assert result["present"] == ["2024/math1/demo/1"]
    assert set(result["absent"]) == {"2024/math1/demo/9", "garbage"}
