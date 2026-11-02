r"""Fill in the question scores that extraction left empty.

A paper's score layout is fixed by the examination itself and is identical in
every bundle of this library::

    choice   1–10   5 points each
    fill    11–16   5 points each
    solution 17     10 points
    solution 18–22  12 points

Measured over the 325 papers that already carry scores, each of those six
positions is unanimous (q17 is always 10; q18…q22 always 12).  118 questions in
5 bundles were stored with ``points: null`` -- an extraction omission, not a
property of those papers.  The class prints the score from ``points``, so filling
it both restores the printed label and makes the paper total correct.

The number is derived from the question's *number*, never guessed per question,
and a paper that contradicts the layout is reported instead of overwritten.

Usage::

   python -m npee_math_papers.maintenance.fill_missing_points            # dry run
   python -m npee_math_papers.maintenance.fill_missing_points --apply
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from npee_math_papers.service import NpeeService  # noqa: E402

#: Question number -> score, per section.
SCORES: dict[str, dict[int, int]] = {
    "choice": {**{number: 5 for number in range(1, 11)}, **{number: 5 for number in range(11, 17)}},
    "fill": {**{number: 5 for number in range(11, 17)}},
    "solution": {17: 10, **{number: 12 for number in range(18, 23)}},
}

def expected_points(section: str, number: int) -> int | None:
    """Return the score this paper layout assigns, or ``None`` if unknown."""

    if section == "choice" and 1 <= number <= 10:
        return 5
    if section == "fill" and 11 <= number <= 16:
        return 5
    if section == "solution":
        return SCORES["solution"].get(number)
    return None

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/missing-points-repairs.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    conflicts: list[str] = []

    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            if question.get("points") is not None:
                continue
            section = str(question.get("section"))
            number = int(question.get("number"))
            value = expected_points(section, number)
            if value is None:
                conflicts.append(f"{record.natural_key} q{number} [{section}]")
                continue
            if modified is None:
                modified = {
                    "series_key": record.series_key, "year": record.year,
                    "subject": record.subject, "paper_no": record.paper_no,
                    "questions": copy.deepcopy(record.questions),
                }
            target = next(x for x in modified["questions"] if int(x["number"]) == number)
            target["points"] = value
            repairs.append({
                "natural_key": record.natural_key, "question": number,
                "section": section, "points": value,
            })
        if modified is not None:
            touched[record.natural_key] = modified

    print(f"需要补分：{len(repairs)} 题，涉及 {len(touched)} 套")
    per_bundle: dict[str, int] = {}
    for item in repairs:
        per_bundle[item["natural_key"]] = per_bundle.get(item["natural_key"], 0) + 1
    for key in sorted(per_bundle):
        print(f"    {key}: {per_bundle[key]} 题")
    if conflicts:
        print()
        print("无法按固定分值判定（需人工确认）：")
        for item in conflicts:
            print("   ", item)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(repairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.apply:
        print()
        print(f"预览模式；加 --apply 写回。清单：{args.json.as_posix()}")
        return 0

    from npee_math_papers.core.store import PaperRecord

    for payload in touched.values():
        store.write_paper(
            PaperRecord(
                series_key=payload["series_key"], year=payload["year"],
                subject=payload["subject"], paper_no=payload["paper_no"],
                questions=payload["questions"],
            ),
            replace=True,
        )
    store.rebuild_index()
    store.write_release()
    print()
    print(f"已写回 {len(touched)} 套，并重建索引与发布清单。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
