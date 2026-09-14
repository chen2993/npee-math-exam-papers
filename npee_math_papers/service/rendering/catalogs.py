"""Resolving a composition's papers from the paper store.

Questions are read from `.npee-math-papers` (the only source of truth) and
converted to the builder's render model here, so the rest of the builder consumes
one stable shape regardless of the storage schema.
"""

from __future__ import annotations

import json
from typing import Any

from npee_math_papers.core.domain import ID_RE
from npee_math_papers.core.render_model import to_render_questions
from npee_math_papers.core.store import NpeePaths, PaperStore
from npee_math_papers.service.rendering.errors import fail
from npee_math_papers.service.rendering.paths import ROOT
from npee_math_papers.service.rendering.text import require_keys
from npee_math_papers.service.rendering.validation import validate_questions

def _store_for_build() -> PaperStore | None:
    """Return the `.npee-math-papers` store when a data root with papers exists, else ``None``."""

    paths = NpeePaths.resolve(repository_root=ROOT)
    if paths.papers.is_dir() and any(paths.papers.iterdir()):
        return PaperStore(paths)
    return None


def _load_store_catalogs(
    store: PaperStore,
    source_specs: list[tuple[str, str, str]],
) -> tuple[dict[str, str], dict[tuple[int, str, str, int], list[dict[str, Any]]]]:
    """Load series names and questions from the `.npee-math-papers` paper store.

    Questions are converted from schema 3.0 to the builder's render model, so the
    renderer consumes a single stable input shape regardless of the storage format.
    """

    wanted = {source_id for source_id, _, _ in source_specs}
    series: dict[str, str] = {}
    papers: dict[tuple[int, str, str, int], list[dict[str, Any]]] = {}
    summaries = store.list_summaries(series_keys=sorted(wanted) if wanted else None)
    seen_keys: set[tuple[int, str, str, int]] = set()
    for summary in summaries:
        key = (summary["year"], summary["subject"], summary["series_key"], summary["paper_no"])
        if key in seen_keys:
            fail(f"Duplicate paper identity in store: {key}")
        seen_keys.add(key)
        record = store.read_paper(summary["series_key"], summary["year"], summary["subject"], summary["paper_no"])
        render_questions = to_render_questions(record.questions)
        clean = validate_questions(render_questions, f"store {record.natural_key}")
        fingerprint = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        series.setdefault(record.series_key, summary.get("series_name") or record.series_key)
        papers[key] = [
            {
                "catalog_id": record.series_key,
                "questions": clean,
                "fingerprint": fingerprint,
                "content_hash": record.content_hash,
            }
        ]
    if not papers:
        fail("the .npee-math-papers paper store contains no papers for the requested series")
    return series, papers


def derive_year(composition: dict[str, Any]) -> int | None:
    """Return the latest paper year referenced by a composition, if any.

    Used as a fallback when ``metadata.year`` is absent, which schema-3.0
    compositions omit because the year is a property of the papers, not the book.
    """

    years: list[int] = []
    groups = composition.get("groups")
    if not isinstance(groups, list):
        return None
    for group in groups:
        if not isinstance(group, dict):
            continue
        for paper in group.get("papers") or []:
            if isinstance(paper, dict) and isinstance(paper.get("year"), int):
                years.append(paper["year"])
    return max(years) if years else None


def load_catalogs(
    document: dict[str, Any],
    *,
    store: "PaperStore | None" = None,
) -> tuple[dict[str, str], dict[tuple[int, str, str, int], list[dict[str, Any]]]]:
    """Resolve the series catalog and every referenced paper's questions.

    ``store`` is the caller's already-wired paper store. Passing it explicitly
    keeps the builder bound to the same data root as the ``NpeeService`` that
    invoked it; only the CLI path omits it and falls back to the default root.
    """

    catalog = document.get("catalog")
    if not isinstance(catalog, dict):
        fail("catalog must be an object")
    if "sources" in catalog:
        require_keys(catalog, {"sources"}, "catalog")
        raw_sources = catalog["sources"]
        if not isinstance(raw_sources, list) or not raw_sources:
            fail("catalog.sources must be a non-empty array")
        source_specs: list[tuple[str, str, str]] = []
        seen_source_ids: set[str] = set()
        for index, source in enumerate(raw_sources):
            field = f"catalog.sources[{index}]"
            if not isinstance(source, dict):
                fail(f"{field} must be an object")
            require_keys(source, {"id"}, field)
            source_id = source["id"]
            if not isinstance(source_id, str) or not ID_RE.fullmatch(source_id) or source_id in seen_source_ids:
                fail(f"{field}.id is invalid or duplicated")
            seen_source_ids.add(source_id)
            source_specs.append((source_id, "", ""))
    elif "store" in catalog:
        # Explicit store-only mode: read every series from the .npee-math-papers paper store.
        require_keys(catalog, {"store"}, "catalog")
        store_sources = catalog["store"]
        if not isinstance(store_sources, list) or not store_sources:
            fail("catalog.store must be a non-empty array")
        source_specs = []
        for index, source_id in enumerate(store_sources):
            if not isinstance(source_id, str) or not ID_RE.fullmatch(source_id):
                fail(f"catalog.store[{index}] must be a series id")
            source_specs.append((source_id, "", ""))
    else:
        require_keys(catalog, {"series", "papers"}, "catalog")
        source_specs = [("default", catalog["series"], catalog["papers"])]

    # The `.npee-math-papers` store is the only source of truth for question content.
    resolved_store = store if store is not None else _store_for_build()
    if resolved_store is None:
        fail(
            "the paper store is empty or missing; populate .npee-math-papers/papers/ "
            "with the MCP tool npee_ingest_paper"
        )
    return _load_store_catalogs(resolved_store, source_specs)


def resolve_catalog_paper(
    papers: dict[tuple[int, str, str, int], list[dict[str, Any]]],
    key: tuple[int, str, str, int],
    catalog_id: str | None,
    field: str,
) -> list[dict[str, Any]]:
    records = papers.get(key)
    if not records:
        fail(f"Paper reference not found in registered catalogs: {key}")
    if catalog_id is not None:
        matches = [record for record in records if record["catalog_id"] == catalog_id]
        if not matches:
            fail(f"{field}.catalog_id does not contain paper reference: {catalog_id}")
        return matches[0]["questions"]
    fingerprints = {record["fingerprint"] for record in records}
    if len(fingerprints) > 1:
        fail(f"Conflicting paper records require catalog_id: {key}")
    return records[0]["questions"]
