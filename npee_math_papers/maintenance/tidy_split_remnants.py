r"""Tidy the two cosmetic leftovers of the minipage split.

``fix_minipage_stem`` split the stem and sub-questions, but the first run left a
trailing ``\n`` on the stem and a leading control space (``\ ``) on each subpart,
because the source used them to separate the parts inside the block.  Both are
now redundant: the split itself separates them.

Usage::

   python -m npee_math_papers.maintenance.tidy_split_remnants            # dry run
   python -m npee_math_papers.maintenance.tidy_split_remnants --apply
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from npee_math_papers.service import NpeeService  # noqa: E402

BREAK = "\\" + "n"

#: A trailing line-break marker on a stem that now ends before its subparts.
_TRAILING_BREAK_RE = re.compile(re.escape(BREAK) + r"[ \t]*$")
#: A leading control space on a subpart, left where an ordinal was removed.
_LEADING_CONTROL_SPACE_RE = re.compile(r"^[ \t]*(?:\\[ \t])+")

def tidy(stem: str, subparts: list[str]) -> tuple[str, list[str]] | None:
    """Return the tidied pair, or ``None`` when nothing needs changing."""

    new_stem = _TRAILING_BREAK_RE.sub("", stem)
    new_subparts = [_LEADING_CONTROL_SPACE_RE.sub("", part).strip() for part in subparts]
    if new_stem == stem and new_subparts == list(subparts):
        return None
    return new_stem, new_subparts

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/split-remnant-tidy.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            stem = (question.get("stem") or {}).get("text") or ""
            parts = [(part or {}).get("text") or "" for part in question.get("subparts") or []]
            if not parts:
                continue
            fixed = tidy(stem, parts)
            if fixed is None:
                continue
            new_stem, new_parts = fixed
            if modified is None:
                modified = {
                    "series_key": record.series_key, "year": record.year,
                    "subject": record.subject, "paper_no": record.paper_no,
                    "questions": copy.deepcopy(record.questions),
                }
            target = next(x for x in modified["questions"]
                          if int(x["number"]) == int(question["number"]))
            target["stem"]["text"] = new_stem
            for block, value in zip(target["subparts"], new_parts):
                block["text"] = value
            repairs.append({
                "natural_key": record.natural_key, "question": int(question["number"]),
                "stem": new_stem, "subparts": new_parts,
            })
        if modified is not None:
            touched[record.natural_key] = modified

    print(f"需要整理：{len(repairs)} 套")
    for item in repairs:
        print()
        print(f"  {item['natural_key']} q{item['question']}")
        print(f"    stem: {item['stem']!r}")
        for index, part in enumerate(item["subparts"], 1):
            print(f"    sub{index}: {part[:100]!r}")

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
