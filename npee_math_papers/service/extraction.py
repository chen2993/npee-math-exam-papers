"""Extraction use cases: register sources, split pages, ingest questions.

This is the agent-facing write path. Validation is inline: :meth:`ingest` validates
the full question array through the shared model before anything is written, so an
invalid extraction is rejected at the boundary rather than discovered later.

No method here accepts a raw path for writing. Identifiers (series/year/subject/
capture_id) are validated and the store derives the location, which closes the
path-injection surface an MCP tool would otherwise expose.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from npee_math_papers.core.question import convert_v2_question, has_schema_v3, validate_questions
from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.paper import parse_document
from npee_math_papers.service.context import ServiceContext
from npee_math_papers.core.store import PaperRecord


class ExtractionService:
    """Write-path use cases for sources, captures and papers."""

    def __init__(self, context: ServiceContext) -> None:
        self.ctx = context

    # --- sources -----------------------------------------------------------

    def register_source(
        self,
        series_key: str,
        year: int,
        subject: str,
        pdf_path: str | Path,
        *,
        source_id: str | None = None,
        page_count: int | None = None,
        notes: str | None = None,
        move: bool = False,
    ) -> dict[str, Any]:
        """Register a source PDF for a bundle and return its record."""

        ref = self.ctx.sources.register(
            series_key,
            year,
            subject,
            Path(pdf_path),
            source_id=source_id,
            page_count=page_count,
            notes=notes,
            move=move,
        )
        return ref.summary()

    def get_source(self, series_key: str, year: int, subject: str) -> dict[str, Any]:
        """Return the registered source for a bundle."""

        return self.ctx.sources.get(series_key, year, subject).summary()

    def list_sources(self) -> list[dict[str, Any]]:
        """Return every registered source."""

        return [ref.summary() for ref in self.ctx.sources.list_sources()]

    # --- captures ----------------------------------------------------------

    def prepare_capture(
        self,
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        *,
        question_pages: Sequence[int],
        answer_pages: Sequence[int] = (),
        exclude_pages: Sequence[int] = (),
        source_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a capture with explicit, non-overlapping page boundaries."""

        ref = self.ctx.captures.prepare(
            series_key,
            year,
            subject,
            capture_id,
            question_pages=question_pages,
            answer_pages=answer_pages,
            exclude_pages=exclude_pages,
            source_id=source_id,
            notes=notes,
        )
        return ref.summary()

    def add_page(
        self,
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        page_number: int,
        png_path: str | Path,
    ) -> dict[str, Any]:
        """Add one rendered page to a capture."""

        target = self.ctx.captures.add_page(series_key, year, subject, capture_id, page_number, Path(png_path))
        return {"capture_id": capture_id, "page": page_number, "path": target.as_posix()}

    def list_captures(
        self,
        *,
        series_key: str | None = None,
        year: int | None = None,
        subject: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return captures, optionally filtered."""

        return [ref.summary() for ref in self.ctx.captures.list_captures(series_key, year, subject)]

    def get_capture(self, series_key: str, year: int, subject: str, capture_id: str) -> dict[str, Any]:
        """Return one capture's record."""

        return self.ctx.captures.get(series_key, year, subject, capture_id).summary()

    def set_capture_status(self, series_key: str, year: int, subject: str, capture_id: str, status: str) -> dict[str, Any]:
        """Update a capture's lifecycle status."""

        self.ctx.captures.set_status(series_key, year, subject, capture_id, status)
        return self.ctx.captures.get(series_key, year, subject, capture_id).summary()

    # --- ingestion ---------------------------------------------------------

    def ingest(
        self,
        series_key: str,
        year: int,
        subject: str,
        paper_no: int,
        questions: Sequence[Mapping[str, Any]],
        *,
        replace: bool = False,
        series_name: str | None = None,
        capture_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate and write one paper's questions.

        Accepts either schema-3.0 questions or schema-2.0 questions, which are
        converted first. Validation runs before any write; on failure nothing is
        changed. ``replace`` must be explicit to overwrite an existing paper.
        """

        converted: list[dict[str, Any]] = []
        for index, question in enumerate(questions):
            if not isinstance(question, Mapping):
                raise ValidationError(f"questions[{index}] must be an object")
            raw = dict(question)
            converted.append(raw if has_schema_v3(raw) else convert_v2_question(raw))
        validated = [question.to_dict() for question in validate_questions(converted, f"{series_key}/{year}/{subject}/{paper_no}.questions")]
        record = PaperRecord(series_key, year, subject, paper_no, validated)
        operation = self.ctx.store.write_paper(record, replace=replace, series_name=series_name)
        self.ctx.store.rebuild_index()
        self.ctx.store.write_release()
        if capture_id is not None:
            self.ctx.captures.set_status(series_key, year, subject, capture_id, "returned")
        return {
            "operation": operation,
            "natural_key": record.natural_key,
            "question_count": len(validated),
            "content_hash": record.content_hash,
        }

    def ingest_document(
        self,
        document: Mapping[str, Any],
        *,
        identity: tuple[str, int, str, int] | None = None,
        replace: bool = False,
        series_name: str | None = None,
    ) -> dict[str, Any]:
        """Ingest a full paper document.

        The payload is exactly what :meth:`LibraryService.get_paper` returns with
        its ``meta`` block removed, so a caller can read a paper, change a
        question and write it back without translating between two shapes.

        Validation is strict: unknown top-level keys and read-only derived fields
        are rejected. The previous implementation read ``document["paper"]`` with
        ``.get(...) or {}`` and fell back to its own arguments, which meant a
        structurally wrong payload silently wrote a paper the caller never asked
        for.

        ``identity`` exists only for callers that already know the natural key
        (the extraction pipeline builds it from a capture) and is ignored when
        the document carries its own ``paper`` block.
        """

        if identity is not None and (not isinstance(document, Mapping) or "paper" not in document):
            series_key, year, subject, paper_no = identity
            document = {**document, "paper": {
                "series_key": series_key,
                "year": year,
                "subject": subject,
                "paper_no": paper_no,
            }}

        parsed_identity, questions, _stored = parse_document(document, context="document")
        return self.ingest(
            parsed_identity.series_key,
            parsed_identity.year,
            parsed_identity.subject,
            parsed_identity.paper_no,
            questions,
            replace=replace,
            series_name=series_name,
        )

    def delete_paper(self, series_key: str, year: int, subject: str, paper_no: int) -> dict[str, Any]:
        """Delete one paper (destructive; callers should gate on human approval)."""

        removed = self.ctx.store.delete_paper(series_key, year, subject, paper_no)
        if removed:
            self.ctx.store.rebuild_index()
            self.ctx.store.write_release()
        return {"removed": removed, "series_key": series_key, "year": year, "subject": subject, "paper_no": paper_no}
