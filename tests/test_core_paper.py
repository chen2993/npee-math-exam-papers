"""The paper-document contract: one shape for reading, writing and transport."""

from __future__ import annotations

import pytest

from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.paper import (
    PAPER_SCHEMA_VERSION,
    PaperIdentity,
    build_document,
    derived_summary,
    merge_read_response,
    parse_document,
    parse_identity,
    strip_meta,
)

from tests.conftest import make_choice_question, make_fill_question


def identity() -> PaperIdentity:
    return PaperIdentity(series_key="demo", year=2024, subject="math1", paper_no=3)


def test_identity_derives_key_and_bundle() -> None:
    assert identity().natural_key == "2024/math1/demo/3"
    assert identity().bundle == "demo-2024-math1"
    assert identity().meta() == {
        "series_key": "demo",
        "year": 2024,
        "subject": "math1",
        "paper_no": 3,
    }


def test_build_document_has_the_documented_shape() -> None:
    document = build_document(identity(), [make_choice_question(1)])
    assert sorted(document) == ["paper", "questions", "schema_version"]
    assert document["schema_version"] == PAPER_SCHEMA_VERSION
    assert document["paper"]["paper_no"] == 3


def test_parse_document_accepts_what_build_document_produces() -> None:
    """Constructor and parser must agree, or the store cannot round-trip."""

    questions = [make_choice_question(1), make_fill_question(11)]
    document = build_document(identity(), questions)
    parsed_identity, parsed_questions, stored_hash = parse_document(document, context="doc")
    assert parsed_identity == identity()
    assert len(parsed_questions) == 2
    assert stored_hash is None


def test_parse_document_verifies_a_supplied_hash() -> None:
    questions = [make_choice_question(1)]
    good = build_document(identity(), questions, extra={"content_hash": derived_summary(
        identity(), series_name="demo", questions=questions)["content_hash"]})
    # Recompute through the same path the parser uses.
    _, _, stored = parse_document(good, context="doc")
    assert stored is not None

    bad = dict(good, content_hash="0" * 64)
    with pytest.raises(ValidationError, match="content_hash"):
        parse_document(bad, context="doc")


def test_parse_document_rejects_read_only_fields() -> None:
    document = build_document(identity(), [make_choice_question(1)])
    document["question_count"] = 1
    with pytest.raises(ValidationError, match="read-only"):
        parse_document(document, context="doc")


def test_parse_document_rejects_unknown_fields() -> None:
    document = build_document(identity(), [make_choice_question(1)])
    document["quesitons"] = []
    with pytest.raises(ValidationError, match="unsupported fields"):
        parse_document(document, context="doc")


def test_parse_document_rejects_a_misspelled_identity_field() -> None:
    """A typo must fail loudly instead of defaulting the paper number."""

    document = build_document(identity(), [make_choice_question(1)])
    document["paper"] = {"seriesKey": "demo", "year": 2024, "subject": "math1", "paper_no": 1}
    with pytest.raises(ValidationError, match="unsupported fields"):
        parse_document(document, context="doc")


def test_parse_document_requires_the_identity_fields() -> None:
    document = build_document(identity(), [make_choice_question(1)])
    document["paper"] = {"series_key": "demo", "year": 2024}
    with pytest.raises(ValidationError, match="missing fields"):
        parse_document(document, context="doc")


def test_parse_document_rejects_an_unknown_subject() -> None:
    document = build_document(
        PaperIdentity(series_key="demo", year=2024, subject="math9", paper_no=1),
        [make_choice_question(1)],
    )
    with pytest.raises(ValidationError, match="subject"):
        parse_document(document, context="doc")


def test_parse_document_accepts_a_document_without_schema_version() -> None:
    """The documented compatibility path: earlier extraction output has no version."""

    document = build_document(identity(), [make_choice_question(1)])
    document.pop("schema_version")
    parsed_identity, questions, _ = parse_document(document, context="doc")
    assert parsed_identity.paper_no == 3 and len(questions) == 1


def test_parse_document_rejects_an_obsolete_schema_version() -> None:
    document = build_document(identity(), [make_choice_question(1)])
    document["schema_version"] = "2.0"
    with pytest.raises(ValidationError, match="schema_version"):
        parse_document(document, context="doc")


def test_identity_rejects_empty_series_key() -> None:
    with pytest.raises(ValidationError, match="series_key"):
        parse_identity({"series_key": "", "year": 2024, "subject": "math1", "paper_no": 1}, context="doc")


def test_derived_summary_counts_sections_and_figures() -> None:
    questions = [make_choice_question(1), make_fill_question(11)]
    summary = derived_summary(identity(), series_name="示例", questions=questions)
    assert summary["question_count"] == 2
    assert summary["section_counts"] == {"choice": 1, "fill": 1}
    assert summary["natural_key"] == "2024/math1/demo/3"
    assert summary["series_name"] == "示例"


def test_read_response_minus_meta_is_a_write_payload() -> None:
    """The invariant the whole module exists to guarantee."""

    questions = [make_choice_question(1)]
    document = build_document(identity(), questions)
    meta = derived_summary(identity(), series_name="示例", questions=questions)
    response = merge_read_response(document, meta)

    assert response["meta"]["content_hash"]
    payload = strip_meta(response)
    parsed_identity, parsed_questions, stored = parse_document(payload, context="doc")
    assert parsed_identity == identity()
    assert len(parsed_questions) == 1
    # The derived hash must not survive into the payload, or editing a question
    # would fail against a hash the caller was merely echoing back.
    assert stored is None
