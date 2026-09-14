"""审计题库中的历史 TeX 写法。

原理
----
渲染构建器 ``validate_inline_tex`` 里有一层"修复"，会在生成 TeX 时改写若干历史
遗留写法。这些修复让 PDF 能正确编译，但也掩盖了存储层的问题：

- 问题会随数据复制而扩散；
- 新读取者（如前端预览）看到的仍是坏写法；
- 修复逻辑越堆越多，难以判断"源数据到底对不对"。

因此本工具把**存储原文**与**修复后文本**逐字段对比，凡有差异即为需要前移到入库
阶段的候选。同时按模式独立扫描，便于分类与判定真伪。

用法::

    python -m npee_math_papers.maintenance.audit_tex
    python -m npee_math_papers.maintenance.audit_tex --sample 5
    python -m npee_math_papers.maintenance.audit_tex --json build/tex-audit.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from npee_math_papers.core.tex_audit import iter_fields  # noqa: E402,F401
from npee_math_papers.core.store import NpeePaths, PaperStore  # noqa: E402
from npee_math_papers.service.tex_builder import validate_inline_tex  # noqa: E402


@dataclass
class Finding:
    """一处可疑写法。"""

    natural_key: str
    question_no: int
    field: str
    category: str
    before: str
    after: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "natural_key": self.natural_key,
            "question_no": self.question_no,
            "field": self.field,
            "category": self.category,
            "before": self.before,
            "after": self.after,
            "note": self.note,
        }


# --- 独立模式扫描：与构建器无关，用于判定真伪 ---------------------------------

# 单反斜杠 + 大写字母/数字，且后面不接字母：极可能是被吃掉一个反斜杠的行分隔符。
SINGLE_SLASH_CAPITAL_RE = re.compile(r"(?<!\\)\\([A-Z0-9])(?![A-Za-z])")
# 双反斜杠 + 常见数学命令：重复转义。
DOUBLED_COMMAND_RE = re.compile(
    r"(?<!\\)\\\\(ne|le|ge|frac|dfrac|lambda|sim|chi|alpha|beta|gamma|mu|nu|sigma|rho|eta|hat|infty|Delta|Sigma|Omega|Gamma|Phi)\b"
)
# 双反斜杠 + 花括号：重复花括号转义。
DOUBLED_BRACE_RE = re.compile(r"(?<!\\)\\\\[{}]")
# 双反斜杠 + 百分号。
DOUBLED_PERCENT_RE = re.compile(r"(?<!\\)\\\\%")
# 非标准黑板粗体。
NONSTANDARD_BB_RE = re.compile(r"\\bb\b(?!\{)")
# 数学模式内的 textcircled。
TEXTCIRCLED_RE = re.compile(r"\\textcircled")
# 文本模式单位指数，如 m/s^2。
UNIT_EXPONENT_RE = re.compile(r"(?<![\\$])\b[A-Za-z]+/[A-Za-z]+\^[0-9]")
# 占位符后直接跟中文。
PLACEHOLDER_CJK_RE = re.compile(r"\\Exam(?:Selection|Blank)(?=[\u3400-\u9fff])")
# 字面量换行。
LITERAL_NEWLINE_RE = re.compile(r"(?<!\\)\\n(?![A-Za-z])")
# 文本模式的单列 array。
TEXT_ARRAY_RE = re.compile(r"\\begin\{array\}\{l\}")

CATEGORY_LABELS = {
    "render_repair": "构建器修复了该字段",
    "single_slash_capital": "单反斜杠后接大写字母/数字",
    "doubled_command": "数学命令被重复转义",
    "doubled_brace": "花括号被重复转义",
    "doubled_percent": "百分号被重复转义",
    "nonstandard_bb": "非标准黑板粗体 \\bb",
    "textcircled_in_math": "数学模式内使用 \\textcircled",
    "unit_exponent": "文本模式单位指数",
    "placeholder_cjk": "占位符后直接接中文",
    "literal_newline": "字面量换行 \\n",
    "text_array": "文本模式单列 array",
}




def scan_text(text: str, field: str, key: str, question_no: int) -> list[Finding]:
    """对一个字段做独立模式扫描。"""

    findings: list[Finding] = []
    patterns = [
        ("single_slash_capital", SINGLE_SLASH_CAPITAL_RE),
        ("doubled_command", DOUBLED_COMMAND_RE),
        ("doubled_brace", DOUBLED_BRACE_RE),
        ("doubled_percent", DOUBLED_PERCENT_RE),
        ("nonstandard_bb", NONSTANDARD_BB_RE),
        ("textcircled_in_math", TEXTCIRCLED_RE),
        ("unit_exponent", UNIT_EXPONENT_RE),
        ("placeholder_cjk", PLACEHOLDER_CJK_RE),
        ("literal_newline", LITERAL_NEWLINE_RE),
        ("text_array", TEXT_ARRAY_RE),
    ]
    for category, pattern in patterns:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            findings.append(
                Finding(
                    natural_key=key,
                    question_no=question_no,
                    field=field,
                    category=category,
                    before=text[start:end],
                    after=match.group(0),
                )
            )
    return findings


def compare_with_render(text: str, field: str, key: str, question_no: int) -> Finding | None:
    """对比存储原文与构建器修复结果，有差异即记录。"""

    try:
        repaired = validate_inline_tex(text, field)
    except Exception as error:
        return Finding(
            natural_key=key,
            question_no=question_no,
            field=field,
            category="render_reject",
            before=text[:200],
            after="",
            note=str(error)[:200],
        )
    if repaired != text:
        return Finding(
            natural_key=key,
            question_no=question_no,
            field=field,
            category="render_repair",
            before=text[:200],
            after=repaired[:200],
        )
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", type=int, default=3, help="每类展示的样本数")
    parser.add_argument("--json", type=Path, help="把完整结果写入 JSON 文件")
    parser.add_argument("--data-root", type=Path, help="覆盖 .npee-math-papers 数据根")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = PaperStore(NpeePaths.resolve(args.data_root, repository_root=REPOSITORY_ROOT))

    findings: list[Finding] = []
    papers_scanned = 0
    fields_scanned = 0
    for record in store.iter_records():
        papers_scanned += 1
        for question in record.questions:
            for field, text in iter_fields(question):
                if not text:
                    continue
                fields_scanned += 1
                findings.extend(scan_text(text, field, record.natural_key, int(question["number"])))
                repair = compare_with_render(text, field, record.natural_key, int(question["number"]))
                if repair is not None:
                    findings.append(repair)

    by_category: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_category[finding.category].append(finding)

    print(f"扫描：{papers_scanned} 套 / {fields_scanned} 个字段")
    print(f"发现：{len(findings)} 处，分 {len(by_category)} 类")
    print("")

    for category in sorted(by_category, key=lambda name: -len(by_category[name])):
        items = by_category[category]
        affected = len({item.natural_key for item in items})
        label = CATEGORY_LABELS.get(category, category)
        print(f"[{len(items):4d}] {category:<24} {label}")
        print(f"       涉及 {affected} 套")
        for sample in items[: args.sample]:
            snippet = sample.before.replace("\n", " ")[:80]
            print(f"       - {sample.natural_key} q{sample.question_no} {sample.field}")
            print(f"         {snippet}")
        print("")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "papers_scanned": papers_scanned,
                    "fields_scanned": fields_scanned,
                    "finding_count": len(findings),
                    "categories": {
                        category: {"count": len(items), "items": [item.to_dict() for item in items]}
                        for category, items in by_category.items()
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"完整结果已写入 {args.json.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
