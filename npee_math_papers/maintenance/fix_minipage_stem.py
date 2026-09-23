r"""Split the one solution stem that wrapped its sub-questions in a ``minipage``.

``euclid3-2025-math1/3`` q20 stored its two sub-questions as a single ``minipage``
block inside the stem::

    设函数 $f_n(x)=…$。\\n\\begin{minipage}{\\linewidth}(I)\\ 证明…；\\\\(II)\\ 设数列…\\end{minipage}

``\\begin{minipage}`` is a *layout* construct, and the document contract puts
sub-questions in ``subparts`` (the class numbers them).  The awkward body also
made the two sub-questions wrap early, so the printed question disagreed with
every other solution question.  This splits the lead-in and the two sub-questions
apart, dropping the wrapper and the ordinals.

Usage::

   python -m npee_math_papers.maintenance.fix_minipage_stem            # dry run
   python -m npee_math_papers.maintenance.fix_minipage_stem --apply
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

#: ``\begin{minipage}{<width>} <body> \end{minipage}``
_MINIPAGE_RE = re.compile(
    r"\\begin\{minipage\}(?:\{[^{}]*\})?(?P<body>.*?)\\end\{minipage\}",
    re.DOTALL,
)
#: A leading sub-question ordinal: ``(I)``, ``（Ⅱ）``, ``(1)`` …
_ORDINAL_RE = re.compile(
    r"^\s*[（(]\s*\$?\s*(?:\\mathrm\{)?\s*(?:I{1,3}|IV|V|[0-9]{1,2})\s*\}?\s*\$?\s*[）)]\s*"
)
#: A row separator that joins two sub-questions inside the block.
_ROW_BREAK_RE = re.compile(r"\\\\[ \t]*")
#: A leading control space left where an ordinal was removed.
_LEADING_SPACE_RE = re.compile(r"^[ \t]*(?:\\[ \t])+")

def split_stem(text: str) -> tuple[str, list[str]] | None:
    """Return ``(stem, subparts)`` for a stem whose sub-questions sit in a minipage."""

    match = _MINIPAGE_RE.search(text)
    if match is None:
        return None
    lead = text[: match.start()]
    # A break before the block only separated it from the lead-in, which the
    # split now expresses with subparts; drop it so the stem ends cleanly.
    lead = re.sub(r"(?:" + re.escape("\\" + "n") + r")+[ \t]*$", "", lead).strip()
    body = match.group("body")
    pieces = []
    for part in _ROW_BREAK_RE.split(body):
        part = _ORDINAL_RE.sub("", part)
        part = _LEADING_SPACE_RE.sub("", part).strip()
        if part:
            pieces.append(part)
    parts = pieces
    if not lead or len(parts) < 2:
        return None
    return lead, parts

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/minipage-stem-repairs.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            stem = (question.get("stem") or {}).get("text") or ""
            if "minipage" not in stem:
                continue
            split = split_stem(stem)
            if split is None:
                continue
            lead, parts = split
            if modified is None:
                modified = {
                    "series_key": record.series_key, "year": record.year,
                    "subject": record.subject, "paper_no": record.paper_no,
                    "questions": copy.deepcopy(record.questions),
                }
            target = next(x for x in modified["questions"]
                          if int(x["number"]) == int(question["number"]))
            target["stem"]["text"] = lead
            target["subparts"] = [{"text": part, "figures": []} for part in parts]
            repairs.append({
                "natural_key": record.natural_key, "question": int(question["number"]),
                "before": stem, "stem": lead, "subparts": parts,
            })
        if modified is not None:
            touched[record.natural_key] = modified

    print(f"需要拆分：{len(repairs)} 套")
    for item in repairs:
        print()
        print(f"  {item['natural_key']} q{item['question']}")
        print(f"    BEFORE: {item['before'][:150]!r}")
        print(f"    stem : {item['stem']!r}")
        for index, part in enumerate(item["subparts"], 1):
            print(f"    sub{index}: {part[:110]!r}")

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
