#!/usr/bin/env python3
"""Audit the .npee-math-papers paper store.

Checks the invariants that keep the store trustworthy:

- every paper document parses and passes schema validation,
- each paper's stored ``content_hash`` matches its questions,
- bundle directories and ``bundle.json`` agree with the papers inside them,
- natural keys are unique across the whole store,
- the derived index and release manifest agree with the papers.

Usage::

    python -m npee_math_papers.maintenance.audit_store
    python -m npee_math_papers.maintenance.audit_store --rebuild
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.errors import NpeeError  # noqa: E402
from npee_math_papers.core.release import verify_release_manifest, load_release_manifest  # noqa: E402
from npee_math_papers.core.store import NpeePaths, PaperStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, help="override the .npee-math-papers data root")
    parser.add_argument("--rebuild", action="store_true", help="rebuild the index and release manifest before auditing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = NpeePaths.resolve(args.data_root, repository_root=ROOT)
    store = PaperStore(paths)
    errors: list[str] = []
    warnings: list[str] = []

    if not paths.papers.is_dir():
        print(f"ERROR paper store is missing: {paths.papers.as_posix()}")
        print("HINT populate it with the MCP tool npee_ingest_paper (one paper per call)")
        return 1

    if args.rebuild:
        index = store.rebuild_index()
        release = store.write_release()
        print(f"rebuilt index: {index['paper_count']} papers; release: {release['paper_count']} papers")

    seen_keys: set[str] = set()
    paper_count = 0
    question_count = 0
    figure_count = 0

    for bundle in store.list_bundles():
        meta_path = bundle.path / "bundle.json"
        if not meta_path.is_file():
            warnings.append(f"{bundle.key}: bundle.json is missing")
        bundle_keys: set[str] = set()
        for path in bundle.paper_paths:
            try:
                record = store.read_paper(bundle.series_key, bundle.year, bundle.subject, int(path.stem))
            except (NpeeError, ValueError) as error:
                errors.append(f"{path.as_posix()}: {error}")
                continue
            paper_count += 1
            question_count += record.question_count
            figure_count += sum(
                len((question.get("stem") or {}).get("figures") or [])
                + sum(len(choice.get("figures") or []) for choice in question.get("choices") or [])
                + sum(len(subpart.get("figures") or []) for subpart in question.get("subparts") or [])
                for question in record.questions
            )
            if record.natural_key in seen_keys:
                errors.append(f"duplicate natural key: {record.natural_key}")
            seen_keys.add(record.natural_key)
            bundle_keys.add(record.natural_key)
            if record.series_key != bundle.series_key or record.year != bundle.year or record.subject != bundle.subject:
                errors.append(f"{path.as_posix()} identity does not match its bundle directory")
        if not bundle_keys:
            warnings.append(f"{bundle.key}: bundle contains no papers")

    # Release manifest agreement.
    release_path = paths.release
    if release_path.is_file():
        try:
            manifest = load_release_manifest(release_path)
            report = verify_release_manifest(manifest, store.list_summaries())
            if not report["ok"]:
                errors.append(
                    f"release manifest is stale: changed={report['changed']} extra={report['extra']}"
                )
            if report["missing"]:
                warnings.append(f"release manifest lists missing papers: {report['missing']}")
            print(f"release library_hash: {manifest.library_hash}")
        except NpeeError as error:
            errors.append(f"release manifest: {error}")
    else:
        warnings.append("release manifest is missing; run with --rebuild")

    print(f"store root : {paths.root.as_posix()}")
    print(f"bundles    : {len(store.list_bundles())}")
    print(f"papers     : {paper_count}")
    print(f"questions  : {question_count}")
    print(f"figures    : {figure_count}")

    for warning in warnings:
        print(f"WARN {warning}")
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        print(f"FAIL errors={len(errors)}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
