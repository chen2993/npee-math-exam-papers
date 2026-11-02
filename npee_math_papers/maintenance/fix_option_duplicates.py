r"""Two option lists that were mis-transcribed; both verified against the source pages.

1. ``yubingsen5-2024-math1/1`` q6 -- source option A reads
   ``线性方程组 (E O; O Aᵀ)x=0 与 (E Aᵀ; A O)x=0 同解``: the left matrix carries
   ``Aᵀ``.  The stored text dropped the transpose, which made A byte-identical to
   B and so removed a distinct option.

2. ``yubingsen5-2025-math2/4`` q4 -- source option C is *blank* (the paper leaves
   the answer to be filled in).  The stored text invented ``$1$``, colliding with
   D.  A blank option is represented by the ``{}`` placeholder, which prints
   nothing and keeps the record structurally valid.

Both are one-off transcriptions, so the corrected values are written verbatim
rather than derived by a rule.

Usage::

   python -m npee_math_papers.maintenance.fix_option_duplicates            # dry run
   python -m npee_math_papers.maintenance.fix_option_duplicates --apply
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

#: ``(series_key, year, subject, paper_no, question_no, label) -> corrected text``
CORRECTIONS: dict[tuple[str, int, str, int, int, str], tuple[str, str]] = {
    # Option A keeps the transpose on the left matrix, exactly as the source prints.
    ("yubingsen5", 2024, "math1", 1, 6, "A"): (
        "线性方程组 $\\begin{pmatrix}E&O\\\\O&A^{\\mathsf T}\\end{pmatrix}x=0$ "
        "与 $\\begin{pmatrix}E&A^{\\mathsf T}\\\\A&O\\end{pmatrix}x=0$ 同解",
        "source page prints A^T in the left matrix; the stored text had dropped it",
    ),
    # Option C is blank on the source page.
    ("yubingsen5", 2025, "math2", 4, 4, "C"): (
        "{}",
        "source page leaves option C blank; the stored text invented a value",
    ),
}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/option-duplicate-repairs.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            for choice in question.get("choices") or []:
                key = (
                    record.series_key, record.year, record.subject, record.paper_no,
                    int(question["number"]), str(choice.get("label")),
                )
                correction = CORRECTIONS.get(key)
                if correction is None:
                    continue
                wanted, reason = correction
                if choice.get("text") == wanted:
                    continue
                if modified is None:
                    modified = {
                        "series_key": record.series_key, "year": record.year,
                        "subject": record.subject, "paper_no": record.paper_no,
                        "questions": copy.deepcopy(record.questions),
                    }
                target = next(x for x in modified["questions"]
                              if int(x["number"]) == int(question["number"]))
                for item in target.get("choices") or []:
                    if item.get("label") == choice.get("label"):
                        item["text"] = wanted
                        break
                repairs.append({
                    "natural_key": record.natural_key, "question": int(question["number"]),
                    "label": choice.get("label"), "before": choice.get("text"),
                    "after": wanted, "reason": reason,
                })
        if modified is not None:
            touched[record.natural_key] = modified

    print(f"需要改正：{len(repairs)} 个选项，涉及 {len(touched)} 套")
    for item in repairs:
        print()
        print(f"  {item['natural_key']} q{item['question']} 选项 {item['label']}")
        print(f"    理由: {item['reason']}")
        print(f"    BEFORE: {item['before']!r}")
        print(f"    AFTER : {item['after']!r}")

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
