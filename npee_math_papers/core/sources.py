"""Sources and captures: PDF provenance and page evidence.

Layer model
-----------
- **series** : a publisher collection, e.g. ``zhangyu8``
- **paper**  : one exam paper, identified by ``series + year + subject + paper_no``
- **bundle** : the directory grouping all papers of one ``series + year + subject``
- **source** : at most one PDF per bundle, stored at ``sources/<bundle>/source.pdf``
- **capture**: one page-splitting batch inside a bundle, holding the PNG pages that
  one extraction run was allowed to read

Design rules
------------
1. No public function accepts an arbitrary path. Callers pass ``series``/``year``/
   ``subject`` and the store derives and contains the path itself. This removes the
   path-injection surface a ``create(source_path=...)`` API would introduce.
2. A capture records its page boundaries so an extraction run always knows exactly
   which pages are question evidence versus answer/cover pages.
3. Evidence files are never rewritten in place; a new capture is a new directory.

Evidence is large (hundreds of MB per source) and reproducible, so ``.npee-math-papers/sources``
and ``.npee-math-papers/captures`` are git-ignored while the papers themselves are committed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from npee_math_papers.core.domain import ID_RE, SUBJECTS
from npee_math_papers.core.errors import NotFoundError, NpeeError, ValidationError
from npee_math_papers.core.release import source_sha256
from npee_math_papers.core.store import NpeePaths, atomic_write_json, bundle_key, parse_bundle_key

CAPTURE_SCHEMA_VERSION = "3.0"
SOURCE_SCHEMA_VERSION = "3.0"
CAPTURE_ID_RE = ID_RE
PDF_SUFFIX = ".pdf"
PAGE_RE = re.compile(r"^p(\d{4})\.png$")


@dataclass(frozen=True)
class SourceRef:
    """A registered source PDF for one bundle."""

    series_key: str
    year: int
    subject: str
    path: Path
    sha256: str
    page_count: int | None = None

    @property
    def bundle(self) -> str:
        return bundle_key(self.series_key, self.year, self.subject)

    def summary(self) -> dict[str, Any]:
        return {
            "bundle": self.bundle,
            "series_key": self.series_key,
            "year": self.year,
            "subject": self.subject,
            "sha256": self.sha256,
            "page_count": self.page_count,
        }


@dataclass(frozen=True)
class CaptureRef:
    """A page-splitting batch for one bundle."""

    series_key: str
    year: int
    subject: str
    capture_id: str
    path: Path
    question_pages: tuple[int, ...] = ()
    answer_pages: tuple[int, ...] = ()
    status: str = "prepared"

    @property
    def bundle(self) -> str:
        return bundle_key(self.series_key, self.year, self.subject)

    @property
    def pages_dir(self) -> Path:
        return self.path / "pages"

    def page_files(self) -> list[Path]:
        if not self.pages_dir.is_dir():
            return []
        return sorted(self.pages_dir.glob("p*.png"))

    def summary(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "bundle": self.bundle,
            "series_key": self.series_key,
            "year": self.year,
            "subject": self.subject,
            "question_pages": list(self.question_pages),
            "answer_pages": list(self.answer_pages),
            "page_count": len(self.page_files()),
            "status": self.status,
        }


def _validate_subject(subject: str) -> None:
    if subject not in SUBJECTS:
        raise ValidationError(f"subject must be one of {', '.join(SUBJECTS)}")


def validate_capture_id(capture_id: str) -> str:
    """Validate a capture id (lowercase ASCII, e.g. ``unit-01`` or ``first-pass``)."""

    if not CAPTURE_ID_RE.fullmatch(capture_id or ""):
        raise ValidationError("capture_id must be a lowercase ASCII id such as 'unit-01'")
    return capture_id


class SourceManager:
    """Manage source PDFs under ``.npee-math-papers/sources``."""

    def __init__(self, paths: NpeePaths) -> None:
        self.paths = paths

    def source_dir(self, series_key: str, year: int, subject: str) -> Path:
        _validate_subject(subject)
        return self.paths.sources / bundle_key(series_key, year, subject)

    def source_path(self, series_key: str, year: int, subject: str) -> Path:
        return self.source_dir(series_key, year, subject) / f"source{PDF_SUFFIX}"

    def source_meta_path(self, series_key: str, year: int, subject: str) -> Path:
        return self.source_dir(series_key, year, subject) / "source.json"

    def register(
        self,
        series_key: str,
        year: int,
        subject: str,
        pdf_path: Path,
        *,
        source_id: str | None = None,
        page_count: int | None = None,
        notes: str | None = None,
        move: bool = False,
    ) -> SourceRef:
        """Register ``pdf_path`` as the source PDF for a bundle.

        ``pdf_path`` is resolved and validated as an existing file, then placed at
        the fixed location ``sources/<bundle>/source.pdf``. A re-registration
        replaces the previous PDF and rewrites ``source.json``; callers that need an
        audit trail should pass distinct bundles or an explicit ``source_id``.
        """

        _validate_subject(subject)
        resolved = Path(pdf_path).resolve()
        if not resolved.is_file():
            raise ValidationError(f"source PDF does not exist: {resolved.as_posix()}")
        if resolved.suffix.lower() != PDF_SUFFIX:
            raise ValidationError("source must be a .pdf file")
        target = self.source_path(series_key, year, subject)
        target.parent.mkdir(parents=True, exist_ok=True)
        if move:
            if target.exists():
                target.unlink()
            shutil.move(str(resolved), str(target))
        elif resolved != target:
            shutil.copy2(resolved, target)
        digest = source_sha256(target)
        page_count = page_count if page_count is not None else _pdf_page_count(target)
        atomic_write_json(
            self.source_meta_path(series_key, year, subject),
            {
                "schema_version": SOURCE_SCHEMA_VERSION,
                "bundle": bundle_key(series_key, year, subject),
                "series_key": series_key,
                "year": year,
                "subject": subject,
                "source_id": source_id,
                "sha256": digest,
                "page_count": page_count,
                "notes": notes,
            },
        )
        return SourceRef(series_key, year, subject, target, digest, page_count)

    def get(self, series_key: str, year: int, subject: str) -> SourceRef:
        path = self.source_path(series_key, year, subject)
        if not path.is_file():
            raise ValidationError(f"no source PDF registered for {bundle_key(series_key, year, subject)}")
        meta_path = self.source_meta_path(series_key, year, subject)
        meta: Mapping[str, Any] = {}
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return SourceRef(
            series_key,
            year,
            subject,
            path,
            str(meta.get("sha256") or source_sha256(path)),
            meta.get("page_count"),
        )

    def list_sources(self) -> list[SourceRef]:
        refs: list[SourceRef] = []
        if not self.paths.sources.is_dir():
            return refs
        for directory in sorted(item for item in self.paths.sources.iterdir() if item.is_dir()):
            try:
                series_key, year, subject = parse_bundle_key(directory.name)
            except ValidationError:
                continue
            pdf = directory / f"source{PDF_SUFFIX}"
            if not pdf.is_file():
                continue
            refs.append(self.get(series_key, year, subject))
        return refs

    def delete(self, series_key: str, year: int, subject: str) -> bool:
        """Delete a bundle's source directory; returns whether it existed."""

        directory = self.source_dir(series_key, year, subject)
        if directory.is_dir():
            shutil.rmtree(directory)
            return True
        return False


class CaptureManager:
    """Manage page captures under ``.npee-math-papers/captures``."""

    def __init__(self, paths: NpeePaths) -> None:
        self.paths = paths

    def capture_dir(self, series_key: str, year: int, subject: str, capture_id: str) -> Path:
        _validate_subject(subject)
        validate_capture_id(capture_id)
        return self.paths.captures / bundle_key(series_key, year, subject) / capture_id

    def capture_meta_path(self, series_key: str, year: int, subject: str, capture_id: str) -> Path:
        return self.capture_dir(series_key, year, subject, capture_id) / "capture.json"

    def prepare(
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
    ) -> CaptureRef:
        """Create an empty capture with explicit page boundaries.

        The boundaries are mandatory: an extraction run must be told which pages are
        question evidence. Overlapping or duplicated page sets are rejected so the
        capture never silently contains answer or cover pages.
        """

        _validate_subject(subject)
        validate_capture_id(capture_id)
        question = _clean_pages(question_pages, "question_pages")
        answer = _clean_pages(answer_pages, "answer_pages")
        exclude = _clean_pages(exclude_pages, "exclude_pages")
        if not question:
            raise ValidationError("question_pages must list at least one page")
        overlap = (set(question) & set(answer)) | (set(question) & set(exclude)) | (set(answer) & set(exclude))
        if overlap:
            raise ValidationError(f"page sets must not overlap: {sorted(overlap)}")
        directory = self.capture_dir(series_key, year, subject, capture_id)
        (directory / "pages").mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            self.capture_meta_path(series_key, year, subject, capture_id),
            {
                "schema_version": CAPTURE_SCHEMA_VERSION,
                "capture_id": capture_id,
                "bundle": bundle_key(series_key, year, subject),
                "series_key": series_key,
                "year": year,
                "subject": subject,
                "source_id": source_id,
                "question_pages": list(question),
                "answer_pages": list(answer),
                "exclude_pages": list(exclude),
                "status": "prepared",
                "notes": notes,
            },
        )
        return CaptureRef(series_key, year, subject, capture_id, directory, tuple(question), tuple(answer), "prepared")

    def add_page(self, series_key: str, year: int, subject: str, capture_id: str, page_number: int, png_path: Path) -> Path:
        """Place one rendered page into a capture.

        The page number must be within the capture's declared question pages, so a
        misplaced page is caught at write time rather than discovered during review.
        """

        ref = self.get(series_key, year, subject, capture_id)
        if page_number not in ref.question_pages:
            raise ValidationError(
                f"page {page_number} is not in question_pages {list(ref.question_pages)} for {capture_id}"
            )
        source = Path(png_path).resolve()
        if not source.is_file():
            raise ValidationError(f"page image does not exist: {source.as_posix()}")
        if source.suffix.lower() != ".png":
            raise ValidationError("page evidence must be a .png file")
        target = ref.pages_dir / f"p{page_number:04d}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target

    def get(self, series_key: str, year: int, subject: str, capture_id: str) -> CaptureRef:
        directory = self.capture_dir(series_key, year, subject, capture_id)
        meta_path = directory / "capture.json"
        if not meta_path.is_file():
            raise NotFoundError(
                f"capture not found: {bundle_key(series_key, year, subject)}/{capture_id}"
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return CaptureRef(
            series_key,
            year,
            subject,
            capture_id,
            directory,
            tuple(int(value) for value in meta.get("question_pages", [])),
            tuple(int(value) for value in meta.get("answer_pages", [])),
            str(meta.get("status", "prepared")),
        )

    def list_captures(self, series_key: str | None = None, year: int | None = None, subject: str | None = None) -> list[CaptureRef]:
        refs: list[CaptureRef] = []
        if not self.paths.captures.is_dir():
            return refs
        for bucket in sorted(item for item in self.paths.captures.iterdir() if item.is_dir()):
            try:
                bucket_series, bucket_year, bucket_subject = parse_bundle_key(bucket.name)
            except ValidationError:
                continue
            if series_key and bucket_series != series_key:
                continue
            if year is not None and bucket_year != year:
                continue
            if subject and bucket_subject != subject:
                continue
            for directory in sorted(item for item in bucket.iterdir() if item.is_dir()):
                if not (directory / "capture.json").is_file():
                    continue
                refs.append(self.get(bucket_series, bucket_year, bucket_subject, directory.name))
        return refs

    def set_status(self, series_key: str, year: int, subject: str, capture_id: str, status: str) -> None:
        """Update a capture's lifecycle status."""

        meta_path = self.capture_meta_path(series_key, year, subject, capture_id)
        if not meta_path.is_file():
            raise NotFoundError(f"capture not found: {capture_id}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = status
        atomic_write_json(meta_path, meta)

    def delete(self, series_key: str, year: int, subject: str, capture_id: str) -> bool:
        """Delete a capture directory; returns whether it existed."""

        directory = self.capture_dir(series_key, year, subject, capture_id)
        if directory.is_dir():
            shutil.rmtree(directory)
            return True
        return False


def _clean_pages(pages: Sequence[int], field: str) -> list[int]:
    cleaned: list[int] = []
    for value in pages:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValidationError(f"{field} must contain positive integers")
        if value not in cleaned:
            cleaned.append(value)
    return sorted(cleaned)


def _pdf_page_count(path: Path) -> int | None:
    """Return the PDF page count using a tiny dependency-free scan.

    Counts ``/Type /Page`` occurrences, which is accurate for the linearized,
    uncompressed page trees produced by the exam PDFs in this repository. Returns
    ``None`` when the structure cannot be determined, rather than guessing.
    """

    try:
        data = path.read_bytes()
    except OSError:
        return None
    matches = re.findall(rb"/Type\s*/Page(?![s])", data)
    if not matches:
        return None
    return len(matches)


def page_number_from_name(name: str) -> int | None:
    """Return the page number encoded in a ``p####.png`` name, else ``None``."""

    match = PAGE_RE.match(name)
    return int(match.group(1)) if match else None


def link_or_copy(source: Path, target: Path, *, hardlink: bool = False) -> None:
    """Copy a file, optionally hardlinking first when possible."""

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    if hardlink:
        try:
            os.link(source, target)
            return
        except OSError:
            pass
    shutil.copy2(source, target)
