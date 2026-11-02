"""Strip the stored ``（本题满分 X 分）`` label from solution stems.

The class prints that label from ``points``, and ``service/rendering/content.py``
already removes a stored copy at render time -- so this pass only removes the
redundancy *in the store*, where the HTTP API and the web reader still show it.
It reuses ``strip_solution_score_label`` so there is one definition of the rule.

Usage::

   python -m npee_math_papers.maintenance.strip_stored_score_labels --apply
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from npee_math_papers.core.store import PaperRecord  # noqa: E402
from npee_math_papers.service import NpeeService  # noqa: E402
from npee_math_papers.service.rendering.content import (  # noqa: E402
    strip_solution_score_label,
)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    changed = 0
    touched: list[PaperRecord] = []
    for record in store.iter_records():
        questions = copy.deepcopy(record.questions)
        dirty = False
        for question in questions:
            stem = question.get("stem") or {}
            text = stem.get("text") or ""
            if question.get("section") != "solution" or "本题满分" not in text:
                continue
            fixed = strip_solution_score_label(text)
            if fixed != text:
                stem["text"] = fixed
                changed += 1
                dirty = True
        if dirty:
            touched.append(PaperRecord(record.series_key, record.year, record.subject, record.paper_no, questions))

    print(f"需要清理：{changed} 处，涉及 {len(touched)} 套")
    for record in touched:
        print(f"    {record.natural_key}")

    if not args.apply:
        print("\n预览模式；加 --apply 写回。")
        return 0

    for record in touched:
        store.write_paper(record, replace=True)
    store.rebuild_index()
    store.write_release()
    print(f"\n已写回 {len(touched)} 套，并重建索引与发布清单。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
