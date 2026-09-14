"""Paper store: atomic writes, replace semantics, index and release."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ConflictError, NotFoundError, ValidationError
from npee_math_papers.core.store import PaperRecord, PaperStore, bundle_key, parse_bundle_key

from tests.conftest import make_choice_question, make_fill_question


def test_bundle_key_round_trip() -> None:
    key = bundle_key("demo-series", 2024, "math1")
    assert key == "demo-series-2024-math1"
    assert parse_bundle_key(key) == ("demo-series", 2024, "math1")


def test_parse_bundle_key_rejects_bad_subject() -> None:
    with pytest.raises(ValidationError):
        parse_bundle_key("demo-2024-math9")


def test_parse_bundle_key_rejects_non_numeric_year() -> None:
    with pytest.raises(ValidationError):
        parse_bundle_key("demo-year-math1")


def test_write_then_read_round_trips_questions(service) -> None:
    store = service.context.store
    record = PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1), make_fill_question(11)])
    assert store.write_paper(record) == "added"
    loaded = store.read_paper("demo", 2024, "math1", 1)
    assert [q["number"] for q in loaded.questions] == [1, 11]
    # The content hash is stable across a write -> read -> write cycle, so a
    # re-read can never disagree with the release manifest.
    assert store.write_paper(PaperRecord("demo", 2024, "math1", 1, loaded.questions), replace=True)
    assert store.read_paper("demo", 2024, "math1", 1).content_hash == loaded.content_hash


def test_overwrite_requires_replace(service) -> None:
    store = service.context.store
    record = PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1)])
    store.write_paper(record)
    with pytest.raises(ConflictError):
        store.write_paper(record)
    assert store.write_paper(record, replace=True) == "replaced"


def test_read_missing_paper_raises(service) -> None:
    with pytest.raises(NotFoundError):
        service.context.store.read_paper("demo", 2024, "math1", 99)


def test_delete_paper_removes_the_file(service) -> None:
    store = service.context.store
    store.write_paper(PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1)]))
    assert store.delete_paper("demo", 2024, "math1", 1) is True
    assert store.delete_paper("demo", 2024, "math1", 1) is False
    assert store.list_summaries() == []


def test_rebuild_index_and_release_agree_with_disk(service) -> None:
    store = service.context.store
    store.write_paper(PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1)]))
    store.write_paper(PaperRecord("demo", 2024, "math1", 2, [make_choice_question(1)]))
    index = store.rebuild_index()
    release = store.write_release()
    assert index["paper_count"] == 2
    assert release["paper_count"] == 2
    assert set(release["papers"]) == {"2024/math1/demo/1", "2024/math1/demo/2"}


def test_list_summaries_filters(service) -> None:
    store = service.context.store
    store.write_paper(PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1)]))
    store.write_paper(PaperRecord("other", 2025, "math2", 1, [make_choice_question(1)]))
    assert [s["natural_key"] for s in store.list_summaries(series_keys=["demo"])] == ["2024/math1/demo/1"]
    assert [s["natural_key"] for s in store.list_summaries(subjects=["math2"])] == ["2025/math2/other/1"]
    assert [s["natural_key"] for s in store.list_summaries(years=[2024])] == ["2024/math1/demo/1"]


def test_stale_index_is_never_served(service) -> None:
    """A write must make the cached/derived index fall back to disk."""

    store = service.context.store
    store.write_paper(PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1)]))
    store.rebuild_index()
    assert len(store.list_summaries()) == 1
    # A second write through the same store must not be masked by the index.
    store.write_paper(PaperRecord("demo", 2024, "math1", 2, [make_choice_question(1)]))
    assert len(store.list_summaries()) == 2


def test_write_paper_normalizes_and_sorts(service) -> None:
    store = service.context.store
    record = PaperRecord("demo", 2024, "math1", 1, [make_fill_question(11), make_choice_question(1)])
    store.write_paper(record)
    loaded = store.read_paper("demo", 2024, "math1", 1)
    assert [q["number"] for q in loaded.questions] == [1, 11]
    # empty figure arrays are dropped by the storage normalization
    assert "figures" not in loaded.questions[1]["stem"]


def test_store_stats(service) -> None:
    store = service.context.store
    store.write_paper(PaperRecord("demo", 2024, "math1", 1, [make_choice_question(1), make_fill_question(11)]))
    stats = service.context.store.stats()
    assert stats["papers"] == 1
    assert stats["questions"] == 2
    assert stats["bundles"] == 1
