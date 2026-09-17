"""生成「提取简报」：把一个 bundle 的转写任务规范成一份可直接交付的文档。

背景
----
按套卷提取题面时，每个子代理都需要一份简报：自然键、来源 PDF 与 sha256、capture
与页码范围、题目结构、schema 形状、排版约定、工具调用顺序、校验失败对照。此前这些
简报是**逐份手写**的，于是同一个批次里出现了三类漂移：

- 措辞不一致：同一件事在不同简报里写法不同，子代理按哪份做都可能；
- 数字漂移：题目结构或分值抄错，甚至照搬了另一个科目的结构；
- 新 bundle 要从头抄一遍，容易漏掉边界条款（禁止项、只写 staging 等）。

本工具把简报变成**由题库事实生成**的产物：

- 来源哈希、页数、capture 与页码范围取自用例层，不可能与来源记录不一致；
- 题目结构与分值取自「同系列、同科目、已完成」的对照套卷；
- 找不到同类对照时退回库级约定，并在简报里**显式标注**这是默认值，提示需要复核。

用法::

    # 预览（默认只打印）
    python -m npee_math_papers.maintenance.extraction_brief --series lilin6 --year 2027 --subject math2

    # 写入 staging/<bundle>/BRIEF.md，供子代理直接读取
    python -m npee_math_papers.maintenance.extraction_brief --series lilin6 --year 2027 --subject math2 --write
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from npee_math_papers.core.canonical import natural_key  # noqa: E402
from npee_math_papers.core.domain import SECTION_LABELS, SECTIONS, SUBJECT_LABELS  # noqa: E402
from npee_math_papers.core.errors import NpeeError  # noqa: E402
from npee_math_papers.service import NpeeService  # noqa: E402

#: 库级约定：题库里每一套卷都是这个形状，但没有同类对照时才使用它。
DEFAULT_COUNTS: dict[str, int] = {"choice": 10, "fill": 6, "solution": 6}
DEFAULT_POINTS: dict[str, tuple[int, ...]] = {"choice": (5,), "fill": (5,), "solution": (10, 12)}

#: 记号约定：转写时最容易被各人写成不同样子的写法。清单是人工挑的（挑的是
#: 会影响渲染的写法），计数在生成时**从题库实测**，因此简报里的数字是可复核的事实，
#: 而不是谁记得的规范。
NOTATION_PROBES: tuple[tuple[str, str], ...] = (
    (r"\mathrm{d}", "微分符号写成 \\mathrm{d}，不要写成普通 d"),
    (r"\mathrm{e}", "自然对数底写成 \\mathrm{e}"),
    (r"\mathrm{T}", "转置写成 \\mathrm{T}"),
    (r"\boldsymbol{", "向量/矩阵用 \\boldsymbol{...}"),
    (r"\begin{pmatrix}", "矩阵用 pmatrix 环境"),
    (r"\begin{cases}", "分段函数用 cases 环境"),
    (r"\dfrac{\partial", "偏导写成 \\dfrac{\\partial ...}{\\partial ...}"),
    (r"\operatorname{tr}", "矩阵的迹用 \\operatorname{tr}"),
)

def measure_notation(service: NpeeService) -> list[tuple[str, str, int]]:
    """在整个题库上实测记号写法；返回 (token, 说明, 次数)，按次数降序。"""

    import re as _re

    blob: list[str] = []
    for path in sorted((ROOT / ".npee-math-papers" / "papers").glob("*/*.yaml")):
        blob.append(path.read_text(encoding="utf-8"))
    text = "\n".join(blob)
    rows = []
    for token, note in NOTATION_PROBES:
        count = len(_re.findall(_re.escape(token), text))
        if count:
            rows.append((token, note, count))
    rows.sort(key=lambda row: -row[2])
    return rows

PAGE_GLOB = ".npee-math-papers/captures/{bundle}/{capture_id}/pages/p####.png"
STAGING = ".npee-math-papers/staging/{bundle}"

def format_points(values: tuple[int, ...]) -> str:
    """把分值集合写成「每题 5 分」或「10 / 12 分」。"""

    if len(values) == 1:
        return "每题 " + str(values[0]) + " 分"
    return " / ".join(str(v) for v in values) + " 分"

def derive_structure(records):
    """从对照套卷推导 (题数, 分值, 参照自然键)。

    以出现次数最多的形状为准，因此个别套卷的分值缺记（题库里确实存在 points=null
    的题）不会污染结论。
    """

    if not records:
        return dict(DEFAULT_COUNTS), dict(DEFAULT_POINTS), ""

    shape: Counter = Counter()
    points: dict[str, Counter] = {name: Counter() for name in SECTIONS}
    for _series, _year, _subject, _paper_no, questions in records:
        counts = Counter(q.get("section") for q in questions)
        shape[tuple(counts.get(name, 0) for name in SECTIONS)] += 1
        for question in questions:
            name = question.get("section")
            value = question.get("points")
            if name in points and isinstance(value, (int, float)) and not isinstance(value, bool):
                points[name][int(value)] += 1

    best = shape.most_common(1)[0][0] if shape else tuple(DEFAULT_COUNTS[n] for n in SECTIONS)
    counts = dict(zip(SECTIONS, best))
    resolved: dict[str, tuple[int, ...]] = {}
    for name in SECTIONS:
        resolved[name] = tuple(v for v, _ in sorted(points[name].items())) or DEFAULT_POINTS[name]
    first = records[0]
    # The natural key has a canonical spelling; building it by hand here once
    # produced "1/math2/lilin6/2025" instead of "2025/math2/lilin6/1".
    key = natural_key(first[1], first[2], first[0], first[3])
    return counts, resolved, key

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--series", required=True, help="series_key，例如 lilin6")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--subject", required=True, choices=("math1", "math2", "math3"))
    parser.add_argument("--data-root", type=Path, help="覆盖 .npee-math-papers 数据根")
    parser.add_argument("--write", action="store_true", help="写入 staging/<bundle>/BRIEF.md（默认只打印）")
    return parser.parse_args()

def build(service: NpeeService, series_key: str, year: int, subject: str) -> str:
    bundle = series_key + "-" + str(year) + "-" + subject
    series_name = next(
        (row["series_name"] for row in service.library.list_series() if row["series_key"] == series_key),
        series_key,
    )
    subject_label = SUBJECT_LABELS.get(subject, subject)

    sources = [row for row in service.extraction.list_sources() if row["bundle"] == bundle]
    source = sources[0] if sources else None
    captures = sorted(
        service.extraction.list_captures(series_key=series_key, year=year, subject=subject),
        key=lambda row: row["capture_id"],
    )

    # 对照套卷：同系列同科目，排除本次正在提取的这一年。
    references = []
    for row in service.library.list_papers(series_keys=[series_key], subjects=[subject], limit=None)["papers"]:
        if row["year"] == year:
            continue
        record = service.context.store.read_paper(
            row["series_key"], row["year"], row["subject"], row["paper_no"]
        )
        references.append((row["series_key"], row["year"], row["subject"], row["paper_no"], record.questions))

    counts, points, reference = derive_structure(references)
    total = sum(counts.values())
    from_default = not reference

    out: list[str] = []
    out.append("# 提取简报：" + bundle + "（" + series_name + " · " + str(year) + " · " + subject_label + "）")
    out.append("")
    out.append("> 本文件由 `python -m npee_math_papers.maintenance.extraction_brief --write` 生成。")
    out.append("> 来源哈希、capture 与页码取自题库与来源记录；请勿手工编辑，改动会被下次生成覆盖。")
    out.append("")
    out.append("## 一、任务边界")
    out.append("")
    out.append("- 自然键：`series_key=" + series_key + "`、`year=" + str(year) + "`、`subject=" + subject + "`。")
    out.append("- 系列名：`" + series_name + "`（写入时作为 `series_name` 传入）。")
    if source:
        sha = source.get("sha256") or ""
        line = "- 来源 PDF 已登记，sha256 `" + (sha[:16] + "…" if sha else "（未记录）") + "`"
        if source.get("page_count"):
            line += "，共 " + str(source["page_count"]) + " 页。"
        else:
            line += "。"
        out.append(line)
    else:
        out.append("- **来源未登记**：先用 `npee_register_source` 登记来源 PDF，再开始转写。")

    if captures:
        out.append("")
        out.append("| paper_no | capture_id | 源页 |")
        out.append("| --- | --- | --- |")
        for index, row in enumerate(captures, 1):
            pages = row.get("question_pages") or []
            span = str(pages[0]) + "-" + str(pages[-1]) if pages else "（未登记）"
            out.append("| " + str(index) + " | `" + row["capture_id"] + "` | " + span + " |")
        out.append("")
        out.append("页面 PNG：`" + PAGE_GLOB.format(bundle=bundle, capture_id=captures[0]["capture_id"]) + "`")
    else:
        out.append("- **没有对应 capture**：先 `npee_capture_pdf` 或 `npee_prepare_capture` 建好页面，再开始转写。")
    out.append("")
    out.append("- **题面只来自页面 PNG 的视觉观察**。禁止 OCR、PDF 文本层、公式识别器、复制粘贴、凭记忆作答。")
    out.append("- 不读答案、解析、勘误、答题卡、封面、广告。")
    out.append("")

    out.append("## 二、每套卷的结构（" + str(total) + " 题）")
    out.append("")
    if from_default:
        out.append("> ⚠️ 同系列暂无已完成套卷可作对照，以下为**库级默认结构**，请对着来源页面复核后再用。")
        out.append("")
    index = 1
    for name in SECTIONS:
        if counts.get(name):
            last = index + counts[name] - 1
            out.append("- " + SECTION_LABELS[name] + " " + str(index) + "~" + str(last) + "：" + format_points(points[name]) + "，共 " + str(counts[name]) + " 题。")
            index = last + 1
    if reference:
        out.append("")
        out.append("结构取自对照套卷 `" + reference + "`。")
    out.append("")

    out.append("## 三、schema 3.0 题目形状")
    out.append("")
    out.append("```json")
    out.append("{")
    out.append('  "number": 1, "section": "choice", "points": 5,')
    out.append('  "stem": {"text": "...", "figures": []},')
    out.append('  "choices": [')
    out.append('    {"label": "A", "text": "...", "figures": []},')
    out.append('    {"label": "B", "text": "...", "figures": []},')
    out.append('    {"label": "C", "text": "...", "figures": []},')
    out.append('    {"label": "D", "text": "...", "figures": []}')
    out.append("  ],")
    out.append('  "subparts": []')
    out.append("}")
    out.append("```")
    out.append("")
    out.append("- `stem` 与 `subparts` 的块是 `{text, figures}`；选项是 `{label, text, figures}`。")
    out.append("- `section` 只能是 `choice` / `fill` / `solution`。")
    out.append("- `choice` 必须有且仅有 A/B/C/D 四项，标签顺序固定；`fill` / `solution` 不能带 `choices`。")
    out.append("- 子问放 `subparts`，每项 `{text, figures}`。")
    out.append('- 图形优先 `kind:"tikz"` 内嵌自包含 `tikzpicture`；确无法重绘才 `kind:"asset"`，并填 `path` 与 `exception_reason`。')
    out.append("")
    out.append("### 排版约定")
    out.append("")
    out.append(r"- 选择题题干结尾加 `\ExamSelection`（选项文本**不要**带 `A.` 前缀）。")
    out.append(r"- 填空题题干结尾加 `\ExamBlank.`（带句点）；填空题不带 `choices`。")
    out.append("- 解答题题干以 `（本题满分 X 分）` 开头，紧接题目内容。")
    out.append(r"- 行内公式一律 `$...$`；分式一律 `\dfrac`，**禁止 `\frac`**；**禁止 `$$` 块级公式**。")
    out.append(r"- 数学模式内不要直接写中文；中文用 `\text{...}` 包起来。")
    out.append(r"- 不要残留 `[待核]` 之类的待审标记。")
    out.append(r"- 只用 `\ExamSelection` / `\ExamBlank` 这两个项目自定义宏。")
    out.append("")

    staging = STAGING.format(bundle=bundle)
    notation = measure_notation(service)
    if notation:
        out.append("### 记号约定（全库实测）")
        out.append("")
        out.append("下面每一行的出现次数是在**整个题库**上数出来的，照此写法才能与既有套卷一致：")
        out.append("")
        out.append("| 写法 | 说明 | 全库出现 |")
        out.append("| --- | --- | --- |")
        for token, note, count in notation:
            out.append("| `" + token.replace("\\", "\\") + "` | " + note + " | " + str(count) + " |")
        out.append("")

    out.append("## 四、执行流程（三个角色，可分别交给三个子代理）")
    out.append("")
    out.append("| 角色 | 做什么 | 写什么 | 不做什么 |")
    out.append("| --- | --- | --- | --- |")
    out.append("| A 转写 | 读页面 PNG，逐题转写成 schema 3.0 | `" + staging + "/paper-<N>.json` | 不调写入工具 |")
    out.append("| B 入库 | 读 A 的 JSON，校验后写入并复核 | 题库 | 不读整页图 |")
    out.append("| V 核对 | 拿入库文本与源页面图**逐题**对照 | `verify-paper-<N>.md`（必要时 `paper-<N>-fixed.json`） | 不写题库 |")
    out.append("")
    out.append("B 的调用序列：")
    out.append("")
    out.append("```text")
    out.append("1. npee_validate_questions(questions=[...])                  直到 ok: true")
    out.append("2. npee_ingest_paper(series_key=\"" + series_key + "\", year=" + str(year) + ", subject=\"" + subject + "\",")
    out.append("       paper_no=<N>, questions=[...], series_name=\"" + series_name + "\",")
    out.append("       capture_id=\"<capture_id>\", replace=false)")
    out.append("3. npee_diagnose_paper(series_key=\"" + series_key + "\", year=" + str(year) + ", subject=\"" + subject + "\", paper_no=<N>)")
    out.append("```")
    out.append("")
    out.append("- `paper already exists` 说明该套已写入：用 `npee_get_paper` 核对即可，**不要**加 `replace`。")
    out.append("- `diagnose` 渲染较重，客户端可能超时（>120s）；先用 `npee_get_paper` 确认已落盘，再决定是否重试。")
    out.append("- `leaked_command: \"arctan\"` / `\"arcsin\"` 是**已知误报**（合法算子名），可忽略；其它 problem 必须修复。")
    out.append("")

    out.append("## 五、校验失败对照")
    out.append("")
    out.append("| 报错 | 处理 |")
    out.append("| --- | --- |")
    out.append(r"| `contains block math` | 改用行内 `$...$` |")
    out.append(r"| `uses \frac` | 改用 `\dfrac` |")
    out.append("| `choice requires exactly four options` | 补齐 A/B/C/D |")
    out.append("| `contains CJK text or punctuation in math mode` | 用 `\\text{...}` 包裹中文 |")
    out.append("| `pending visual-review marker` | 删除 `[待核]` |")
    out.append("| `paper already exists` | 该套已写入，不要再写 |")
    out.append("")

    if reference:
        ref_year, ref_subject, ref_series, ref_no = reference.split("/")
        out.append("## 六、参考样例")
        out.append("")
        out.append("同系列已完成的套卷，可直接读取作对照：")
        out.append("")
        out.append("- `.npee-math-papers/papers/" + ref_series + "-" + ref_year + "-" + ref_subject + "/" + ref_no + ".yaml`")
        out.append("")

    return "\n".join(out).rstrip() + "\n"

def main() -> int:
    args = parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        service = NpeeService.create(args.data_root)
    except NpeeError as error:
        print("extraction_brief: error: " + str(error), file=sys.stderr)
        return 2

    brief = build(service, args.series, args.year, args.subject)
    if not args.write:
        print(brief, end="")
        return 0

    target = ROOT / ".npee-math-papers" / "staging" / (args.series + "-" + str(args.year) + "-" + args.subject) / "BRIEF.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(brief, encoding="utf-8", newline="\n")
    print("已写入 " + target.relative_to(ROOT).as_posix())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
