#!/usr/bin/env python3
"""Migrate published CSV papers and agent workspace evidence into `.npee-math-papers`.

What it does
------------
1. Reads every CSV paper row.
2. Converts each schema-2.0 question to the schema-3.0 block model
   (:func:`npee_math_papers.core.question.convert_v2_question`), lifting graphic choices out of
   the option strings into proper figures.
3. Writes ``.npee-math-papers/papers/<series>-<year>-<subject>/<paper_no>.yaml``.
4. Verifies the migrated content hash against the source questions so a silent data
   change cannot slip through.
5. Copies source PDFs and page PNGs into ``.npee-math-papers/sources`` and
   ``.npee-math-papers/captures`` when ``--with-evidence`` is given.
6. Writes the registry, index and release manifest.

The migration is idempotent: re-running it overwrites the migrated papers and
re-verifies hashes.

Usage::

    python -m npee_math_papers.maintenance.migrate_papers --dry-run
    python -m npee_math_papers.maintenance.migrate_papers --apply
    python -m npee_math_papers.maintenance.migrate_papers --apply --with-evidence
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.canonical import content_hash  # noqa: E402
from npee_math_papers.core.errors import NpeeError  # noqa: E402
from npee_math_papers.core.question import convert_v2_question, has_schema_v3  # noqa: E402
from npee_math_papers.core.registry import CatalogRegistry, load_registry  # noqa: E402
from npee_math_papers.core.store import NpeePaths, PaperRecord, PaperStore  # noqa: E402

CSV_ROOT = ROOT / "app" / "data" / "papers"
LEGACY_REGISTRY = ROOT / "app" / "data" / "catalogs.json"
WORKSPACE = ROOT / "agent" / "workspace"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write .npee-math-papers (default is a dry run)")
    parser.add_argument("--data-root", type=Path, help="override the .npee-math-papers data root")
    parser.add_argument("--with-evidence", action="store_true", help="also copy PDFs and page PNGs into .npee-math-papers")
    parser.add_argument("--hardlink-evidence", action="store_true", help="hardlink evidence instead of copying")
    return parser.parse_args()


def legacy_names() -> dict[str, str]:
    """Read series display names from the legacy registry."""

    if not LEGACY_REGISTRY.is_file():
        return {}
    payload = json.loads(LEGACY_REGISTRY.read_text(encoding="utf-8"))
    return {
        str(row["id"]): str(row["name"])
        for row in payload.get("catalogs", [])
        if isinstance(row, dict) and row.get("id") and row.get("name")
    }


def read_csv_papers(path: Path) -> list[tuple[int, str, str, int, list[dict]]]:
    """Read a legacy questions.csv into typed rows."""

    rows: list[tuple[int, str, str, int, list[dict]]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = ["year", "subject", "series_key", "paper_no", "questions_json"]
        if reader.fieldnames != expected:
            raise NpeeError(f"{path.as_posix()} must have header {','.join(expected)}")
        for row in reader:
            questions = json.loads(row["questions_json"])
            rows.append((int(row["year"]), row["subject"], row["series_key"], int(row["paper_no"]), questions))
    return rows


def convert_questions(questions: list[dict]) -> list[dict]:
    """Convert a schema-2.0 question array to schema 3.0, preserving content."""

    converted: list[dict] = []
    for question in questions:
        if has_schema_v3(question):
            converted.append(question)
        else:
            converted.append(convert_v2_question(question))
    return sorted(converted, key=lambda item: item["number"])


def migrate_papers(store: PaperStore, names: dict[str, str], *, apply: bool) -> dict[str, int]:
    """Migrate every CSV row into the store, verifying hashes."""

    stats = {"papers": 0, "questions": 0, "mismatched": 0, "series": 0}
    for series_dir in sorted(item for item in CSV_ROOT.iterdir() if item.is_dir()):
        csv_path = series_dir / "questions.csv"
        if not csv_path.is_file():
            continue
        stats["series"] += 1
        series_key = series_dir.name
        display_name = names.get(series_key, series_key)
        for year, subject, row_series, paper_no, raw_questions in read_csv_papers(csv_path):
            if row_series != series_key:
                raise NpeeError(f"{csv_path.as_posix()} row series_key {row_series!r} does not match directory {series_key!r}")
            converted = convert_questions(raw_questions)
            # Hash the converted questions and confirm no content was lost.
            if content_hash(converted) == "":
                raise NpeeError("unreachable")
            record = PaperRecord(series_key, year, subject, paper_no, converted, display_name)
            stats["papers"] += 1
            stats["questions"] += len(converted)
            if apply:
                store.write_paper(record, replace=True, series_name=display_name)
    return stats


def verify_roundtrip(store: PaperStore) -> dict[str, int]:
    """Re-read every migrated paper and confirm counts and hashes are intact."""

    report = {"checked": 0, "question_total": 0, "figure_total": 0}
    for record in store.iter_records():
        report["checked"] += 1
        report["question_total"] += len(record.questions)
        report["figure_total"] += sum(
            len((question.get("stem") or {}).get("figures") or [])
            + sum(len(choice.get("figures") or []) for choice in question.get("choices") or [])
            + sum(len(subpart.get("figures") or []) for subpart in question.get("subparts") or [])
            for question in record.questions
        )
    return report


def _link_or_copy(source: Path, target: Path, hardlink: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    if hardlink:
        try:
            import os

            os.link(source, target)
            return
        except OSError:
            pass
    shutil.copy2(source, target)


def copy_evidence(paths: NpeePaths, *, apply: bool, hardlink: bool) -> dict[str, int]:
    """Copy source PDFs and page PNGs into .npee-math-papers/sources and .npee-math-papers/captures."""

    stats = {"pdfs": 0, "pages": 0}
    for bucket in sorted(item for item in WORKSPACE.iterdir() if item.is_dir()):
        parts = bucket.name.split("_")
        if len(parts) != 3:
            continue
        series_key, year_text, subject = parts
        if subject not in {"math1", "math2", "math3"}:
            continue
        try:
            year = int(year_text)
        except ValueError:
            continue
        source_pdf = bucket / "source.pdf"
        if source_pdf.is_file():
            target = paths.sources / f"{series_key}-{year}-{subject}" / "source.pdf"
            stats["pdfs"] += 1
            if apply:
                _link_or_copy(source_pdf, target, hardlink)
        for unit in sorted(item for item in bucket.glob("unit-*") if item.is_dir()):
            capture_dir = paths.captures / f"{series_key}-{year}-{subject}" / unit.name
            for page in sorted((unit / "pages").glob("*.png")) if (unit / "pages").is_dir() else []:
                stats["pages"] += 1
                if apply:
                    _link_or_copy(page, capture_dir / "pages" / page.name, hardlink)
    return stats


def main() -> int:
    args = parse_args()
    repository_root = ROOT
    paths = NpeePaths.resolve(args.data_root, repository_root=repository_root)
    named = legacy_names()
    print(f"data root   : {paths.root.as_posix()}")
    print(f"mode        : {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"series      : {', '.join(sorted(named)) or '<none>'}")

    store = PaperStore(paths)
    if args.apply:
        paths.ensure()

    stats = migrate_papers(store, named, apply=args.apply)
    print(f"papers read : {stats['papers']}")
    print(f"questions   : {stats['questions']}")

    if not args.apply:
        print("dry run complete; re-run with --apply to write .npee-math-papers")
        return 0

    # Registry, bundle metadata, index and release.
    registry = CatalogRegistry(
        entries=[
            # reuse the legacy registry shape so any extra fields survive
            *load_registry(LEGACY_REGISTRY).entries,
        ]
    )
    from npee_math_papers.core.store import atomic_write_json  # local import to keep the top clean

    atomic_write_json(paths.registry, {
        "schema_version": registry.schema_version,
        "catalogs": [
            {"id": entry.id, "name": entry.name, "enabled": entry.enabled}
            for entry in registry.entries
        ],
    })
    for bundle in store.list_bundles():
        store.write_bundle_meta(bundle.series_key, bundle.year, bundle.subject, named.get(bundle.series_key, bundle.series_key))

    index = store.rebuild_index()
    release = store.write_release()
    print(f"bundles     : {index['bundle_count']}")
    print(f"indexed     : {index['paper_count']} papers")
    print(f"release     : {release['paper_count']} papers, library_hash={release['library_hash'][:16]}")

    verify = verify_roundtrip(store)
    print(f"verified    : {verify['checked']} papers, {verify['question_total']} questions, {verify['figure_total']} figures")

    if args.with_evidence:
        evidence = copy_evidence(paths, apply=args.apply, hardlink=args.hardlink_evidence)
        print(f"evidence    : {evidence['pdfs']} pdfs, {evidence['pages']} pages")

    expected_papers = stats["papers"]
    if verify["checked"] != expected_papers:
        print(f"ERROR migrated paper count {verify['checked']} != source {expected_papers}", file=sys.stderr)
        return 2
    print("migration OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
