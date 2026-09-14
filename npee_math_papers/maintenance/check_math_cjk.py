#!/usr/bin/env python3
"""Audit the question store for CJK characters left directly in math mode.

CJK inside ``\\text{...}`` is fine; CJK rendered directly by the math font is not.
This scans every stored paper through the shared store so it stays correct as the
question model evolves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.store import NpeePaths, PaperStore  # noqa: E402
from npee_math_papers.core.tex import cjk_text_in_math  # noqa: E402


def latex_fields(question: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield every TeX-bearing field of a schema-3.0 question."""

    stem = question.get("stem") or {}
    yield "stem.text", str(stem.get("text", ""))
    for figure_index, figure in enumerate(stem.get("figures") or []):
        if isinstance(figure.get("latex"), str):
            yield f"stem.figures[{figure_index}].latex", figure["latex"]
    for choice_index, choice in enumerate(question.get("choices") or []):
        yield f"choices[{choice_index}].text", str(choice.get("text", ""))
        for figure_index, figure in enumerate(choice.get("figures") or []):
            if isinstance(figure.get("latex"), str):
                yield f"choices[{choice_index}].figures[{figure_index}].latex", figure["latex"]
    for part_index, subpart in enumerate(question.get("subparts") or []):
        yield f"subparts[{part_index}].text", str(subpart.get("text", ""))
        for figure_index, figure in enumerate(subpart.get("figures") or []):
            if isinstance(figure.get("latex"), str):
                yield f"subparts[{part_index}].figures[{figure_index}].latex", figure["latex"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, help="override the .npee-math-papers data root")
    args = parser.parse_args()

    store = PaperStore(NpeePaths.resolve(args.data_root, repository_root=ROOT))
    findings: list[str] = []
    papers = 0
    for record in store.iter_records():
        papers += 1
        for question in record.questions:
            for field, value in latex_fields(question):
                for fragment in cjk_text_in_math(value):
                    findings.append(f"{record.natural_key} q{question['number']} {field}: {fragment!r}")

    if findings:
        print(f"CJK-in-math findings: {len(findings)} (papers scanned: {papers})")
        for finding in findings:
            print(finding)
        return 1
    print(f"No CJK characters found directly in math mode. (papers scanned: {papers})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
