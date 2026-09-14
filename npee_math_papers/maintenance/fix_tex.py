r"""修复题面中"命令丢反斜杠"的历史错误。

背景
----
在矩阵/分段/数组环境里，``\\`` 是行分隔符（本库约定：**2 个反斜杠**）。历史数据里
某些命令少写了一个反斜杠，于是：:

    \\lambda   （2 个）→ 换行 + 字面文本 "lambda"，编译通过但渲染出字母
    \\hline    （2 个）→ 缺行分隔，XeLaTeX 报 ``Misplaced \noalign``

判定标准（与 ``service/tex_builder`` 的构建器一致，纯静态可算）
-----------------------------------------------------------------
设某位置紧跟命令名前有连续 N 个反斜杠：

* 偶数个（``N >= 2``）→ 损坏：偶数意味着"整行分隔 + 字面文本"。
* 奇数个 → 命令被正常求值。

修复方向**按命令分类**，两类方向相反，不能一刀切：

* **行级命令**（``hline`` / ``cline`` / ``hdashline``，必须跟在行分隔之后）：
  目标是 ``行分隔(2) + 命令(1) = 3``，即偶数补一个（``N + 1``）。
* **其他命令**（行内命令，如 ``lambda`` / ``vdots``）：目标是"之前有行分隔则为 3，
  否则为 1"，偶数则减一个（``N - 1``）。

只处理对齐环境内的这一种模式，不动其它任何字符。所有改动都会被记录，便于审查与回滚。
本工具是**幂等**的：对已经正确的文本再跑一次不会产生任何变化。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from npee_math_papers.core.tex_audit import COMMAND_SET  # noqa: E402
from npee_math_papers.service import NpeeService  # noqa: E402
from npee_math_papers.maintenance.audit_tex import iter_fields  # noqa: E402

# 反斜杠串 + 紧跟的字母序列（命令名候选，可能为空 = 纯行分隔）。
_RUN_RE = re.compile(r"\\+([A-Za-z]*)")

# 只在下列对齐环境内做修复。
ALIGNMENT_ENVIRONMENTS = (
    "cases", "matrix", "pmatrix", "bmatrix", "Bmatrix", "vmatrix",
    "Vmatrix", "smallmatrix", "array",
)
ALIGNMENT_RE = re.compile(
    r"\\begin\{(?P<environment>"
    + "|".join(ALIGNMENT_ENVIRONMENTS)
    + r")\}(?P<body>.*?)\\end\{(?P=environment)\}",
    re.DOTALL,
)

# 必须跟在行分隔之后的"行级"命令：偶数个反斜杠时补一个（2 -> 3）。
ROW_LEVEL_COMMANDS = frozenset({"hline", "cline", "hdashline"})

# 少量无法用通用规则表达的历史字段，单独重建其损坏的对齐环境体（见 TODO 的 D2）。
# 键为 (series_key, year, subject, paper_no, question_no, field)，值为函数：
# 输入存储原文，输出修复后文本（只替换环境体，前后文字原样保留）。
# q15 是 6 阶行列式：行分隔统一为 2 个反斜杠，首列 vdots/ddots 前用行分隔 + 命令。
# 该行列式的行结构本身损坏（2/4/6 个反斜杠混杂），无法用统一规则安全推断。
_Q15_VMATRIX_BODY = (
    r"0&0&a_1&0&\cdots&0\\0&0&0&a_2&\cdots&0"
    r"\\\vdots&\vdots&\vdots&\vdots&\ddots&\vdots"
    r"\\0&0&0&0&\cdots&a_{n-2}\\a_{n-1}&0&0&0&\cdots&0"
    r"\\0&a_n&0&0&\cdots&0"
)


def _rebuild_vmatrix(text: str, body: str) -> str:
    """把文本里的第一个 vmatrix 环境体整体替换为 ``body``。"""

    match = re.search(r"\\begin\{vmatrix\}(?P<body>.*?)\\end\{vmatrix\}", text, re.DOTALL)
    if match is None:
        return text
    return text[: match.start("body")] + body + text[match.end("body") :]


CANONICAL_OVERRIDES: dict[tuple[str, int, str, int, int, str], Any] = {
    ("chaoyue10", 2025, "math1", 4, 15, "stem.text"): lambda text: _rebuild_vmatrix(text, _Q15_VMATRIX_BODY),
}


@dataclass
class Repair:
    """一处修复记录。"""

    natural_key: str
    question_no: int
    field: str
    before: str
    after: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "natural_key": self.natural_key,
            "question_no": self.question_no,
            "field": self.field,
            "before": self.before,
            "after": self.after,
        }


def target_backslashes(word: str, count: int, *, at_row_head: bool) -> int:
    """给定反斜杠串的语义，返回修复后的目标个数。

    ``word`` 为空或非命令时表示"纯行分隔串"：

    - 1/2/3 个都可能有合法语义（``\\``、``\\``、``\\\\命令``），保持不动；
    - 偶数且 ``>= 4`` 表示多打了行分隔（矩阵/表格里会多出空行），收敛为 2。

    ``word`` 是命令时：

    - 行级命令（``hline`` 等）必须紧跟一个行分隔，目标恒为 3；
    - 行内命令：``at_row_head`` 为真（命令位于单元格/行首，前面是 ``&`` 或 ``{``）
      时目标为 1；否则（命令跟在行分隔之后）目标为 3。
    """

    if not word or word.lower() not in COMMAND_SET:
        if count >= 4 and count % 2 == 0:
            return 2
        return count
    if word.lower() in ROW_LEVEL_COMMANDS:
        return 3
    if count == 1:
        return 1
    if at_row_head:
        return 1
    return 3


def _fix_alignment_body(body: str) -> tuple[str, list[tuple[str, str]]]:
    """修复一个对齐环境体；返回 (修复后文本, 改动列表)。"""

    changes: list[tuple[str, str]] = []
    output: list[str] = []
    cursor = 0
    for match in _RUN_RE.finditer(body):
        word = match.group(1)
        count = len(match.group(0)) - len(word)
        previous = body[match.start() - 1] if match.start() > 0 else "{"
        target = target_backslashes(word, count, at_row_head=previous in "&{")
        if target == count:
            continue
        fixed = "\\" * target + word
        output.append(body[cursor : match.start()])
        output.append(fixed)
        cursor = match.end()
        changes.append((match.group(0), fixed))
    output.append(body[cursor:])
    return "".join(output), changes


def fix_text(text: str) -> tuple[str, list[tuple[str, str]]]:
    """修复一段文本；返回 (修复后文本, 改动列表)。

    只在 :data:`ALIGNMENT_RE` 命中的对齐环境体内改写，环境之外原样保留。
    """

    changes: list[tuple[str, str]] = []
    output: list[str] = []
    cursor = 0
    for match in ALIGNMENT_RE.finditer(text):
        output.append(text[cursor : match.start("body")])
        fixed_body, body_changes = _fix_alignment_body(match.group("body"))
        output.append(fixed_body)
        changes.extend(body_changes)
        cursor = match.end("body")
    output.append(text[cursor:])
    return "".join(output), changes


def _set_field(question: dict[str, Any], field: str, value: str) -> bool:
    """按 iter_fields 的字段名写回；返回是否命中。"""

    if field == "stem.text":
        question["stem"]["text"] = value
        return True
    match = re.match(r"^choices\[([^\]]+)\]\.text$", field)
    if match:
        label = match.group(1)
        for choice in question.get("choices") or []:
            if str(choice.get("label")) == label:
                choice["text"] = value
                return True
        return False
    match = re.match(r"^subparts\[(\d+)\]\.text$", field)
    if match:
        index = int(match.group(1))
        subparts = question.get("subparts") or []
        if index < len(subparts):
            subparts[index]["text"] = value
            return True
        return False
    return False


def _field_text(question: dict[str, Any], field: str) -> str:
    """按 iter_fields 的字段名取值。"""

    if field == "stem.text":
        return str((question.get("stem") or {}).get("text") or "")
    match = re.match(r"^choices\[([^\]]+)\]\.text$", field)
    if match:
        label = match.group(1)
        for choice in question.get("choices") or []:
            if str(choice.get("label")) == label:
                return str(choice.get("text") or "")
        return ""
    match = re.match(r"^subparts\[(\d+)\]\.text$", field)
    if match:
        index = int(match.group(1))
        subparts = question.get("subparts") or []
        if index < len(subparts):
            return str((subparts[index] or {}).get("text") or "")
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="写回题库（默认只报告）")
    parser.add_argument("--data-root", type=Path, help="覆盖 .npee-math-papers 数据根")
    parser.add_argument(
        "--json",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "tex-repairs.json",
        help="改动清单输出路径",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = NpeeService.create(args.data_root)
    store = service.context.store

    repairs: list[Repair] = []
    touched_papers: dict[str, dict[str, Any]] = {}

    for record in store.iter_records():
        modified: dict[str, Any] | None = None
        for question in record.questions:
            for field, text in list(iter_fields(question)):
                if not text:
                    continue
                override = CANONICAL_OVERRIDES.get(
                    (record.series_key, record.year, record.subject, record.paper_no, int(question["number"]), field)
                )
                if override is not None:
                    fixed = override(text)
                    changes = [(text, fixed)] if fixed != text else []
                else:
                    fixed, changes = fix_text(text)
                if not changes:
                    continue
                if modified is None:
                    import copy

                    modified = {
                        "series_key": record.series_key,
                        "year": record.year,
                        "subject": record.subject,
                        "paper_no": record.paper_no,
                        "questions": copy.deepcopy(record.questions),
                    }
                target_question = next(q for q in modified["questions"] if int(q["number"]) == int(question["number"]))
                if _set_field(target_question, field, fixed) and _field_text(target_question, field) == fixed:
                    for before, after in changes:
                        repairs.append(
                            Repair(record.natural_key, int(question["number"]), field, before, after)
                        )
        if modified is not None:
            touched_papers[record.natural_key] = modified

    print(f"需要修复：{len(repairs)} 处，涉及 {len(touched_papers)} 套")
    print("")
    for repair in repairs:
        print(f"  {repair.natural_key} q{repair.question_no} {repair.field}")
        print(f"    {repair.before!r}  ->  {repair.after!r}")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps([r.to_dict() for r in repairs], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not args.apply:
        print("")
        print(f"预览模式；加 --apply 写回。清单：{args.json.as_posix()}")
        return 0

    from npee_math_papers.core.store import PaperRecord

    applied = 0
    for key, payload in touched_papers.items():
        record = PaperRecord(
            series_key=payload["series_key"],
            year=payload["year"],
            subject=payload["subject"],
            paper_no=payload["paper_no"],
            questions=payload["questions"],
        )
        store.write_paper(record, replace=True)
        applied += 1
    store.rebuild_index()
    store.write_release()
    print("")
    print(f"已写回 {applied} 套，并重建索引与发布清单。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
