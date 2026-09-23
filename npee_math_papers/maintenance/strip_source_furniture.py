r"""Remove source-page furniture that was copied into the stored text.

Two kinds of furniture sit in the store, both verified as non-question content:

* a **section heading** copied from the top of a page:
  ``一、选择题：1～10 小题，每小题 5 分，共 50 分。下列每题给出的四个选项中，只有一个选项是最符合题目要求的。``
  The layout class prints that heading from the question's own section, so a
  stored copy prints the heading twice.
* a **public-account stamp**: ``（公众号：风中羽小易）``. It is a publisher mark,
  not question text.

``service/rendering/content.py`` already strips both at render time, so the
compiled PDFs are correct.  This pass additionally cleans the *store*, because
the store is what the HTTP API and the web reader display: leaving the text there
would show the watermark in the browser even though the PDF is clean.

A stem that consisted only of furniture (a lone watermark) is left empty by this
pass; it is written as the ``{}`` placeholder, which the renderer prints as
nothing.  When the question has subparts, those carry the content and the
placeholder is invisible.

Usage::

   python -m npee_math_papers.maintenance.strip_source_furniture            # dry run
   python -m npee_math_papers.maintenance.strip_source_furniture --apply
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
from npee_math_papers.service.rendering.content import (  # noqa: E402
    strip_section_heading,
    strip_watermark,
)

def clean(text: str) -> str:
    """Apply both strips, keeping the record renderable."""

    cleaned = strip_section_heading(strip_watermark(text))
    return cleaned if cleaned.strip() else "{}"

def _fields(question: dict) -> list[tuple[str, str]]:
    found = [("stem", (question.get("stem") or {}).get("text") or "")]
    for order, part in enumerate(question.get("subparts") or [], 1):
        found.append((f"subparts[{order}]", (part or {}).get("text") or ""))
    for choice in question.get("choices") or []:
        found.append((f"choices[{choice.get('label')}]", choice.get("text") or ""))
    return found

def _set(question: dict, field: str, value: str) -> None:
    if field == "stem":
        question["stem"]["text"] = value
        return
    if field.startswith("subparts["):
        order = int(field[len("subparts["):-1])
        question["subparts"][order - 1]["text"] = value
        return
    label = field[len("choices["):-1]
    for choice in question["choices"]:
        if choice.get("label") == label:
            choice["text"] = value
            return

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/source-furniture-repairs.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            for field, text in _fields(question):
                if not text:
                    continue
                fixed = clean(text)
                if fixed == text:
                    continue
                if modified is None:
                    modified = {
                        "series_key": record.series_key, "year": record.year,
                        "subject": record.subject, "paper_no": record.paper_no,
                        "questions": copy.deepcopy(record.questions),
                    }
                target = next(x for x in modified["questions"]
                              if int(x["number"]) == int(question["number"]))
                _set(target, field, fixed)
                repairs.append({
                    "natural_key": record.natural_key, "question": int(question["number"]),
                    "field": field, "before": text, "after": fixed,
                })
        if modified is not None:
            touched[record.natural_key] = modified

    print(f"需要清理：{len(repairs)} 处字段，涉及 {len(touched)} 套")
    print()
    for item in repairs:
        print(f"  {item['natural_key']} q{item['question']} {item['field']}")
        print(f"    BEFORE: {item['before'][:120]!r}")
        print(f"    AFTER : {item['after'][:120]!r}")

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
