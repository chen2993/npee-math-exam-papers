r"""Repair a doubled backslash inside inline math.

A row separator (``\\``) is only meaningful inside an alignment environment, where
TeX uses it to end a row. Written in ordinary inline math it instead ends the
*line*, so a formula that should read ``f_1(x)=y_2(x),\ f_2(x)=y_1(x)`` prints on
two lines. Extraction produced 13 such fields (20 occurrences) across 4 papers.

The source spelling is always a single backslash:

* ``=1\\ (x>0)``      -> ``=1\ (x>0)``        a control space
* ``(\\|x\\|)^2``     -> ``(\|x\|)^2``        the norm delimiter
* ``a,\\ b``          -> ``a,\ b``             a control space

So the repair halves the run. Nothing inside an alignment environment or a
``\substack``/``\subarray`` body is touched -- there ``\\`` is a real row
separator -- and a run of 4 or more is left alone, because that is not the
pattern this tool knows how to read.

Usage::

   python -m npee_math_papers.maintenance.fix_stray_row_break            # dry run
   python -m npee_math_papers.maintenance.fix_stray_row_break --apply
   python -m npee_math_papers.maintenance.fix_stray_row_break --json out.json
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

#: Environments whose body is a grid: ``\\`` there is a row separator.
ALIGNMENT_ENVIRONMENTS = (
    "array", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix",
    "Vmatrix", "smallmatrix", "cases", "aligned", "gathered", "split",
)
_ENV_RE = re.compile(r"\\(begin|end)\{([A-Za-z*]+)\}")
_MACRO_RE = re.compile(r"\\(?:substack|subarray)\s*\{")
_ESCAPED_DOLLAR = chr(92) + "$"

def find_stray(text: str) -> list[int]:
    """Return the offsets of an inline-math ``\\`` that is not a row separator."""

    found: list[int] = []
    depth = 0
    macro = 0
    math = False
    index = 0
    while index < len(text):
        env = _ENV_RE.match(text, index)
        if env:
            if env.group(2) in ALIGNMENT_ENVIRONMENTS:
                depth += 1 if env.group(1) == "begin" else -1
            index = env.end()
            continue
        spacer = _MACRO_RE.match(text, index)
        if spacer:
            macro += 1
            index = spacer.end()
            continue
        if macro > 0 and text[index] == "}":
            macro -= 1
            index += 1
            continue
        if text.startswith(_ESCAPED_DOLLAR, index):
            index += 2
            continue
        if text[index] == "$":
            math = not math
            index += 1
            continue
        if text.startswith("\\\\", index):
            end = index
            while text.startswith("\\\\", end):
                end += 2
            if depth == 0 and macro == 0 and math and (end - index) == 2:
                found.append(index)
            index = end
            continue
        index += 1
    return found

def repair(text: str) -> str:
    """Halve each qualifying ``\\`` run to a single backslash."""

    offsets = find_stray(text)
    if not offsets:
        return text
    out: list[str] = []
    cursor = 0
    for at in offsets:
        out.append(text[cursor:at])
        out.append("\\")
        cursor = at + 2
    out.append(text[cursor:])
    return "".join(out)

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
    parser.add_argument("--json", type=Path, default=Path("build/stray-row-break-repairs.json"))
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store

    repairs: list[dict] = []
    touched: dict[str, dict] = {}
    for record in store.iter_records():
        modified: dict | None = None
        for question in record.questions:
            for field, text in _fields(question):
                fixed = repair(text)
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

    print(f"需要修复：{len(repairs)} 处字段，涉及 {len(touched)} 套")
    print()
    for item in repairs:
        print(f"  {item['natural_key']} q{item['question']} {item['field']}")
        print(f"    {item['before']!r}")
        print(f"    -> {item['after']!r}")

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
