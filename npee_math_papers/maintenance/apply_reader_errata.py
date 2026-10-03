r"""按《贾基八十五套卷勘误收集》逐条回图核对后修正题库。

读者提交的 22 条勘误分成两类：

1. **识别错误**（``TRANSCRIPTION_FIXES``）——题库与源页不符，属我们自己的转写缺陷，
   本工具默认修正；
2. **来源书自身有误**（``SOURCE_FIXES``）——题库与源页一致，但源页本身印错
   （例如积分漏了导数符号）。题库以「忠实转写源页」为准，因此这类**默认不动**，
   需要显式 ``--include-source-fixes`` 才写入；是否改写题面属产品决策。

每条改动都给出源页路径与目视结论，可逐条复算：题面只来自
``.npee-math-papers/captures/<bundle>/unit-00N/pages/p####.png`` 的原生视觉观察。

写入后自动重建索引与发布清单，并把正式组卷包中的 ``content_hash`` 钉重新对齐
（``$subject`` 模板引用按它原先对应的科目重钉，保持既有封印约定）。

用法::

   python -m npee_math_papers.maintenance.apply_reader_errata            # 演练
   python -m npee_math_papers.maintenance.apply_reader_errata --apply
   python -m npee_math_papers.maintenance.apply_reader_errata --apply --include-source-fixes
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
sys.stdout.reconfigure(encoding="utf-8")

from npee_math_papers.core.store import PaperRecord  # noqa: E402
from npee_math_papers.service import NpeeService  # noqa: E402

#: 源页与题干不符 → 识别错误，属我方可确定性修复的缺陷。
TRANSCRIPTION_FIXES: list[dict] = [
    {
        "key": "2025/math1/chaoyue10/6",
        "question": 3,
        "field": "stem.text",
        "before": "+xy^2\\boldsymbol{j}",
        "after": "+xy^2z\\boldsymbol{j}",
        "page": "captures/chaoyue10-2025-math1/unit-006/pages/p0073.png",
        "evidence": "源页 q3 印 A=(y²z+x)i+xy²zj+(2xy+z²)k，第二分量带 z",
        "errata_row": 3,
    },
    {
        "key": "2025/math1/chaoyue10/6",
        "question": 13,
        "field": "stem.text",
        "before": "u=e^{xy}+\\dfrac{y^2}{z^2}",
        "after": "u=e^{xy}+\\dfrac{y}{z^2}",
        "page": "captures/chaoyue10-2025-math1/unit-006/pages/p0078.png",
        "evidence": "源页 q13 的分式分子是 y（不是 y²），分母 z²",
        "errata_row": 5,
    },
    {
        "key": "2025/math1/chaoyue10/6",
        "question": 17,
        "field": "stem.text",
        "before": "$f'_y(x,y)=2(y+1)e^x$",
        "after": "$f''_{xy}(x,y)=2(y+1)e^x$",
        "page": "captures/chaoyue10-2025-math1/unit-006/pages/p0080.png",
        "evidence": "源页 q17 印 f''_{xy}(x,y)=2(y+1)e^x（混合二阶偏导）",
        "errata_row": 6,
    },
    {
        "key": "2025/math2/chaoyue10/6",
        "question": 6,
        "field": "stem.text",
        "before": "\\int_0^{\\cos\\theta}",
        "after": "\\int_0^{\\frac{1}{\\cos\\theta}}",
        "page": "captures/chaoyue10-2025-math2/unit-006/pages/p0027.png",
        "evidence": "源页 q6 的内层积分上限是 1/cosθ（叠分数），不是 cosθ",
        "errata_row": 17,
    },
    {
        "key": "2025/math2/chaoyue10/6",
        "question": 8,
        "field": "stem.text",
        "before": "$A'$ 为 $A$ 的伴随矩阵",
        "after": "$A^*$ 为 $A$ 的伴随矩阵",
        "page": "captures/chaoyue10-2025-math2/unit-006/pages/p0028.png",
        "evidence": "源页 q8 印 A^*（伴随），不是 A'",
        "errata_row": 18,
    },
    {
        "key": "2025/math2/chaoyue10/6",
        "question": 8,
        "field": "stem.text",
        "before": "\\operatorname{tr}[(A-E)^2]",
        "after": "\\operatorname{tr}[(A-E)^*]",
        "page": "captures/chaoyue10-2025-math2/unit-006/pages/p0028.png",
        "evidence": "源页 q8 印 tr[(A-E)^*]（伴随），不是平方",
        "errata_row": 18,
    },
    {
        "key": "2025/math2/chaoyue10/6",
        "question": 12,
        "field": "stem.text",
        "before": "n\\left[f\\left(\\dfrac{1}{n}\\right)\\right]^n",
        "after": "\\left[nf\\left(\\dfrac{1}{n}\\right)\\right]^n",
        "page": "captures/chaoyue10-2025-math2/unit-006/pages/p0028.png",
        "evidence": "源页 q12 的 n 在方括号内：[n f(1/n)]^n",
        "errata_row": 19,
    },
    {
        "key": "2025/math2/chaoyue10/6",
        "question": 19,
        "field": "stem.text",
        "before": "f''_{yy}(x,y)=2(y+1)e^x",
        "after": "f''_{xy}(x,y)=2(y+1)e^x",
        "page": "captures/chaoyue10-2025-math2/unit-006/pages/p0030.png",
        "evidence": "源页 q19 印 f''_{xy}（先 x 后 y），不是 f''_{yy}",
        "errata_row": 22,
    },
    {
        "key": "2025/math3/chaoyue10/6",
        "question": 18,
        "field": "stem.text",
        "before": "f''_{yy}(x,y)=2(y+1)e^x",
        "after": "f''_{xy}(x,y)=2(y+1)e^x",
        "page": "captures/chaoyue10-2025-math3/unit-006/pages/p0081.png",
        "evidence": "数三同题（源页 q18）同样印 f''_{xy}；勘误未提及，属同批识别缺陷",
        "errata_row": None,
    },
    {
        "key": "2024/math1/chaoyue10/2",
        "question": 15,
        "field": "stem.text",
        "before": "r(A^4+2A^3-3E)",
        "after": "r(A^2+2A-3E)",
        "page": "captures/chaoyue10-2024-math1/unit-002/pages/p0008.png",
        "evidence": "源页 q15 印 r(A²+2A-3E)（数三同题亦为 A²+2A-3E）",
        "errata_row": 9,
    },
    {
        "key": "2024/math1/chaoyue10/2",
        "question": 18,
        "field": "stem.text",
        "before": "f''(t)+f'(t)=1",
        "after": "f''(t)+f(t)=1",
        "page": "captures/chaoyue10-2024-math1/unit-002/pages/p0008.png",
        "evidence": "源页 q18 印 f''(t)+f(t)=1（第二项无撇号）",
        "errata_row": 10,
    },
    {
        "key": "2024/math1/chaoyue10/2",
        "question": 10,
        "field": "choices.A.text",
        "before": "$\\left|\\dfrac{X_1-X_2}{X_3+X_4}\\right|\\sim t(2)$",
        "after": "$\\dfrac{X_1-X_2}{|X_3+X_4|}\\sim t(2)$",
        "page": "captures/chaoyue10-2024-math1/unit-002/pages/p0007.png",
        "evidence": "源页 A 选项分子无绝对值、分母有绝对值（数三同题同形）",
        "errata_row": 21,
    },
    {
        "key": "2024/math1/chaoyue10/3",
        "question": 6,
        "field": "stem.text",
        "before": "则矩阵 $A^*$ 与 $C^T$",
        "after": "则矩阵 $A^*$ 与 $C^*$",
        "page": "captures/chaoyue10-2024-math1/unit-003/pages/p0011.png",
        "evidence": "源页 q6 印 A^* 与 C^*（两者都是伴随）",
        "errata_row": 12,
    },
    {
        "key": "2024/math2/chaoyue10/3",
        "question": 9,
        "field": "stem.text",
        "before": "则矩阵 $A^*$ 与 $C^{\\mathrm{T}}$",
        "after": "则矩阵 $A^*$ 与 $C^*$",
        "page": "captures/chaoyue10-2024-math2/unit-003/pages/p0012.png",
        "evidence": "数二同题（源页 q9）同样印 A^* 与 C^*；勘误未提及，属同批识别缺陷",
        "errata_row": 12,
    },
    {
        "key": "2024/math1/zhangyu8/1",
        "question": 4,
        "field": "stem.text",
        "before": "\\oint_L ((2y)^3-3y)",
        "after": "\\oint_L (2y^3-3y)",
        "page": "captures/zhangyu8-2024-math1/unit-001/pages/p0002.png",
        "evidence": "源页 q4 印 2y³（系数 2 与 y³，不是 (2y)³）",
        "errata_row": 7,
    },
    {
        "key": "2024/math1/zhangyu8/2",
        "question": 4,
        "field": "stem.text",
        "before": "I_2=\\int_{\\Gamma}f(x,y)\\,\\mathrm{d}y",
        "after": "I_2=\\int_{\\Gamma}f(x,y)\\,\\mathrm{d}s",
        "page": "captures/zhangyu8-2024-math1/unit-002/pages/p0010.png",
        "evidence": "源页 q4 印 I₂=∫_Γ f(x,y)ds（弧长微元），不是对 y 积分",
        "errata_row": 16,
    },
    {
        "key": "2024/math2/zhangyu8/1",
        "question": 2,
        "field": "stem.figures[0].latex",
        "before": (
            "\\draw[thick] (0,2.45)..controls (0.6,2.35) and (1.1,2.05)..(1.6,1.65)"
            "..controls (2.6,0.75) and (3.9,0.75)..(5.3,1.65)"
            "..controls (5.9,2.15) and (6.5,2.30)..(6.9,2.20);"
            "\\draw[thick,dashed] (0,1.35)..controls (0.55,1.25) and (1.05,1.35)..(1.6,1.65)"
            "..controls (2.6,2.65) and (3.7,3.00)..(5.3,1.65)"
            "..controls (5.75,1.30) and (6.25,1.15)..(6.9,1.10);"
        ),
        "after": (
            "\\draw[thick] (0,1.35)..controls (0.55,1.25) and (1.05,1.35)..(1.6,1.65)"
            "..controls (2.6,2.65) and (3.7,3.00)..(5.3,1.65)"
            "..controls (5.75,1.30) and (6.25,1.15)..(6.9,1.10);"
            "\\draw[thick,dashed] (0,2.45)..controls (0.6,2.35) and (1.1,2.05)..(1.6,1.65)"
            "..controls (2.6,0.75) and (3.9,0.75)..(5.3,1.65)"
            "..controls (5.9,2.15) and (6.5,2.30)..(6.9,2.20);"
        ),
        "page": "captures/zhangyu8-2024-math2/unit-001/pages/p0001.png",
        "evidence": (
            "源图（数二 p1 q2、数一 p2 q2 两处同图）中实线在前、后两段位于下方、"
            "中段位于上方；原入库图把实线/虚线整体画反"
        ),
        "errata_row": 13,
    },
    {
        "key": "2025/math2/zhangyu4/4",
        "question": 17,
        "field": "stem.text",
        "before": "\\int_0^xe^{t^2}",
        "after": "\\int_0^{\\frac{1}{x}}e^{t^2}",
        "page": "captures/zhangyu4-2025-math2/unit-004/pages/p0013.png",
        "evidence": "源页 q17 的变上限积分上限是 1/x（叠分数），不是 x",
        "errata_row": 11,
    },
    {
        "key": "2024/math1/liyanfang3/1",
        "question": 15,
        "field": "stem.text",
        "before": "若 $a_{ij}+A_{ij}=1$",
        "after": "若 $a_{ij}+A_{ji}=1$",
        "page": "captures/liyanfang3-2024-math1/unit-001/pages/p0002.png",
        "evidence": "源页 q15 印 a_{ij}+A_{ji}=1（第二项下标为 ji）",
        "errata_row": 15,
    },
]

#: 题库与源页一致，但源页本身印错 → 属产品决策，默认不写。
SOURCE_FIXES: list[dict] = [
    {
        "key": "2024/math2/chaoyue10/5",
        "question": 18,
        "field": "stem.text",
        "before": "t^2[y(t)+1]",
        "after": "t^2[y'(t)+1]",
        "page": "captures/chaoyue10-2024-math2/unit-005/pages/p0023.png",
        "evidence": "源页 q18 确印 t²[y(t)+1]（无导数），与题库一致；同题在数一/数三卷次也有",
        "errata_row": 1,
        "rationale": "按原式解出 y 的表达式含 e^{±√2x}；补上导数后答案化简为 y=e^{2x}-x，疑为源书漏印撇号",
    },
    {
        "key": "2025/math1/chaoyue10/6",
        "question": 8,
        "field": "stem.text",
        "before": "④ $P(A\\cup\\overline{B})P(A\\overline{B})\\leq P(A)P(B)$。",
        "after": "④ $P(A\\cup B)P(AB)\\leq P(A)P(B)$。",
        "page": "captures/chaoyue10-2025-math1/unit-006/pages/p0075.png",
        "evidence": "源页 q8 的 ④ 确实印 P(A∪B̄)P(AB̄)≤P(A)P(B)（两处上划线），与题库一致",
        "errata_row": 4,
        "rationale": "读者主张去掉上划线；改动会改变命题真假与答案，需要用户确认",
    },
    {
        "key": "2024/math1/zhangyu8/2",
        "question": 5,
        "field": "stem.text",
        "before": "$\\begin{pmatrix}B&BC\\\\AB&O\\end{pmatrix}$",
        "after": "$\\begin{pmatrix}B&CB\\\\AB&O\\end{pmatrix}$",
        "page": "captures/zhangyu8-2024-math1/unit-002/pages/p0010.png",
        "evidence": "源页 q5 三个分块矩阵依次为 (O AB;B CB)、(B BC;AB O)、(BA BAC;O B)，题库逐字一致",
        "errata_row": 8,
        "rationale": "读者注明这是「张宇八套卷勘误、非文件错误」；题库与源页一致，改动即偏离来源",
    },
    {
        "key": "2024/math1/chaoyue10/2",
        "question": 4,
        "field": "choices.B.text",
        "before": "$\\oint_L y^2\\,\\mathrm{d}x=\\int_L x^2\\,\\mathrm{d}y$",
        "after": "$\\oint_L y^2\\,\\mathrm{d}x=\\oint_L x^2\\,\\mathrm{d}y$",
        "page": "captures/chaoyue10-2024-math1/unit-002/pages/p0006.png",
        "evidence": "源页 B 选项右侧确印开式 ∫_L（左侧为 ∮_L），与题库一致",
        "errata_row": 20,
        "rationale": "读者主张两侧都用封闭曲线积分；源书此处与 A、C、D 三项体例不一致，疑为源书漏印",
    },
]

_CHOICE_RE = re.compile(r"^choices\.([A-Z])\.text$")
_FIGURE_RE = re.compile(r"^stem\.figures\[(\d+)\]\.latex$")
_SUBPART_RE = re.compile(r"^subparts\.(\d+)\.text$")


def _field_text(question: dict, field: str) -> str:
    if field == "stem.text":
        return question["stem"]["text"]
    match = _CHOICE_RE.fullmatch(field)
    if match:
        label = match.group(1)
        for choice in question.get("choices") or []:
            if choice.get("label") == label:
                return choice["text"]
        raise KeyError(field)
    match = _SUBPART_RE.fullmatch(field)
    if match:
        index = int(match.group(1))
        return (question.get("subparts") or [])[index - 1]["text"]
    match = _FIGURE_RE.fullmatch(field)
    if match:
        index = int(match.group(1))
        return (question["stem"].get("figures") or [])[index]["latex"]
    raise KeyError(field)


def _set_field_text(question: dict, field: str, value: str) -> None:
    if field == "stem.text":
        question["stem"]["text"] = value
        return
    match = _CHOICE_RE.fullmatch(field)
    if match:
        label = match.group(1)
        for choice in question.get("choices") or []:
            if choice.get("label") == label:
                choice["text"] = value
                return
        raise KeyError(field)
    match = _SUBPART_RE.fullmatch(field)
    if match:
        index = int(match.group(1))
        question["subparts"][index - 1]["text"] = value
        return
    match = _FIGURE_RE.fullmatch(field)
    if match:
        index = int(match.group(1))
        (question["stem"].get("figures") or [])[index]["latex"] = value
        return
    raise KeyError(field)


def _pin_plan(store) -> list[dict]:
    """在改动题库**之前**判断每个 ``$subject`` 钉当前封印的是哪个科目。

    模板引用不参与绑定校验（见 ``core/composition.py::verify_bindings``），但正式组卷包
    按「math3 的哈希」封印。改动题库后需要按同一科目重钉，因此先记录对应关系。
    """

    lookup = store.content_hash_lookup()
    plan: list[dict] = []
    for path in sorted((REPOSITORY_ROOT / "composition").glob("*/composition.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        refs: list[tuple[int, int, dict]] = [
            (group_index, paper_index, paper)
            for group_index, group in enumerate(payload.get("groups") or [])
            for paper_index, paper in enumerate(group.get("papers") or [])
        ]
        matched_subjects: dict[tuple[int, int], str] = {}
        tally: dict[str, int] = {}
        for group_index, paper_index, paper in refs:
            if paper["subject"] != "$subject":
                continue
            key = f"{paper['year']}/{{subject}}/{paper['series_key']}/{paper['paper_no']}"
            matched = next(
                (
                    item
                    for item in ("math1", "math2", "math3")
                    if lookup.get(key.format(subject=item)) == paper.get("content_hash")
                ),
                None,
            )
            if matched:
                matched_subjects[(group_index, paper_index)] = matched
                tally[matched] = tally.get(matched, 0) + 1
        # 包内已过期的模板钉（换过题库的引用）沿用本包多数钉的封印口径。
        fallback = max(tally, key=lambda item: tally[item]) if tally else None
        for group_index, paper_index, paper in refs:
            subject = paper["subject"]
            key = f"{paper['year']}/{{subject}}/{paper['series_key']}/{paper['paper_no']}"
            if subject != "$subject":
                plan.append(
                    {
                        "path": path, "group": group_index, "paper": paper_index,
                        "lookup_key": key.format(subject=subject),
                    }
                )
                continue
            sealed = matched_subjects.get((group_index, paper_index), fallback)
            if sealed is None:
                continue
            plan.append(
                {
                    "path": path, "group": group_index, "paper": paper_index,
                    "lookup_key": key.format(subject=sealed),
                }
            )
    return plan


def _repin_compositions(store, plan: list[dict]) -> list[str]:
    """按预先记录的口径把组卷包里的 content_hash 钉对齐到当前题库。"""

    lookup = store.content_hash_lookup()
    notes: list[str] = []
    cache: dict[Path, dict] = {}
    counts: dict[Path, int] = {}
    for item in plan:
        path = item["path"]
        payload = cache.get(path)
        if payload is None:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cache[path] = payload
        paper = payload["groups"][item["group"]]["papers"][item["paper"]]
        current = lookup.get(item["lookup_key"])
        if current and current != paper.get("content_hash"):
            paper["content_hash"] = current
            counts[path] = counts.get(path, 0) + 1
    for path, payload in cache.items():
        if not counts.get(path):
            continue
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        notes.append(f"{path.relative_to(REPOSITORY_ROOT).as_posix()} 重钉 {counts[path]} 条")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="写回题库")
    parser.add_argument(
        "--include-source-fixes",
        action="store_true",
        help="同时写入「源书自身有误」的改写（默认不动，见文件头说明）",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("build/reader-errata-repairs.json"),
        help="改动清单输出路径",
    )
    args = parser.parse_args()

    service = NpeeService.create()
    store = service.context.store
    records = {record.natural_key: record for record in store.iter_records()}
    # 组卷包的 content_hash 封印口径要在改动题库之前记录（见 _pin_plan）。
    pin_plan = _pin_plan(store)

    plan: list[dict] = []
    edits: list[dict] = []
    for group_name, fixes, enabled in (
        ("识别错误", TRANSCRIPTION_FIXES, True),
        ("源书自身有误", SOURCE_FIXES, args.include_source_fixes),
    ):
        for fix in fixes:
            record = records.get(fix["key"])
            if record is None:
                plan.append({**fix, "group": group_name, "status": "缺少套卷"})
                continue
            question = next(
                (
                    item
                    for item in record.questions
                    if int(item["number"]) == int(fix["question"])
                ),
                None,
            )
            if question is None:
                plan.append({**fix, "group": group_name, "status": "缺少题号"})
                continue
            text = _field_text(question, fix["field"])
            if fix["after"] in text:
                status = "已是目标值"
            elif fix["before"] not in text:
                status = "锚点未命中"
            else:
                status = "待改写" if enabled else "待用户确认"
            plan.append({**fix, "group": group_name, "status": status})
            if status == "待改写":
                edits.append({"fix": fix, "record": record, "question_number": int(fix["question"])})

    print(f"共 {len(plan)} 条：待改写 {sum(1 for x in plan if x['status'] == '待改写')}，"
          f"待用户确认 {sum(1 for x in plan if x['status'] == '待用户确认')}，"
          f"已是目标值 {sum(1 for x in plan if x['status'] == '已是目标值')}，"
          f"异常 {sum(1 for x in plan if x['status'] in ('缺少套卷', '缺少题号', '锚点未命中'))}")
    for item in plan:
        print()
        print(f"[{item['group']}] {item['key']} q{item['question']} {item['field']} -> {item['status']}")
        print(f"    源页: .npee-math-papers/{item['page']}")
        print(f"    依据: {item['evidence']}")
        print(f"    BEFORE: {item['before']}")
        print(f"    AFTER : {item['after']}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print()
    print(f"清单：{args.report.as_posix()}")

    if not args.apply:
        print("预览模式；加 --apply 写回。")
        return 0

    touched: dict[str, PaperRecord] = {}
    applied = 0
    for edit in edits:
        record = edit["record"]
        fix = edit["fix"]
        payload = touched.get(record.natural_key)
        if payload is None:
            payload = PaperRecord(
                record.series_key,
                record.year,
                record.subject,
                record.paper_no,
                copy.deepcopy(record.questions),
            )
            touched[record.natural_key] = payload
        question = next(
            item for item in payload.questions if int(item["number"]) == edit["question_number"]
        )
        text = _field_text(question, fix["field"])
        _set_field_text(question, fix["field"], text.replace(fix["before"], fix["after"], 1))
        applied += 1

    for payload in touched.values():
        store.write_paper(payload, replace=True)
    store.rebuild_index()
    store.write_release()
    print()
    print(f"已写回 {applied} 处改动，涉及 {len(touched)} 套，并重建索引与发布清单。")

    notes = _repin_compositions(store, pin_plan)
    for note in notes:
        print("  ", note)
    if not notes:
        print("   组卷包 content_hash 无需重钉。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
