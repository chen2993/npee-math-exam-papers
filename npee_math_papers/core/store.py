"""Paper store: the authoritative on-disk repository for `.npee-math-papers`.

Layout under the data root (default ``.npee-math-papers/``)::

    .npee-math-papers/
    ├─ sources/<series>-<year>-<subject>/
    │  ├─ source.pdf
    │  └─ source.json                 provenance, page count, sha256
    ├─ captures/<series>-<year>-<subject>/<capture_id>/
    │  ├─ pages/p####.png             visual evidence (read-only after capture)
    │  └─ capture.json                page boundaries and status
    ├─ papers/<series>-<year>-<subject>/
    │  ├─ bundle.json                 bundle metadata (machine-only)
    │  └─ <paper_no>.yaml             one paper per file (YAML, agent-editable)
    ├─ index/
    │  ├─ papers.json                 derived flat summary list (machine-only)
    │  └─ bundles.json                derived bundle list (machine-only)
    └─ release.json                   content hashes for every paper (machine-only)

Format policy
-------------
Paper documents are the only files a human or agent edits by hand, and they are
full of LaTeX, so they are stored as YAML with literal block scalars (see
:mod:`npee_math_papers.core.serialize`). Index, release and bundle metadata are machine-only
and contain no LaTeX, so they stay compact JSON.

The single source of truth for paper content is ``papers/<bundle>/<n>.yaml``.
Everything under ``index/`` is derived and may be deleted and rebuilt at any time.

Write safety: every write goes through an atomic temp-file + rename so a reader
observes either the old or the new file, never a partial one.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from npee_math_papers.core.canonical import content_hash, natural_key
from npee_math_papers.core.domain import SUBJECTS
from npee_math_papers.core.errors import ConflictError, NotFoundError, ValidationError
from npee_math_papers.core.paper import (
    PAPER_SCHEMA_VERSION,
    PaperIdentity,
    build_document,
    derived_summary,
    normalize_questions,
    parse_document,
)

# Re-exported: `PAPER_SCHEMA_VERSION` is part of the store's public surface
# (``core/__init__`` and the migration tooling import it from here). It is
# defined in `core.paper`, which owns the document contract.
__all__ = ["PAPER_SCHEMA_VERSION", "PaperRecord", "PaperStore", "BundleRef"]
from npee_math_papers.core.serialize import dump_json_compatible, read_document, write_document

BUNDLE_SCHEMA_VERSION = "3.0"
INDEX_SCHEMA_VERSION = "1.0"
RELEASE_SCHEMA_VERSION = "3.0"
BUNDLE_META_NAME = "bundle.json"
PAPER_EXTENSION = ".yaml"


def bundle_key(series_key: str, year: int, subject: str) -> str:
    """Return the canonical bundle directory name ``<series>-<year>-<subject>``."""

    return f"{series_key}-{int(year)}-{subject}"


def parse_bundle_key(key: str) -> tuple[str, int, str]:
    """Parse ``<series>-<year>-<subject>`` back into typed parts.

    ``series_key`` may itself contain hyphens, so the year and subject are matched
    from the right. Raises :class:`ValidationError` on a malformed key.
    """

    parts = key.rsplit("-", 2)
    if len(parts) != 3:
        raise ValidationError(f"bundle key {key!r} must be <series>-<year>-<subject>")
    series_key, year_text, subject = parts
    if not series_key:
        raise ValidationError(f"bundle key {key!r} has an empty series")
    if subject not in SUBJECTS:
        raise ValidationError(f"bundle key {key!r} has an invalid subject {subject!r}")
    try:
        year = int(year_text)
    except ValueError as error:
        raise ValidationError(f"bundle key {key!r} has a non-numeric year") from error
    return series_key, year, subject


@dataclass(frozen=True)
class NpeePaths:
    """Resolved locations of every top-level area under the data root."""

    root: Path

    @property
    def sources(self) -> Path:
        return self.root / "sources"

    @property
    def captures(self) -> Path:
        return self.root / "captures"

    @property
    def papers(self) -> Path:
        return self.root / "papers"

    @property
    def index(self) -> Path:
        return self.root / "index"

    @property
    def release(self) -> Path:
        return self.root / "release.json"

    @property
    def registry(self) -> Path:
        return self.root / "registry.json"

    @property
    def staging(self) -> Path:
        return self.root / "staging"

    def ensure(self) -> None:
        for path in (self.sources, self.captures, self.papers, self.index, self.staging):
            path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def resolve(cls, root: str | Path | None = None, *, repository_root: Path | None = None) -> "NpeePaths":
        """Resolve the data root, honouring ``NPEE_DATA_ROOT`` then ``.npee-math-papers``."""

        if root is not None:
            return cls(Path(root).resolve())
        env = os.environ.get("NPEE_DATA_ROOT", "").strip()
        if env:
            return cls(Path(env).resolve())
        base = repository_root or Path(__file__).resolve().parents[2]
        return cls((base / ".npee-math-papers").resolve())


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_write_json(path: Path, value: Any) -> None:
    """Write ``value`` as UTF-8 JSON atomically with a trailing newline."""

    _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n")


def atomic_write_text(path: Path, text: str) -> None:
    """Write plain text atomically."""

    _atomic_write(path, text)


@dataclass(frozen=True)
class PaperRecord:
    """One paper with its identity and validated questions."""

    series_key: str
    year: int
    subject: str
    paper_no: int
    questions: list[dict[str, Any]]
    series_name: str | None = None

    @property
    def identity(self) -> PaperIdentity:
        """The typed natural key, built from the flat fields for convenience."""

        return PaperIdentity(
            series_key=self.series_key,
            year=self.year,
            subject=self.subject,
            paper_no=self.paper_no,
        )

    @property
    def natural_key(self) -> str:
        return self.identity.natural_key

    @property
    def bundle(self) -> str:
        return self.identity.bundle

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def content_hash(self) -> str:
        """Canonical hash of the question array; ignores metadata and ordering."""

        return content_hash(self.questions)

    def summary(self) -> dict[str, Any]:
        """Return the lightweight projection used by list views and MCP.

        Delegates to the shared contract so a list row and a full read cannot
        report different counts for the same paper.
        """

        return derived_summary(
            self.identity,
            series_name=self.series_name or self.series_key,
            questions=self.questions,
        )

    def document(self) -> dict[str, Any]:
        """Return the on-disk paper document (schema 3.0)."""

        return build_document(
            self.identity,
            self.questions,
            extra={"content_hash": self.content_hash},
        )


@dataclass(frozen=True)
class BundleRef:
    """A resolved bundle directory."""

    key: str
    series_key: str
    year: int
    subject: str
    path: Path
    display_name: str = ""

    @property
    def paper_paths(self) -> list[Path]:
        return sorted(
            (item for item in self.path.glob(f"*{PAPER_EXTENSION}")),
            key=lambda item: _paper_sort_key(item),
        )

    @property
    def paper_count(self) -> int:
        return len(self.paper_paths)


def read_paper_document(path: Path) -> PaperRecord:
    """Read and validate one paper document, verifying its stored content hash."""

    try:
        payload = read_document(path)
    except ValidationError:
        raise
    # Validation lives in the shared contract so the file reader, the MCP tools
    # and the HTTP API cannot disagree about what a valid document is.
    identity, questions, _stored_hash = parse_document(payload, context=path.as_posix())
    record = PaperRecord(
        series_key=identity.series_key,
        year=identity.year,
        subject=identity.subject,
        paper_no=identity.paper_no,
        questions=questions,
    )
    expected_name = f"{record.paper_no}{PAPER_EXTENSION}"
    if path.name != expected_name:
        raise ValidationError(
            f"{path.as_posix()} must be named {expected_name} for paper_no {record.paper_no}"
        )
    return record


class PaperStore:
    """Filesystem store for sources, captures, papers, index and release."""

    def __init__(self, paths: NpeePaths) -> None:
        self.paths = paths
        # Counts writes made through this instance so a read can detect that its
        # cached index is stale.
        self._written_since_index = 0
        # In-process summary cache: (paper_file_count, summaries).
        self._summary_cache: tuple[int, list[dict[str, Any]]] | None = None
        # Guards the cache and write counter: background compile threads share the store.
        self._state_lock = threading.Lock()

    # --- bundles -----------------------------------------------------------

    def bundle_dir(self, series_key: str, year: int, subject: str) -> Path:
        return self.paths.papers / bundle_key(series_key, year, subject)

    def paper_path(self, series_key: str, year: int, subject: str, paper_no: int) -> Path:
        return self.bundle_dir(series_key, year, subject) / f"{int(paper_no)}{PAPER_EXTENSION}"

    def bundle_meta_path(self, series_key: str, year: int, subject: str) -> Path:
        return self.bundle_dir(series_key, year, subject) / BUNDLE_META_NAME

    def list_bundle_keys(self) -> list[str]:
        """Return every bundle directory name, sorted."""

        if not self.paths.papers.is_dir():
            return []
        return sorted(item.name for item in self.paths.papers.iterdir() if item.is_dir())

    def list_bundles(self) -> list[BundleRef]:
        """Return every bundle with its display name resolved from ``bundle.json``."""

        bundles: list[BundleRef] = []
        for key in self.list_bundle_keys():
            series_key, year, subject = parse_bundle_key(key)
            path = self.paths.papers / key
            display_name = ""
            meta_path = path / BUNDLE_META_NAME
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    display_name = str(meta.get("series_name") or "")
                except (json.JSONDecodeError, AttributeError):
                    display_name = ""
            bundles.append(BundleRef(key=key, series_key=series_key, year=year, subject=subject, path=path, display_name=display_name))
        return bundles

    def write_bundle_meta(self, series_key: str, year: int, subject: str, display_name: str) -> None:
        """Write ``bundle.json`` for a bundle."""

        atomic_write_json(
            self.bundle_meta_path(series_key, year, subject),
            {
                "schema_version": BUNDLE_SCHEMA_VERSION,
                "bundle": bundle_key(series_key, year, subject),
                "series_key": series_key,
                "series_name": display_name,
                "year": year,
                "subject": subject,
            },
        )

    # --- papers ------------------------------------------------------------

    def read_paper(self, series_key: str, year: int, subject: str, paper_no: int) -> PaperRecord:
        path = self.paper_path(series_key, year, subject, paper_no)
        if not path.is_file():
            raise NotFoundError(f"paper not found: {series_key}/{year}/{subject}/{paper_no}")
        record = read_paper_document(path)
        name = self._bundle_display_name(series_key, year, subject)
        if name:
            record = PaperRecord(record.series_key, record.year, record.subject, record.paper_no, record.questions, name)
        return record

    def read_paper_summary(self, series_key: str, year: int, subject: str, paper_no: int) -> dict[str, Any]:
        """Return one paper's summary without validating the full TeX payload."""

        path = self.paper_path(series_key, year, subject, paper_no)
        if not path.is_file():
            raise NotFoundError(f"paper not found: {series_key}/{year}/{subject}/{paper_no}")
        return self._summary_from_document(path, self._bundle_ref(series_key, year, subject))

    def has_paper(self, series_key: str, year: int, subject: str, paper_no: int) -> bool:
        return self.paper_path(series_key, year, subject, paper_no).is_file()

    def write_paper(self, record: PaperRecord, *, replace: bool = False, series_name: str | None = None) -> str:
        """Write one paper atomically.

        Questions are normalized through the schema-3.0 model first so the bytes
        written are exactly the bytes that will be read back (empty figure arrays
        dropped, key order fixed, question order sorted). Without this, the stored
        ``content_hash`` could disagree with a later re-read.

        Refuses to overwrite an existing paper unless ``replace`` is explicit, so a
        re-extraction cannot silently clobber a reviewed record.
        """

        normalized = normalize_questions(
            record.questions, context=f"{record.natural_key}.questions"
        )
        record = PaperRecord(
            record.series_key,
            record.year,
            record.subject,
            record.paper_no,
            normalized,
            record.series_name,
        )
        path = self.paper_path(record.series_key, record.year, record.subject, record.paper_no)
        operation = "added"
        if path.exists():
            if not replace:
                raise ConflictError(f"paper already exists: {record.natural_key}; pass replace=True after review")
            operation = "replaced"
        if series_name:
            self.write_bundle_meta(record.series_key, record.year, record.subject, series_name)
        elif not self.bundle_meta_path(record.series_key, record.year, record.subject).exists():
            self.write_bundle_meta(record.series_key, record.year, record.subject, record.series_key)
        write_document(path, record.document())
        # The index no longer reflects the on-disk papers. Track the write count so a
        # later read rebuilds it instead of serving stale counts.
        with self._state_lock:
            self._written_since_index += 1
        return operation

    def delete_paper(self, series_key: str, year: int, subject: str, paper_no: int) -> bool:
        """Delete one paper; returns whether a file was removed."""

        path = self.paper_path(series_key, year, subject, paper_no)
        if path.is_file():
            path.unlink()
            with self._state_lock:
                self._written_since_index += 1
            return True
        return False

    def iter_records(self) -> Iterable[PaperRecord]:
        """Yield every stored paper in stable order."""

        for bundle in self.list_bundles():
            for path in bundle.paper_paths:
                yield read_paper_document(path)

    def list_summaries(
        self,
        *,
        series_keys: Sequence[str] | None = None,
        years: Sequence[int] | None = None,
        subjects: Sequence[str] | None = None,
        paper_nos: Sequence[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Return filtered paper summaries.

        Summaries come from the derived index when it is usable, because parsing every
        paper document on each request costs seconds at library scale. The index is
        trusted only when it declares the same number of files that exist on disk;
        otherwise it is rebuilt from the documents. Any doubt falls back to reading
        the documents, so a stale index can never change the reported data.
        """

        wanted_series = set(series_keys) if series_keys else None
        wanted_years = set(int(year) for year in years) if years else None
        wanted_subjects = set(subjects) if subjects else None
        wanted_papers = set(int(value) for value in paper_nos) if paper_nos else None

        summaries = self._indexed_summaries()
        if summaries is None:
            summaries = self._scan_summaries()

        selected: list[dict[str, Any]] = []
        for item in summaries:
            if wanted_series is not None and item.get("series_key") not in wanted_series:
                continue
            if wanted_years is not None and item.get("year") not in wanted_years:
                continue
            if wanted_subjects is not None and item.get("subject") not in wanted_subjects:
                continue
            if wanted_papers is not None and item.get("paper_no") not in wanted_papers:
                continue
            selected.append(item)
        selected.sort(key=lambda entry: (entry["series_key"], entry["year"], entry["subject"], entry["paper_no"]))
        return selected

    def _paper_file_count(self) -> int:
        """Count the paper documents currently on disk."""

        count = 0
        for bundle in self.list_bundles():
            count += len(bundle.paper_paths)
        return count

    def _indexed_summaries(self) -> list[dict[str, Any]] | None:
        """Return summaries from the in-process cache or the derived index.

        Order of trust:

        1. in-process cache, valid only while no write happened in this process;
        2. ``index/papers.json``, valid only when its paper count matches the files
           on disk, which catches a write performed by another process;
        3. ``None``, so the caller reads the documents directly.

        A stale index can therefore never change reported data; it only costs a
        fallback scan.
        """

        if self._written_since_index == 0 and self._summary_cache is not None:
            return list(self._summary_cache[1])

        with self._state_lock:
            if self._written_since_index == 0 and self._summary_cache is not None:
                return list(self._summary_cache[1])

        file_count = self._paper_file_count()
        if self._written_since_index == 0 and self._summary_cache is not None and self._summary_cache[0] == file_count:
            return list(self._summary_cache[1])

        index_path = self.paths.index / "papers.json"
        if not index_path.is_file():
            return None
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        papers = payload.get("papers")
        if not isinstance(papers, list):
            return None
        if int(payload.get("paper_count", -1)) != file_count:
            return None
        for item in papers:
            if not isinstance(item, dict) or "natural_key" not in item:
                return None
        summaries = [dict(item) for item in papers]
        with self._state_lock:
            self._summary_cache = (file_count, summaries)
            self._written_since_index = 0
        return list(summaries)

    def _scan_summaries(self) -> list[dict[str, Any]]:
        """Read every paper document and build summaries."""

        summaries: list[dict[str, Any]] = []
        for bundle in self.list_bundles():
            for path in bundle.paper_paths:
                summaries.append(self._summary_from_document(path, bundle))
        return summaries

    def invalidate_index(self) -> None:
        """Drop the derived index so the next read rebuilds from documents.

        Called after any write whose index rebuild is deferred, so a stale index can
        never be served.
        """

        index_path = self.paths.index / "papers.json"
        if index_path.is_file():
            index_path.unlink()
        with self._state_lock:
            self._summary_cache = None
            self._written_since_index += 1

    # --- index and release -------------------------------------------------

    def rebuild_index(self) -> dict[str, Any]:
        """Rebuild ``index/papers.json`` and ``index/bundles.json`` from papers.

        Always reads the documents directly, never the previous index, so a rebuild
        reflects the current files even when the index is missing or stale.
        """

        summaries = self._scan_summaries()
        summaries.sort(key=lambda entry: (entry["series_key"], entry["year"], entry["subject"], entry["paper_no"]))
        bundles = [
            {
                "bundle": bundle.key,
                "series_key": bundle.series_key,
                "series_name": bundle.display_name or bundle.series_key,
                "year": bundle.year,
                "subject": bundle.subject,
                "paper_count": bundle.paper_count,
            }
            for bundle in self.list_bundles()
        ]
        atomic_write_json(
            self.paths.index / "papers.json",
            {"schema_version": INDEX_SCHEMA_VERSION, "paper_count": len(summaries), "papers": summaries},
        )
        atomic_write_json(
            self.paths.index / "bundles.json",
            {"schema_version": INDEX_SCHEMA_VERSION, "bundle_count": len(bundles), "bundles": bundles},
        )
        # The freshly written index is now authoritative; refresh the cache so the
        # next read is served without re-scanning.
        with self._state_lock:
            self._summary_cache = (len(summaries), summaries)
            self._written_since_index = 0
        return {"paper_count": len(summaries), "bundle_count": len(bundles)}

    def build_release(self) -> dict[str, Any]:
        """Compute the release manifest from the current paper files."""

        from npee_math_papers.core.release import build_release_manifest

        return build_release_manifest(self.list_summaries())

    def write_release(self) -> dict[str, Any]:
        """Build and persist the release manifest, then return it."""

        manifest = self.build_release()
        atomic_write_json(self.paths.release, manifest)
        return manifest

    def content_hash_lookup(self) -> dict[str, str]:
        """Return ``natural_key -> content_hash`` for every paper.

        Served from the summaries projection, whose ``content_hash`` is recorded at
        write time, so binding verification does not re-read every document.
        """

        return {
            str(item["natural_key"]): str(item.get("content_hash") or "")
            for item in self.list_summaries()
        }

    def raw_document(self, series_key: str, year: int, subject: str, paper_no: int) -> dict[str, Any]:
        """Return the on-disk document as plain JSON-compatible data."""

        path = self.paper_path(series_key, year, subject, paper_no)
        if not path.is_file():
            raise NotFoundError(f"paper not found: {series_key}/{year}/{subject}/{paper_no}")
        return dump_json_compatible(read_document(path))

    def stats(self) -> dict[str, Any]:
        """Return aggregate counts for dashboards and MCP metadata."""

        summaries = self.list_summaries()
        return {
            "bundles": len(self.list_bundles()),
            "papers": len(summaries),
            "questions": sum(item["question_count"] for item in summaries),
            "figures": sum(item.get("figure_count", 0) for item in summaries),
            "series": sorted({item["series_key"] for item in summaries}),
            "years": sorted({item["year"] for item in summaries}),
            "subjects": sorted({item["subject"] for item in summaries}),
        }

    # --- helpers -----------------------------------------------------------

    def _bundle_ref(self, series_key: str, year: int, subject: str) -> BundleRef:
        key = bundle_key(series_key, year, subject)
        return BundleRef(key, series_key, year, subject, self.paths.papers / key, self._bundle_display_name(series_key, year, subject))

    def _bundle_display_name(self, series_key: str, year: int, subject: str) -> str:
        meta_path = self.bundle_meta_path(series_key, year, subject)
        if not meta_path.is_file():
            return ""
        try:
            return str(json.loads(meta_path.read_text(encoding="utf-8")).get("series_name") or "")
        except (json.JSONDecodeError, AttributeError):
            return ""

    def _summary_from_document(self, path: Path, bundle: BundleRef) -> dict[str, Any]:
        payload = read_document(path)
        meta = payload.get("paper") or {}
        questions = payload.get("questions") or []
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
        series_key = str(meta.get("series_key", bundle.series_key))
        year = int(meta.get("year", bundle.year))
        subject = str(meta.get("subject", bundle.subject))
        paper_no = int(meta.get("paper_no", _paper_number(path)))
        return {
            "natural_key": natural_key(year, subject, series_key, paper_no),
            "bundle": bundle_key(series_key, year, subject),
            "series_key": series_key,
            "series_name": bundle.display_name or series_key,
            "year": year,
            "subject": subject,
            "paper_no": paper_no,
            "question_count": len(questions),
            "section_counts": counts,
            "figure_count": figure_count,
            "content_hash": str(payload.get("content_hash") or ""),
        }


def _paper_number(path: Path) -> int:
    try:
        return int(path.stem)
    except ValueError as error:
        raise ValidationError(f"{path.as_posix()} must be named <paper_no>{PAPER_EXTENSION}") from error


def _paper_sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    try:
        return (int(stem), stem)
    except ValueError:
        return (0, stem)
