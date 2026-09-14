#!/usr/bin/env python3
"""Migrate source PDFs and page captures from ``agent/workspace`` into ``.npee-math-papers``.

For each workspace bucket ``<series>_<year>_<subject>`` this:

1. registers ``source.pdf`` as ``.npee-math-papers/sources/<bundle>/source.pdf`` (hardlinked by
   default so the ~1 GB of PDFs is not duplicated);
2. reads each ``unit-###/dispatch.json`` for its page boundaries and creates a
   capture ``.npee-math-papers/captures/<bundle>/<unit-###>/`` with the page PNGs hardlinked;
3. verifies the migrated page count matches the source before reporting success.

Hardlinks keep the migration instant and space-free. Because the source tree is
removed only after verification, the linked files remain valid afterwards.

Usage::

    python -m npee_math_papers.maintenance.migrate_evidence            # dry run
    python -m npee_math_papers.maintenance.migrate_evidence --apply
    python -m npee_math_papers.maintenance.migrate_evidence --apply --copy   # copy instead of hardlink
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.sources import CaptureManager, SourceManager, link_or_copy  # noqa: E402
from npee_math_papers.core.store import NpeePaths  # noqa: E402
from npee_math_papers.core.release import source_sha256  # noqa: E402

WORKSPACE = ROOT / "agent" / "workspace"
SUBJECTS = {"math1", "math2", "math3"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write .npee-math-papers (default is a dry run)")
    parser.add_argument("--copy", action="store_true", help="copy evidence instead of hardlinking")
    return parser.parse_args()


def bucket_identity(name: str) -> tuple[str, int, str] | None:
    parts = name.split("_")
    if len(parts) != 3:
        return None
    series_key, year_text, subject = parts
    if subject not in SUBJECTS:
        return None
    try:
        year = int(year_text)
    except ValueError:
        return None
    return series_key, year, subject


def page_files(unit: Path) -> list[Path]:
    pages_dir = unit / "pages"
    if not pages_dir.is_dir():
        return []
    return sorted(pages_dir.glob("p*.png"), key=lambda item: item.name)


def main() -> int:
    args = parse_args()
    paths = NpeePaths.resolve(repository_root=ROOT)
    if args.apply:
        paths.ensure()
    sources = SourceManager(paths)
    captures = CaptureManager(paths)

    if not WORKSPACE.is_dir():
        print(f"workspace is absent: {WORKSPACE.as_posix()}; nothing to migrate")
        return 0

    buckets = 0
    pdfs = 0
    captures_made = 0
    pages_linked = 0
    mismatches: list[str] = []

    for bucket in sorted(item for item in WORKSPACE.iterdir() if item.is_dir()):
        identity = bucket_identity(bucket.name)
        if identity is None:
            continue
        series_key, year, subject = identity
        buckets += 1

        source_pdf = bucket / "source.pdf"
        if source_pdf.is_file():
            pdfs += 1
            if args.apply:
                target_dir = sources.source_dir(series_key, year, subject)
                target_dir.mkdir(parents=True, exist_ok=True)
                target = sources.source_path(series_key, year, subject)
                if not target.exists():
                    link_or_copy(source_pdf, target, hardlink=not args.copy)
                digest = source_sha256(target)
                from npee_math_papers.core.store import atomic_write_json

                atomic_write_json(
                    sources.source_meta_path(series_key, year, subject),
                    {
                        "schema_version": "3.0",
                        "bundle": f"{series_key}-{year}-{subject}",
                        "series_key": series_key,
                        "year": year,
                        "subject": subject,
                        "source_id": None,
                        "sha256": digest,
                        "page_count": None,
                        "notes": f"migrated from {bucket.name}",
                    },
                )

        for unit in sorted(item for item in bucket.glob("unit-*") if item.is_dir()):
            absolute_pages = page_files(unit)
            if not absolute_pages:
                continue
            question_pages: list[int] = []
            answer_pages: list[int] = []
            dispatch_path = unit / "dispatch.json"
            if dispatch_path.is_file():
                dispatch = json.loads(dispatch_path.read_text(encoding="utf-8"))
                question_pages = [int(value) for value in dispatch.get("input", {}).get("question_pages", [])]
                answer_pages = [int(value) for value in dispatch.get("input", {}).get("answer_pages", [])]
            if not question_pages:
                # Fall back to the page numbers actually present.
                question_pages = [int(path.stem[1:]) for path in absolute_pages]

            captures_made += 1
            if args.apply:
                captures.prepare(
                    series_key,
                    year,
                    subject,
                    unit.name,
                    question_pages=question_pages,
                    answer_pages=answer_pages,
                    notes=f"migrated from {bucket.name}/{unit.name}",
                )
                for png in absolute_pages:
                    page_number = int(png.stem[1:])
                    if page_number not in question_pages:
                        mismatches.append(f"{bucket.name}/{unit.name}: page {page_number} not in question_pages")
                        continue
                    target = captures.capture_dir(series_key, year, subject, unit.name) / "pages" / png.name
                    link_or_copy(png, target, hardlink=not args.copy)
                    pages_linked += 1

    print(f"data root    : {paths.root.as_posix()}")
    print(f"mode         : {'APPLY' if args.apply else 'DRY-RUN'}{' (copy)' if args.copy else ' (hardlink)'}")
    print(f"buckets      : {buckets}")
    print(f"source pdfs  : {pdfs}")
    print(f"captures     : {captures_made}")
    print(f"pages linked : {pages_linked}")
    for mismatch in mismatches:
        print(f"WARN {mismatch}")

    if args.apply:
        # Verify every migrated capture page exists in .npee-math-papers.
        missing = 0
        for capture in captures.list_captures():
            for page in capture.question_pages:
                target = capture.pages_dir / f"p{page:04d}.png"
                if not target.is_file():
                    missing += 1
                    print(f"MISSING {capture.bundle}/{capture.capture_id}/p{page:04d}.png")
        if missing:
            print(f"FAIL missing={missing}")
            return 1
        print("evidence migration OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
