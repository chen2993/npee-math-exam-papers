"""Composition model and validation.

A composition references papers by natural key and records the ``content_hash``
each reference was authored against. Validation here is shared by the builder, the
service layer, the HTTP API and the MCP server, so a composition that validates in
one surface is accepted by all of them.

Rendering lives in ``python -m npee_math_papers.service.tex_builder``; this module owns only the
contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from npee_math_papers.core.canonical import natural_key
from npee_math_papers.core.domain import (
    HOOK_PHASES,
    ID_RE,
    LAYOUTS,
    SOLUTION_STRUCTURES,
    SPACINGS,
    SUBJECTS,
    SUBJECT_LABELS,
    SUBJECT_TEMPLATE,
    THEMES,
)
from npee_math_papers.core.errors import ValidationError
from npee_math_papers.core.release import ReleaseManifest

COMPOSITION_SCHEMA_VERSION = "3.0"


def fail(message: str) -> None:
    raise ValidationError(message)


def _require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        fail(f"{context} must be an object")
    return value


@dataclass(frozen=True)
class PaperRef:
    """A reference to one paper, optionally pinned to a content hash."""

    year: int
    subject: str
    series_key: str
    paper_no: int
    content_hash: str | None = None
    catalog_id: str | None = None
    bookmark_title: str | None = None
    display_title: str | None = None

    @property
    def natural_key(self) -> str:
        return natural_key(self.year, self.subject, self.series_key, self.paper_no)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "year": self.year,
            "subject": self.subject,
            "series_key": self.series_key,
            "paper_no": self.paper_no,
        }
        if self.content_hash:
            payload["content_hash"] = self.content_hash
        if self.catalog_id:
            payload["catalog_id"] = self.catalog_id
        if self.bookmark_title:
            payload["bookmark_title"] = self.bookmark_title
        if self.display_title is not None:
            payload["display_title"] = self.display_title
        return payload


def parse_paper_ref(value: Any, context: str) -> PaperRef:
    """Validate and return one paper reference.

    ``subject`` may be the literal ``$subject`` template marker, which the builder
    expands per subject variant.
    """

    raw = _require_mapping(value, context)
    allowed = {"year", "subject", "series_key", "paper_no", "content_hash", "catalog_id", "bookmark_title", "display_title"}
    required = {"year", "subject", "series_key", "paper_no"}
    missing = sorted(required - set(raw))
    if missing:
        fail(f"{context} is missing fields: {', '.join(missing)}")
    extra = sorted(set(raw) - allowed)
    if extra:
        fail(f"{context} has unsupported fields: {', '.join(extra)}")
    year = raw["year"]
    if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 2200:
        fail(f"{context}.year is invalid")
    subject = raw["subject"]
    if subject != SUBJECT_TEMPLATE and subject not in SUBJECTS:
        fail(f"{context}.subject is invalid")
    series_key = raw["series_key"]
    if not isinstance(series_key, str) or not ID_RE.fullmatch(series_key):
        fail(f"{context}.series_key is invalid")
    paper_no = raw["paper_no"]
    if isinstance(paper_no, bool) or not isinstance(paper_no, int) or paper_no < 1:
        fail(f"{context}.paper_no is invalid")
    content_hash_value = raw.get("content_hash")
    if content_hash_value is not None:
        if not isinstance(content_hash_value, str) or not re.fullmatch(r"[0-9a-f]{64}", content_hash_value):
            fail(f"{context}.content_hash must be a 64-character lowercase hex digest")
    catalog_id = raw.get("catalog_id")
    if catalog_id is not None and (not isinstance(catalog_id, str) or not ID_RE.fullmatch(catalog_id)):
        fail(f"{context}.catalog_id is invalid")
    bookmark_title = raw.get("bookmark_title")
    if bookmark_title is not None and not str(bookmark_title).strip():
        fail(f"{context}.bookmark_title must be a non-empty string when present")
    display_title = raw.get("display_title")
    return PaperRef(
        year=year,
        subject=str(subject),
        series_key=series_key,
        paper_no=paper_no,
        content_hash=content_hash_value,
        catalog_id=catalog_id,
        bookmark_title=str(bookmark_title) if bookmark_title else None,
        display_title=None if display_title is None else str(display_title),
    )


@dataclass
class Group:
    """A named group of papers."""

    id: str
    title: str
    order_index: int
    papers: list[PaperRef] = field(default_factory=list)


@dataclass
class CompositionSpec:
    """A validated composition."""

    composition_id: str
    title: str
    groups: list[Group]
    raw: dict[str, Any]
    source_ids: list[str] = field(default_factory=list)
    release_id: str | None = None

    @property
    def papers(self) -> list[PaperRef]:
        return [paper for group in self.groups for paper in group.papers]

    @property
    def target_subjects(self) -> list[str]:
        seen: list[str] = []
        for paper in self.papers:
            if paper.subject != SUBJECT_TEMPLATE and paper.subject not in seen:
                seen.append(paper.subject)
        return seen

    def to_dict(self) -> dict[str, Any]:
        return dict(self.raw)


def _parse_groups(raw: Any) -> list[Group]:
    if not isinstance(raw, list) or not raw:
        fail("groups must be a non-empty array")
    groups: list[Group] = []
    seen_ids: set[str] = set()
    seen_order: set[int] = set()
    for index, item in enumerate(raw):
        mapping = _require_mapping(item, f"groups[{index}]")
        group_id = str(mapping.get("id") or "")
        if not ID_RE.fullmatch(group_id):
            fail(f"groups[{index}].id is invalid")
        if group_id in seen_ids:
            fail(f"groups[{index}].id {group_id!r} is duplicated")
        seen_ids.add(group_id)
        order_index = mapping.get("order_index")
        if isinstance(order_index, bool) or not isinstance(order_index, int) or order_index < 1:
            fail(f"groups[{index}].order_index is invalid")
        seen_order.add(order_index)
        title = str(mapping.get("title") or "").strip()
        if not title:
            fail(f"groups[{index}].title must be non-empty")
        papers_raw = mapping.get("papers")
        if not isinstance(papers_raw, list) or not papers_raw:
            fail(f"groups[{index}].papers must be a non-empty array")
        papers = [parse_paper_ref(paper, f"groups[{index}].papers[{paper_index}]") for paper_index, paper in enumerate(papers_raw)]
        groups.append(Group(id=group_id, title=title, order_index=order_index, papers=papers))
    return groups


def parse_composition(value: Mapping[str, Any]) -> CompositionSpec:
    """Validate a composition document and return its spec.

    Accepts both the compact ``groups`` form and the older single-group shorthand,
    and enforces cross-field rules such as unique group ids and ordering.
    """

    raw = dict(_require_mapping(value, "composition"))
    schema = raw.get("schema_version")
    if schema not in {COMPOSITION_SCHEMA_VERSION, "2.0"}:
        fail(f"composition.schema_version must be {COMPOSITION_SCHEMA_VERSION!r}")
    composition_id = str(raw.get("composition_id") or "")
    if not ID_RE.fullmatch(composition_id):
        fail("composition.composition_id must be a lowercase ASCII id")
    metadata = _require_mapping(raw.get("metadata"), "composition.metadata")
    title = str(metadata.get("title") or "").strip()
    if not title:
        fail("composition.metadata.title must be non-empty")
    release_id = metadata.get("release_id")
    if release_id is not None and not isinstance(release_id, str):
        fail("composition.metadata.release_id must be a string when present")
    groups = _parse_groups(raw.get("groups"))
    catalog = raw.get("catalog")
    source_ids: list[str] = []
    if isinstance(catalog, Mapping):
        sources = catalog.get("sources")
        if isinstance(sources, list):
            for index, source in enumerate(sources):
                mapping = _require_mapping(source, f"catalog.sources[{index}]")
                source_id = str(mapping.get("id") or "")
                if not ID_RE.fullmatch(source_id):
                    fail(f"catalog.sources[{index}].id is invalid")
                if source_id not in source_ids:
                    source_ids.append(source_id)
    return CompositionSpec(
        composition_id=composition_id,
        title=title,
        groups=groups,
        raw=raw,
        source_ids=source_ids,
        release_id=str(release_id) if release_id else None,
    )


def load_composition(path: Path) -> CompositionSpec:
    """Read and validate a composition JSON file."""

    if not path.is_file():
        fail(f"composition file is missing: {path.as_posix()}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"composition is not valid JSON: {error.msg}")
    if not isinstance(payload, Mapping):
        fail("composition must be a JSON object")
    return parse_composition(payload)


def verify_bindings(
    spec: CompositionSpec,
    lookup: Mapping[str, str],
) -> dict[str, Any]:
    """Check every paper reference against ``natural_key -> content_hash``.

    A reference without a pinned hash is allowed (it binds to whatever is current)
    but is reported as ``unpinned`` so callers can require pinning when they need
    strict reproducibility.
    """

    resolved: list[str] = []
    unpinned: list[str] = []
    missing: list[str] = []
    changed: list[str] = []
    for paper in spec.papers:
        if paper.subject == SUBJECT_TEMPLATE:
            continue
        key = paper.natural_key
        current = lookup.get(key)
        if current is None:
            missing.append(key)
            continue
        resolved.append(key)
        if paper.content_hash is None:
            unpinned.append(key)
        elif paper.content_hash != current:
            changed.append(key)
    return {
        "ok": not missing and not changed,
        "resolved": resolved,
        "missing": missing,
        "changed": changed,
        "unpinned": unpinned,
    }


def verify_against_manifest(spec: CompositionSpec, manifest: ReleaseManifest) -> dict[str, Any]:
    """Verify references against a release manifest instead of live content."""

    return verify_bindings(spec, manifest.papers)


def filter_available(
    spec: CompositionSpec,
    available: Sequence[str],
) -> dict[str, Any]:
    """Return which references are present in ``available`` natural keys."""

    available_set = set(available)
    present: list[str] = []
    absent: list[str] = []
    for paper in spec.papers:
        if paper.subject == SUBJECT_TEMPLATE:
            continue
        (present if paper.natural_key in available_set else absent).append(paper.natural_key)
    return {"present": present, "absent": absent}


def composition_document(
    *,
    composition_id: str,
    title: str,
    groups: Sequence[Group],
    source_ids: Sequence[str],
    document: Mapping[str, Any],
    compile_config: Mapping[str, Any],
    release_id: str | None = None,
) -> dict[str, Any]:
    """Build a canonical composition document from structured inputs.

    The MCP composition tool and the frontend both construct compositions through
    this function, guaranteeing identical output for identical selections.
    """

    metadata: dict[str, Any] = {"title": title, "revision": 1}
    if release_id:
        metadata["release_id"] = release_id
    return {
        "schema_version": COMPOSITION_SCHEMA_VERSION,
        "composition_id": composition_id,
        "metadata": metadata,
        "catalog": {"sources": [{"id": source_id} for source_id in dict.fromkeys(source_ids)]},
        "document": dict(document),
        "groups": [
            {
                "id": group.id,
                "title": group.title,
                "order_index": group.order_index,
                "papers": [paper.to_dict() for paper in group.papers],
            }
            for group in groups
        ],
        "compile": dict(compile_config),
    }
