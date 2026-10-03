#!/usr/bin/env python3
r"""Apply a reviewed errata file to the question bank.

``maintenance/apply_reader_errata`` hard-codes one batch of fixes. This tool does
the same job for any batch, driven by a JSON file, so a re-extraction sweep can
hand its verified findings over without another bespoke script.

Fix file format (UTF-8 JSON array)::

    [
      {
        "key": "2025/math1/zhangyu8/1",
        "question": 3,
        "field": "choices.A.text",
        "before": "\\cdot",
        "after": "\\times",
        "evidence": "源页 p004 选项 A 印 ×，选项 B 印 ·",
        "source": "build/zy8-v2/zhangyu8-2025-math1/pages/p004.png"
      }
    ]

``field`` is one of ``stem.text``, ``stem.figures[N].latex``,
``choices.X.text`` (X = A..D) or ``subparts.N.text``.

Two edit modes are accepted:

``anchor``
    ``before``/``after``: ``before`` must occur exactly once in the target field
    and is replaced in place. Use this for a localised change.
``field``
    ``after`` only, with ``before`` omitted or ``null``: the whole field is
    replaced. Use this when the re-reading produced a complete new field, which
    is the normal shape of an adjudicated correction.

Every fix carries its own evidence and source-page reference so the batch stays
auditable.

The command is dry-run unless ``--apply`` is given. On apply it also re-pins the
``content_hash`` of every affected ``composition/*/composition.json`` reference,
using the sealing subject recorded *before* the bank changed.

Usage::

    python -m npee_math_papers.maintenance.apply_errata_file --fixes build/zy8-v2/fixes.json
    python -m npee_math_papers.maintenance.apply_errata_file --fixes build/zy8-v2/fixes.json --apply
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.store import PaperRecord  # noqa: E402
from npee_math_papers.maintenance.apply_reader_errata import (  # noqa: E402
    _field_text,
    _pin_plan,
    _repin_compositions,
    _set_field_text,
)
from npee_math_papers.service import NpeeService  # noqa: E402

VALID_FIELD = re.compile(
    r"^stem\.text$|^stem\.figures\[\d+\]\.latex$|^choices\.[A-Z]\.text$|^subparts\.\d+\.text$"
)


def load_fixes(path: Path) -> list[dict]:
    # utf-8-sig so a file written by PowerShell's Out-File (which prepends a BOM)
    # still parses; a stray BOM would otherwise make json.loads fail on line 1.
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise SystemExit(f"{path.as_posix()}: 顶层必须是数组")
    for index, item in enumerate(payload, 1):
        for name in ("key", "question", "field", "after"):
            if name not in item:
                raise SystemExit(f"{path.as_posix()} 第 {index} 条缺少字段 {name!r}")
        if not VALID_FIELD.match(item["field"]):
            raise SystemExit(f"{path.as_posix()} 第 {index} 条 field 非法：{item['field']!r}")
        if item.get("before") is not None and item["before"] == item["after"]:
            raise SystemExit(f"{path.as_posix()} 第 {index} 条 before 与 after 相同")
    return payload


def plan_fix(question: dict, fix: dict) -> tuple[str, str | None]:
    """Return (status, mode) for one fix against the current field content.

    ``mode`` is ``"anchor"`` for an in-place substring replacement and
    ``"field"`` for a whole-field replacement; ``None`` means no edit.
    """

    try:
        text = _field_text(question, fix["field"])
    except KeyError:
        return "缺少字段", None
    anchor = fix.get("before")
    if anchor is None:
        return ("已是目标值" if text == fix["after"] else "待整段替换"), "field"
    if anchor not in text and fix["after"] in text:
        return "已是目标值", None
    count = text.count(anchor)
    if count == 0:
        return "锚点未命中", None
    if count > 1:
        return "锚点不唯一", None
    return "待改写", "anchor"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixes", type=Path, required=True, help="已复核的勘误清单 JSON")
    parser.add_argument("--apply", action="store_true", help="写回题库（默认只预览）")
    parser.add_argument("--report", type=Path, help="实际写入的改动记录（默认与 --fixes 同名 .applied.json）")
    args = parser.parse_args()

    fixes = load_fixes(args.fixes)
    service = NpeeService.create()
    store = service.context.store
    records = {record.natural_key: record for record in store.iter_records()}
    pin_plan = _pin_plan(store)

    plan: list[dict] = []
    edits: list[dict] = []
    for fix in fixes:
        record = records.get(fix["key"])
        if record is None:
            plan.append({**fix, "status": "缺少套卷"})
            continue
        question = next(
            (item for item in record.questions if int(item["number"]) == int(fix["question"])),
            None,
        )
        if question is None:
            plan.append({**fix, "status": "缺少题号"})
            continue
        status, mode = plan_fix(question, fix)
        plan.append({**fix, "status": status})
        if mode is not None:
            edits.append({"fix": fix, "record": record, "number": int(fix["question"]), "mode": mode})

    counts: dict[str, int] = {}
    for item in plan:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(f"共 {len(plan)} 条：" + "，".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for item in plan:
        if item["status"] not in ("待改写", "待整段替换"):
            print(f"  [{item['status']}] {item['key']} q{item['question']} {item['field']}")
            print(f"      BEFORE: {str(item.get('before'))!r}")
    print()

    if not args.apply:
        print("预览模式；加 --apply 写回。")
        return 0

    touched: dict[str, PaperRecord] = {}
    applied: list[dict] = []
    for edit in edits:
        record, fix = edit["record"], edit["fix"]
        payload = touched.get(record.natural_key)
        if payload is None:
            payload = PaperRecord(
                record.series_key, record.year, record.subject, record.paper_no,
                copy.deepcopy(record.questions),
            )
            touched[record.natural_key] = payload
        question = next(item for item in payload.questions if int(item["number"]) == edit["number"])
        if edit["mode"] == "field":
            _set_field_text(question, fix["field"], fix["after"])
        else:
            text = _field_text(question, fix["field"])
            _set_field_text(question, fix["field"], text.replace(fix["before"], fix["after"], 1))
        applied.append({**fix, "mode": edit["mode"]})

    for payload in touched.values():
        store.write_paper(payload, replace=True)
    store.rebuild_index()
    store.write_release()

    report = args.report or args.fixes.with_suffix(".applied.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(applied, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已写回 {len(applied)} 处改动，涉及 {len(touched)} 套，并重建索引与发布清单。")
    print(f"改动记录：{report.as_posix()}")
    notes = _repin_compositions(store, pin_plan)
    for note in notes:
        print("  ", note)
    if not notes:
        print("   组卷包 content_hash 无需重钉。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
