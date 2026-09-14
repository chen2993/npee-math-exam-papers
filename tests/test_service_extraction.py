"""Extraction use cases: ingest (schema 2.0 and 3.0) and delete."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ConflictError, ValidationError

from tests.conftest import make_choice_question, make_fill_question


def test_ingest_writes_a_paper_and_rebuilds_index(service) -> None:
    result = service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    assert result["operation"] == "added"
    assert result["natural_key"] == "2024/math1/demo/1"
    assert service.library.stats()["papers"] == 1
    assert (service.context.paths.index / "papers.json").is_file()
    assert service.context.paths.release.is_file()


def test_ingest_requires_explicit_replace(service) -> None:
    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    with pytest.raises(ConflictError):
        service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    replaced = service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(2)], replace=True)
    assert replaced["operation"] == "replaced"


def test_ingest_rejects_invalid_questions_without_writing(service) -> None:
    with pytest.raises(ValidationError):
        service.extraction.ingest("demo", 2024, "math1", 1, [{"number": 1}])
    assert service.library.stats()["papers"] == 0


def test_ingest_accepts_schema_v2_document(service) -> None:
    legacy = {
        "number": 1,
        "section": "fill",
        "points": 5,
        "latex": "求 $\\int_0^1 x\\,dx$。",
    }
    service.extraction.ingest("demo", 2024, "math1", 1, [legacy])
    paper = service.library.get_paper("demo", 2024, "math1", 1)
    assert paper["questions"][0]["stem"]["text"].startswith("求")


def test_ingest_document_uses_document_metadata(service) -> None:
    document = {
        "paper": {"series_key": "demo", "year": 2024, "subject": "math1", "paper_no": 3},
        "questions": [make_fill_question(11)],
    }
    result = service.extraction.ingest_document(document)
    assert result["natural_key"] == "2024/math1/demo/3"


def test_ingest_document_accepts_a_read_response(service) -> None:
    """A paper that is read can be written back unchanged.

    This is the invariant that makes the two surfaces share one shape: drop the
    read-only ``meta`` block and the response *is* a write payload. Previously
    reads returned ``{summary, questions}`` while writes required
    ``{paper, questions}``, so no client could round-trip without translating.
    """

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    read = service.library.get_paper("demo", 2024, "math1", 1)

    payload = {key: value for key, value in read.items() if key != "meta"}
    result = service.extraction.ingest_document(payload, replace=True)
    assert result["operation"] == "replaced"
    assert result["question_count"] == 1


def test_ingest_document_rejects_read_only_fields(service) -> None:
    """Derived fields are refused rather than silently dropped."""

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    read = service.library.get_paper("demo", 2024, "math1", 1)
    payload = {key: value for key, value in read.items() if key != "meta"}
    payload["question_count"] = 999
    with pytest.raises(ValidationError, match="read-only"):
        service.extraction.ingest_document(payload, replace=True)


def test_ingest_document_rejects_unknown_fields(service) -> None:
    """A typo'd key is an error, not a silently ignored field."""

    document = {
        "paper": {"series_key": "demo", "year": 2024, "subject": "math1", "paper_no": 1},
        "questions": [make_choice_question(1)],
        "quesitons": [],
    }
    with pytest.raises(ValidationError, match="unsupported fields"):
        service.extraction.ingest_document(document)


def test_ingest_document_rejects_a_wrong_content_hash(service) -> None:
    """The stored hash is a self-check, so a stale one must not be accepted."""

    document = {
        "paper": {"series_key": "demo", "year": 2024, "subject": "math1", "paper_no": 1},
        "questions": [make_choice_question(1)],
        "content_hash": "0" * 64,
    }
    with pytest.raises(ValidationError, match="content_hash"):
        service.extraction.ingest_document(document)


def test_delete_paper_rebuilds_index_and_release(service) -> None:
    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    removed = service.extraction.delete_paper("demo", 2024, "math1", 1)
    assert removed["removed"] is True
    assert service.library.stats()["papers"] == 0
    missing = service.extraction.delete_paper("demo", 2024, "math1", 1)
    assert missing["removed"] is False
