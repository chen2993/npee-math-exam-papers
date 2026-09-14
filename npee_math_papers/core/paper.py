r"""The canonical paper document: one shape for disk, MCP and HTTP.

Why this module exists
----------------------
The store, the MCP tools and the HTTP API each used to describe a paper
differently. Reading a paper returned ``{summary: {...}, questions: [...]}``
but writing one required ``{paper: {...}, questions: [...]}``, so a client could
not feed a read result back into a write. Worse, the write path looked up
``document["paper"]`` with ``.get(...) or {}`` and silently fell back to its own
function arguments, so a structurally wrong payload "succeeded" while writing
something the caller never intended.

This module is the single definition of what a paper document is:

* :data:`DOCUMENT_KEYS` — the only top-level keys that are *input*;
* :func:`parse_document` — strict parsing shared by every reader and writer;
* :func:`build_document` — the one constructor, so the on-disk file and the
  transported document cannot drift apart;
* :func:`derived_summary` — the computed fields (counts, hashes, display name)
  that ride along with a read but are **never** accepted as input.

The rule that keeps the two surfaces honest:

    A read response, minus its read-only ``meta`` block, is exactly a valid
    write payload.

Nothing here touches the filesystem or a third-party package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from npee_math_papers.core.canonical import content_hash, natural_key
from npee_math_papers.core.domain import SUBJECTS
from npee_math_papers.core.errors import ValidationError

#: Schema version written into every document.
PAPER_SCHEMA_VERSION = "3.0"

#: The only top-level keys a document may carry.
#:
#: ``content_hash`` is included because the on-disk file records it, but it is a
#: *self-check*: a supplied value must equal the hash recomputed from the
#: questions, so it can never be used to lie about the content.
DOCUMENT_KEYS: tuple[str, ...] = ("schema_version", "paper", "questions", "content_hash")

#: Keys required in every document.
#:
#: ``schema_version`` and ``content_hash`` are written on every save but are
#: optional on *input*: the documented compatibility entry point accepts
#: documents produced by earlier extraction runs. When present they are
#: validated, so an obsolete version or a wrong hash is still rejected.
REQUIRED_DOCUMENT_KEYS: tuple[str, ...] = ("paper", "questions")

#: The identity fields inside ``paper``. There is no other place to put them.
PAPER_FIELDS: tuple[str, ...] = ("series_key", "year", "subject", "paper_no")

#: Fields returned by a read but rejected on write. They are computed from the
#: content, so accepting them from a client would let a payload assert counts or
#: a display name that the stored questions do not support. ``content_hash`` is
#: deliberately absent: the file records it as a self-check, and it is accepted
#: as long as it matches the questions (see :func:`parse_document`).
DERIVED_FIELDS: tuple[str, ...] = (
    "natural_key",
    "bundle",
    "series_name",
    "question_count",
    "section_counts",
    "figure_count",
)

#: Read-only fields a read response carries under ``meta`` rather than at the top
#: level, so the top level stays a valid write payload.
META_FIELDS: tuple[str, ...] = DERIVED_FIELDS + ("content_hash",)


@dataclass(frozen=True)
class PaperIdentity:
    """The typed natural key of one paper."""

    series_key: str
    year: int
    subject: str
    paper_no: int

    @property
    def natural_key(self) -> str:
        return natural_key(self.year, self.subject, self.series_key, self.paper_no)

    @property
    def bundle(self) -> str:
        return f"{self.series_key}-{self.year}-{self.subject}"

    def meta(self) -> dict[str, Any]:
        """Return the ``paper`` block as it appears in a document."""

        return {
            "series_key": self.series_key,
            "year": self.year,
            "subject": self.subject,
            "paper_no": self.paper_no,
        }


def normalize_questions(questions: Any, *, context: str = "questions") -> list[dict[str, Any]]:
    """Validate a question array and return its canonical form.

    The single normalization step: the store writes these bytes, the parser
    validates against them, and the hash is computed over them. Keeping one
    implementation is what stops a stored ``content_hash`` from disagreeing with
    a later re-read.
    """

    from npee_math_papers.core.question import validate_questions

    return [
        question.to_dict()
        for question in validate_questions(questions, context)
    ]


def parse_identity(meta: Any, *, context: str) -> PaperIdentity:
    """Validate a ``paper`` block into a :class:`PaperIdentity`.

    Unknown keys are rejected rather than ignored: a typo such as ``paperNo``
    would otherwise be dropped silently and the paper would be written under a
    defaulted number.
    """

    if not isinstance(meta, Mapping):
        raise ValidationError(f"{context}.paper must be an object")
    unknown = sorted(set(meta) - set(PAPER_FIELDS))
    if unknown:
        raise ValidationError(
            f"{context}.paper has unsupported fields: {', '.join(unknown)}; "
            f"expected only {', '.join(PAPER_FIELDS)}"
        )
    missing = sorted(set(PAPER_FIELDS) - set(meta))
    if missing:
        raise ValidationError(f"{context}.paper is missing fields: {', '.join(missing)}")
    try:
        year = int(meta["year"])
        paper_no = int(meta["paper_no"])
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{context}.paper.year and paper_no must be integers") from error
    series_key = str(meta["series_key"])
    subject = str(meta["subject"])
    if not series_key:
        raise ValidationError(f"{context}.paper.series_key must not be empty")
    if subject not in SUBJECTS:
        raise ValidationError(
            f"{context}.paper.subject must be one of {', '.join(SUBJECTS)}"
        )
    return PaperIdentity(series_key=series_key, year=year, subject=subject, paper_no=paper_no)


def build_document(
    identity: PaperIdentity,
    questions: Sequence[Mapping[str, Any]],
    *,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a paper document.

    This is the only constructor, so everything written to disk and everything
    sent over a wire has the same key order and the same nesting.

    ``extra`` carries document-level fields contributed by a caller (the store
    passes ``content_hash``); it is merged after the base keys and is validated
    by :func:`parse_document` like any other input.
    """

    document: dict[str, Any] = {
        "schema_version": PAPER_SCHEMA_VERSION,
        "paper": identity.meta(),
        "questions": list(questions),
    }
    if extra:
        unknown = sorted(set(extra) - set(DOCUMENT_KEYS))
        if unknown:
            raise ValidationError(
                f"document has unsupported fields: {', '.join(unknown)}"
            )
        document.update(extra)
    return document


def parse_document(
    payload: Any,
    *,
    context: str,
) -> tuple[PaperIdentity, list[dict[str, Any]], str | None]:
    """Validate a document and return its identity, questions and stored hash.

    Strict by design. A read-only field (see :data:`DERIVED_FIELDS`) present at
    the top level is an error rather than something to ignore, because silently
    dropping it is what allowed a mismatched payload to look successful.
    """

    if not isinstance(payload, Mapping):
        raise ValidationError(f"{context} must be an object")

    derived = sorted(set(payload) & set(DERIVED_FIELDS))
    if derived:
        raise ValidationError(
            f"{context} carries read-only fields: {', '.join(derived)}; "
            "these are derived from the questions and are not accepted as input"
        )
    unknown = sorted(set(payload) - set(DOCUMENT_KEYS))
    if unknown:
        raise ValidationError(
            f"{context} has unsupported fields: {', '.join(unknown)}; "
            f"expected only {', '.join(DOCUMENT_KEYS)}"
        )
    missing = sorted(set(REQUIRED_DOCUMENT_KEYS) - set(payload))
    if missing:
        raise ValidationError(f"{context} is missing fields: {', '.join(missing)}")

    declared_version = payload.get("schema_version")
    if declared_version is not None and declared_version != PAPER_SCHEMA_VERSION:
        raise ValidationError(
            f"{context} must declare schema_version {PAPER_SCHEMA_VERSION!r}"
        )

    identity = parse_identity(payload.get("paper"), context=context)

    questions = normalize_questions(payload.get("questions"), context=f"{context}.questions")

    stored_hash = payload.get("content_hash")
    if stored_hash is not None:
        if not isinstance(stored_hash, str) or not stored_hash:
            raise ValidationError(f"{context}.content_hash must be a non-empty string")
        actual = content_hash(questions)
        if stored_hash != actual:
            raise ValidationError(
                f"{context}.content_hash does not match its questions; "
                "re-run the migration or re-extract"
            )
    return identity, questions, stored_hash


def derived_summary(
    identity: PaperIdentity,
    *,
    series_name: str,
    questions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the computed fields that accompany a paper.

    Defined once here so list views, the MCP tools and the HTTP API cannot
    disagree about a paper's counts or its display name.

    Counts are taken from the questions as given, but the hash is computed from
    the *normalized* array, matching :func:`parse_document` and the store's
    write path. Hashing the raw input instead would make the reported hash
    depend on incidental input formatting, so a paper could carry a different
    hash in a list row than the same paper carries when read in full.
    """

    counts: dict[str, int] = {}
    figure_count = 0
    for question in questions:
        section = str(question.get("section", "unknown"))
        counts[section] = counts.get(section, 0) + 1
        stem = question.get("stem") or {}
        figure_count += len(stem.get("figures") or [])
        for choice in question.get("choices") or []:
            figure_count += len(choice.get("figures") or [])
        for subpart in question.get("subparts") or []:
            figure_count += len(subpart.get("figures") or [])
    return {
        "natural_key": identity.natural_key,
        "bundle": identity.bundle,
        "series_key": identity.series_key,
        "series_name": series_name or identity.series_key,
        "year": identity.year,
        "subject": identity.subject,
        "paper_no": identity.paper_no,
        "question_count": len(questions),
        "section_counts": counts,
        "figure_count": figure_count,
        "content_hash": content_hash(normalize_questions(questions)),
    }


def merge_read_response(
    document: Mapping[str, Any],
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Combine a document with its derived block into one read response.

    The document is spread at the top level (not nested under another key) so the
    invariant holds mechanically: deleting ``meta`` from this response yields a
    payload that :func:`parse_document` accepts unchanged.

    ``content_hash`` is moved out of the top level into ``meta`` on the way out.
    It is written to disk as a self-check, but it is *derived* from the questions
    just like the counts are, so leaving it in the payload would mean any edit
    invalidated the hash the caller was echoing back — making "read, change one
    question, write" fail for a reason that has nothing to do with the change.
    """

    payload = dict(document)
    stored_hash = payload.pop("content_hash", None)
    merged_meta = dict(meta)
    if stored_hash is not None:
        merged_meta["content_hash"] = stored_hash
    payload["meta"] = merged_meta
    return payload


def strip_meta(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a read response as a plain write payload."""

    return {key: value for key, value in payload.items() if key != "meta"}
