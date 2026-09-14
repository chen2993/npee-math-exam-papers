"""Library use cases: browse, read, search and inventory the question bank.

Everything the catalog UI and the MCP library tools need, expressed over the store
so both surfaces return identical data.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from npee_math_papers.core.domain import (
    DEFAULT_PAPER_ORDER,
    PAPER_ORDER_KEYS,
    normalize_paper_order,
    subject_label,
)
from npee_math_papers.core.errors import NotFoundError, ValidationError
from npee_math_papers.core.paper import merge_read_response
from npee_math_papers.service.context import ServiceContext
from npee_math_papers.core.store import parse_bundle_key


class LibraryService:
    """Read-only queries over the paper store."""

    def __init__(self, context: ServiceContext) -> None:
        self.ctx = context

    # --- inventory ---------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return library-wide counts and facets."""

        stats = self.ctx.store.stats()
        stats["series_names"] = self.ctx.display_names()
        return stats

    def list_series(self) -> list[dict[str, Any]]:
        """Return every registered series with its paper and question counts."""

        names = self.ctx.display_names()
        counts: dict[str, dict[str, Any]] = {}
        for summary in self.ctx.store.list_summaries():
            entry = counts.setdefault(
                summary["series_key"],
                {"series_key": summary["series_key"], "series_name": names.get(summary["series_key"], summary["series_key"]), "paper_count": 0, "question_count": 0, "years": set(), "subjects": set()},
            )
            entry["paper_count"] += 1
            entry["question_count"] += summary["question_count"]
            entry["years"].add(summary["year"])
            entry["subjects"].add(summary["subject"])
        result: list[dict[str, Any]] = []
        for key in sorted(counts):
            entry = counts[key]
            result.append(
                {
                    "series_key": entry["series_key"],
                    "series_name": entry["series_name"],
                    "paper_count": entry["paper_count"],
                    "question_count": entry["question_count"],
                    "years": sorted(entry["years"]),
                    "subjects": sorted(entry["subjects"]),
                }
            )
        return result

    def list_bundles(
        self,
        *,
        series_keys: Sequence[str] | None = None,
        years: Sequence[int] | None = None,
        subjects: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return bundles, filtered by the same vocabulary as :meth:`list_papers`.

        Filtering lives here rather than in an adapter: the MCP tool used to
        filter ``year``/``subject`` in Python while the HTTP endpoint could not
        filter them at all, so the two surfaces offered different capabilities
        for the same query. One implementation, exposed identically.
        """

        wanted_series = set(series_keys) if series_keys else None
        wanted_years = {int(year) for year in years} if years else None
        wanted_subjects = set(subjects) if subjects else None
        bundles = []
        for bundle in self.ctx.store.list_bundles():
            if wanted_series is not None and bundle.series_key not in wanted_series:
                continue
            if wanted_years is not None and bundle.year not in wanted_years:
                continue
            if wanted_subjects is not None and bundle.subject not in wanted_subjects:
                continue
            bundles.append(
                {
                    "bundle": bundle.key,
                    "series_key": bundle.series_key,
                    "series_name": bundle.display_name or self.ctx.display_name(bundle.series_key),
                    "year": bundle.year,
                    "subject": bundle.subject,
                    "paper_count": bundle.paper_count,
                }
            )
        return bundles

    def list_papers(
        self,
        *,
        series_keys: Sequence[str] | None = None,
        years: Sequence[int] | None = None,
        subjects: Sequence[str] | None = None,
        paper_nos: Sequence[int] | None = None,
        query: str | None = None,
        order: str = DEFAULT_PAPER_ORDER,
        offset: int = 0,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Return a paginated, filtered list of paper summaries.

        Summaries deliberately omit the questions so a list view stays small; fetch
        a single paper with :meth:`get_paper` when the questions are needed.

        ``query`` is a case-insensitive substring match over the series name, the
        series key, the year, the subject and the paper number, so a human can
        type "zhangyu8 2024" and get that year's papers. Filtering happens before
        pagination, which is what keeps ``total`` — and therefore the pager —
        correct for the *filtered* set rather than the whole library.
        """

        if offset < 0:
            raise ValidationError("offset must be >= 0")
        if limit is not None and limit < 1:
            raise ValidationError("limit must be >= 1")
        all_summaries = self.ctx.store.list_summaries(
            series_keys=series_keys,
            years=years,
            subjects=subjects,
            paper_nos=paper_nos,
        )
        names = self.ctx.display_names()
        for summary in all_summaries:
            summary["series_name"] = names.get(summary["series_key"], summary["series_key"])
        if query and query.strip():
            all_summaries = _filter_summaries(all_summaries, query.strip())
        all_summaries.sort(key=paper_sort_key(order))
        total = len(all_summaries)
        window = all_summaries[offset : offset + limit] if limit is not None else all_summaries[offset:]
        return {"total": total, "offset": offset, "count": len(window), "papers": window}

    def get_paper(
        self,
        series_key: str,
        year: int,
        subject: str,
        paper_no: int,
        *,
        with_questions: bool = True,
    ) -> dict[str, Any]:
        """Return one paper; when ``with_questions`` is false only the summary.

        With questions, the response is the canonical document plus a ``meta``
        block: the document keys sit at the top level, so dropping ``meta``
        yields a payload the write path accepts unchanged. Without questions the
        response is just the derived summary, for cheap list/peek use.

        The return shape is JSON-compatible and identical over HTTP and MCP.
        """

        if not with_questions:
            summary = self.ctx.store.read_paper_summary(series_key, year, subject, paper_no)
            summary["series_name"] = self.ctx.display_name(series_key)
            return summary
        record = self.ctx.store.read_paper(series_key, year, subject, paper_no)
        meta = record.summary()
        meta["series_name"] = self.ctx.display_name(series_key)
        return merge_read_response(record.document(), meta)

    def get_question(self, series_key: str, year: int, subject: str, paper_no: int, question_no: int) -> dict[str, Any]:
        """Return one question with its paper context."""

        record = self.ctx.store.read_paper(series_key, year, subject, paper_no)
        for question in record.questions:
            if int(question["number"]) == int(question_no):
                return {
                    "natural_key": record.natural_key,
                    "series_name": self.ctx.display_name(series_key),
                    "paper_no": record.paper_no,
                    "question": question,
                }
        raise NotFoundError(f"question {question_no} not found in {record.natural_key}")

    def search(
        self,
        query: str,
        *,
        series_keys: Sequence[str] | None = None,
        subjects: Sequence[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search question stems and choices for a substring.

        This is a linear scan over question text. It is intentionally simple and
        exact; a derived index can replace it later without changing the contract.
        """

        needle = query.strip()
        if not needle:
            raise ValidationError("query must be non-empty")
        if limit < 1:
            raise ValidationError("limit must be >= 1")
        matches: list[dict[str, Any]] = []
        names = self.ctx.display_names()
        wanted_series = set(series_keys) if series_keys else None
        wanted_subjects = set(subjects) if subjects else None
        for bundle in self.ctx.store.list_bundles():
            if wanted_series is not None and bundle.series_key not in wanted_series:
                continue
            if wanted_subjects is not None and bundle.subject not in wanted_subjects:
                continue
            for record in (self.ctx.store.read_paper(bundle.series_key, bundle.year, bundle.subject, _paper_no(path)) for path in bundle.paper_paths):
                for question in record.questions:
                    haystack = _question_text(question)
                    if needle in haystack:
                        matches.append(
                            {
                                "natural_key": record.natural_key,
                                "series_key": record.series_key,
                                "series_name": names.get(record.series_key, record.series_key),
                                "year": record.year,
                                "subject": record.subject,
                                "paper_no": record.paper_no,
                                "number": question["number"],
                                "section": question["section"],
                                "excerpt": haystack[:120],
                            }
                        )
                        if len(matches) >= limit:
                            return {"total": len(matches), "limit": limit, "matches": matches}
        return {"total": len(matches), "limit": limit, "matches": matches}

    def overview(self) -> dict[str, Any]:
        """Return a single object with stats, series and bundles for dashboards."""

        return {
            "stats": self.stats(),
            "series": self.list_series(),
            "bundles": self.list_bundles(),
        }

    def resolve_natural_keys(self, keys: Sequence[str]) -> dict[str, Any]:
        """Split natural keys into those present and absent in the store."""

        present: list[str] = []
        absent: list[str] = []
        for key in keys:
            parts = key.split("/")
            if len(parts) != 4:
                absent.append(key)
                continue
            year, subject, series_key, paper_no = parts
            try:
                number = int(paper_no)
                year_value = int(year)
            except ValueError:
                absent.append(key)
                continue
            (present if self.ctx.store.has_paper(series_key, year_value, subject, number) else absent).append(key)
        return {"present": present, "absent": absent}


def _filter_summaries(summaries: Sequence[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Return the summaries whose display fields contain ``query``.

    The haystack includes both the human-facing series name and the machine
    series key, so "张宇" and "zhangyu8" both match, and the subject is matched
    through its Chinese label as well as its code.
    """

    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    for summary in summaries:
        haystack = " ".join(
            str(part)
            for part in (
                summary.get("series_name"),
                summary.get("series_key"),
                summary.get("year"),
                summary.get("paper_no"),
                summary.get("subject"),
                subject_label(str(summary.get("subject") or "")),
                summary.get("natural_key"),
            )
            if part is not None
        ).casefold()
        if needle in haystack:
            matches.append(summary)
    return matches


class _Descending:
    """Sort-key component that compares in reverse.

    ``sorted(key=...)`` has no per-component ``reverse`` flag, so descending
    order is expressed by wrapping the value. This keeps every ordering mode a
    single declarative table instead of a chain of ``if`` branches.
    """

    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Descending) and self.value == other.value

    def __lt__(self, other: "_Descending") -> bool:
        return self.value > other.value

    def __hash__(self) -> int:
        return hash(self.value)


def paper_sort_key(order: str):
    """Build the sort key for one paper summary under an ordering mode.

    Summaries can come from the derived index or from a freshly parsed document,
    so every component is coerced to a comparable primitive to keep the order
    insensitive to the source representation.
    """

    fields = PAPER_ORDER_KEYS[normalize_paper_order(order)]

    def key(summary: Mapping[str, Any]) -> tuple:
        values: list[Any] = []
        for field, descending in fields:
            if field in ("year", "question_count", "paper_no"):
                value: Any = int(summary.get(field) or 0)
            else:
                # series_key and subject sort lexically, which is also their
                # intended order (math1 < math2 < math3).
                value = str(summary.get(field) or "")
            values.append(_Descending(value) if descending else value)
        return tuple(values)

    return key


def _paper_no(path: Any) -> int:
    return int(path.stem)


def _question_text(question: Mapping[str, Any]) -> str:
    """Flatten a question into searchable text."""

    parts: list[str] = []
    stem = question.get("stem") or {}
    parts.append(str(stem.get("text", "")))
    for choice in question.get("choices") or []:
        parts.append(str(choice.get("text", "")))
    for subpart in question.get("subparts") or []:
        parts.append(str(subpart.get("text", "")))
    return "\n".join(parts)


def bundle_identity(bundle_key_value: str) -> tuple[str, int, str]:
    """Expose bundle parsing through the service layer for adapters."""

    return parse_bundle_key(bundle_key_value)
