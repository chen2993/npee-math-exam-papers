"""Re-transcribe zhangyu4-2026-math1 paper 3 from the source page images.

Why this exists
---------------
``.npee-math-papers/sources/zhangyu4-2026-math1/source.pdf`` is an *imposition*
file: 8 physical pages, all landscape, each holding two logical pages side by
side.  capture ``unit-003`` originally recorded the page range [4, 5], which in
reality held 预测卷（二）'s first two logical pages plus 预测卷（三）'s last page.
The capture was later corrected to physical page 6 (预测卷（三）'s first two
logical pages), but **the stored paper 3 was never rebuilt**, so it still mixes
two papers: q1--q17 are 预测卷（二）'s and q18--q22 are 预测卷（三）'s.

This pass rewrites paper 3 as 预测卷（三）:

* q1--q17 are transcribed from the page images of
  ``captures/zhangyu4-2026-math1/unit-003/pages/p0006.png``
  (left half = 第 1 页, q1--q8; right half = 第 2 页, q8--q17);
* q18--q22 are kept from the source page 预测卷（三）第 3 页
  (``.../unit-003/pages/p0005.png``) and are already stored correctly.

The transcription follows ``docs/EXTRACTION.md`` (schema 3.0, ``\\ExamSelection``
/ ``\\ExamBlank`` endings, ``\\dfrac`` in body positions and ``\\frac`` in
scripts, the ``\\n`` proposition-sequence template).

Usage::

   python -m npee_math_papers.maintenance.retranscribe_zhangyu4_paper3            # dry run
   python -m npee_math_papers.maintenance.retranscribe_zhangyu4_paper3 --apply
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

SERIES_KEY = "zhangyu4"
YEAR = 2026
SUBJECT = "math1"
PAPER_NO = 3

#: 预测卷（三）, q1--q17, transcribed from ``unit-003/pages/p0006.png``.
TRANSCRIBED: list[dict] = [
    {
        "number": 1,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设 $f(x)=\int_0^x(x-2t)e^{-t^2}\,\mathrm{d}t\ (x\geq 0)$，$g(x)=\int_0^x(x-2t)\sin t^2\,\mathrm{d}t$，则\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$f(x)$ 单调增加，$g(x)$ 是奇函数。"},
            {"label": "B", "text": r"$f(x)$ 单调增加，$g(x)$ 是偶函数。"},
            {"label": "C", "text": r"$f(x)$ 单调减少，$g(x)$ 是奇函数。"},
            {"label": "D", "text": r"$f(x)$ 单调减少，$g(x)$ 是偶函数。"},
        ],
    },
    {
        "number": 2,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设函数 $f(x)$ 在 $[0,1]$ 上二阶可导，则\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"当 $f'(x)<0$ 时，$f\left(\dfrac{1}{2}\right)<\int_0^1f(x)\,\mathrm{d}x$。"},
            {"label": "B", "text": r"当 $f'(x)>0$ 时，$f\left(\dfrac{1}{2}\right)<\int_0^1f(x)\,\mathrm{d}x$。"},
            {"label": "C", "text": r"当 $f''(x)<0$ 时，$f\left(\dfrac{1}{3}\right)<\int_0^1f(x^2)\,\mathrm{d}x$。"},
            {"label": "D", "text": r"当 $f''(x)>0$ 时，$f\left(\dfrac{1}{3}\right)<\int_0^1f(x^2)\,\mathrm{d}x$。"},
        ],
    },
    {
        "number": 3,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"已知函数 $f(x,y)$ 满足 $f(0,0)=0$，设 $\boldsymbol{n}=(f'_x(0,0),f'_y(0,0),-1)$，$\boldsymbol{\alpha}=(x,y,f(x,y))$，则 $\boldsymbol{n}\cdot\boldsymbol{\alpha}=0$ 是 $f(x,y)$ 在点 $(0,0)$ 处可微的\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"充分非必要条件。"},
            {"label": "B", "text": r"必要非充分条件。"},
            {"label": "C", "text": r"充分必要条件。"},
            {"label": "D", "text": r"既非充分也非必要条件。"},
        ],
    },
    {
        "number": 4,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设 $f'(x)>0$，$f''(x)<0$，$x>0$，对任意的正整数 $n$，记 $I_1=\dfrac{1}{2}\left[f(n+1)-f(n)\right]$，$I_2=f(n)-f\left(\dfrac{2n-1}{2}\right)$，$I_3=f\left(\dfrac{2n+1}{2}\right)-f(n)$，则\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$I_1>I_2>I_3$。"},
            {"label": "B", "text": r"$I_1>I_3>I_2$。"},
            {"label": "C", "text": r"$I_2>I_1>I_3$。"},
            {"label": "D", "text": r"$I_2>I_3>I_1$。"},
        ],
    },
    {
        "number": 5,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设 $n$ 阶矩阵 $A,B,C$ 满足 $r(ABC)+2n=r(A)+r(B)+r(C)$，则\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$r(A)+r(B)+r(C)=r(AB)$。"},
            {"label": "B", "text": r"$r(AB)+n=r(A)+r(B)$。"},
            {"label": "C", "text": r"$r(ABC)>r(A)+r(BC)-n$。"},
            {"label": "D", "text": r"$r(AB)=r(BC)=n$。"},
        ],
    },
    {
        "number": 6,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设矩阵 $\begin{pmatrix}1&2&0\\2&a&1\\0&1&b\end{pmatrix}$ 有 $2$ 个正特征值和 $1$ 个负特征值，则\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$a>4$，$b>1$。"},
            {"label": "B", "text": r"$a<4$，$b>1$。"},
            {"label": "C", "text": r"$(a-4)b>1$。"},
            {"label": "D", "text": r"$(a-4)b<1$。"},
        ],
    },
    {
        "number": 7,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设 $\boldsymbol{\alpha}_1,\boldsymbol{\alpha}_2,\boldsymbol{\alpha}_3,\boldsymbol{\alpha}_4$ 是 $n$ 维非零列向量，$x_1\boldsymbol{\alpha}_1+x_2\boldsymbol{\alpha}_2=\boldsymbol{\alpha}_3$ 有唯一解，且 $\boldsymbol{\alpha}_1,\boldsymbol{\alpha}_2,\boldsymbol{\alpha}_4$ 线性相关。在空间直角坐标系 $O-xyz$ 中，关于 $x,y,z$ 的方程组 $x\boldsymbol{\alpha}_1+y\boldsymbol{\alpha}_2+z\boldsymbol{\alpha}_3=\boldsymbol{\alpha}_4$ 的几何图形是\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"过原点的一条直线。"},
            {"label": "B", "text": r"过原点的一个平面。"},
            {"label": "C", "text": r"不过原点的一条直线。"},
            {"label": "D", "text": r"不过原点的一个平面。"},
        ],
    },
    {
        "number": 8,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设随机变量 $X$ 的概率密度为 $f(x)=\dfrac{1}{2}e^{-|x|}$，$x\in(-\infty,+\infty)$，则\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$X$ 与 $|X|$ 不相关，$X$ 与 $|X|$ 不相互独立。"},
            {"label": "B", "text": r"$X$ 与 $|X|$ 不相关，$X$ 与 $|X|$ 相互独立。"},
            {"label": "C", "text": r"$X$ 与 $|X|$ 相关，$X$ 与 $|X|$ 不相互独立。"},
            {"label": "D", "text": r"$X$ 与 $|X|$ 相关，$X$ 与 $|X|$ 相互独立。"},
        ],
    },
    {
        "number": 9,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"将 $2$ 个球随机放入 $3$ 个盒子，每个盒子可放任意个球。设 $X_1$，$X_2$ 分别表示第一个和第二个盒子中放入的球的个数，$Y_1=X_1+X_2$，$Y_2=X_1-X_2$，则 $E(Y_1)$ 与 $E(Y_2)$ 分别为\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$\dfrac{2}{3}$，$0$。"},
            {"label": "B", "text": r"$\dfrac{4}{3}$，$0$。"},
            {"label": "C", "text": r"$\dfrac{2}{3}$，$\dfrac{1}{3}$。"},
            {"label": "D", "text": r"$\dfrac{4}{3}$，$\dfrac{1}{3}$。"},
        ],
    },
    {
        "number": 10,
        "section": "choice",
        "points": 5,
        "stem": {"text": r"设总体 $X$ 的概率密度为 $f(x)=\begin{cases}6x(1-x),&0<x<1,\\0,&\text{其他},\end{cases}$，$X_1,X_2,\cdots,X_n,\cdots$ 为来自总体 $X$ 的简单随机样本，且对任意的 $\varepsilon>0$，有 $\lim\limits_{n\to\infty}P\left\{\left|\sum\limits_{i=1}^{n}\dfrac{X_{2i}}{nX_{2i-1}}-a\right|<\varepsilon\right\}=1$，则 $a=$\ExamSelection。"},
        "choices": [
            {"label": "A", "text": r"$\dfrac{1}{2}$。"},
            {"label": "B", "text": r"$1$。"},
            {"label": "C", "text": r"$\dfrac{3}{2}$。"},
            {"label": "D", "text": r"$\dfrac{5}{2}$。"},
        ],
    },
    {
        "number": 11,
        "section": "fill",
        "points": 5,
        "stem": {"text": r"$\int_{-\pi}^{\pi}(x+\cos x)^3\,\mathrm{d}x=$\ExamBlank。"},
        "choices": [],
    },
    {
        "number": 12,
        "section": "fill",
        "points": 5,
        "stem": {"text": r"设 $u=ze^y\sin(x^2+y^2)$，其中 $z=z(x,y)$ 是由方程 $3x^2+2y^2+2z=7$ 确定的隐函数，则 $\left.\dfrac{\partial u}{\partial x}\right|_{(1,1)}=$\ExamBlank。"},
        "choices": [],
    },
    {
        "number": 13,
        "section": "fill",
        "points": 5,
        "stem": {"text": r"当 $|x|<1$ 时，$\ln\sqrt{\dfrac{1+x}{1-x}}$ 的幂级数展开式为\ExamBlank。"},
        "choices": [],
    },
    {
        "number": 14,
        "section": "fill",
        "points": 5,
        "stem": {"text": r"设 $\Sigma:x^2+y^2+z^2=4(z\geq 0)$，取上侧，则曲面积分 $I=\iint_{\Sigma}\dfrac{x\,\mathrm{d}y\mathrm{d}z+y\,\mathrm{d}z\mathrm{d}x+z\,\mathrm{d}x\mathrm{d}y}{\sqrt{x^2+(y-1)^2+z^2}}=$\ExamBlank。"},
        "choices": [],
    },
    {
        "number": 15,
        "section": "fill",
        "points": 5,
        "stem": {"text": r"若二次曲面 $x^2+(2+a)y^2+az^2+2xy-2xz-yz-5=0$ 为椭球面，则常数 $a$ 的取值范围为\ExamBlank。"},
        "choices": [],
    },
    {
        "number": 16,
        "section": "fill",
        "points": 5,
        "stem": {"text": r"设总体 $X$ 的概率密度为 $f(x;\sigma^2)=\begin{cases}\dfrac{a}{\sigma}e^{-\frac{x}{2\sigma^2}},&x\geq 0,\\0,&x<0,\end{cases}$，其中 $\sigma>0$ 为未知参数，$a$ 为常数。$X_1,X_2,\cdots,X_n$ 为来自总体 $X$ 的简单随机样本，则 $\sigma^2$ 的最大似然估计量为\ExamBlank。"},
        "choices": [],
    },
    {
        "number": 17,
        "section": "solution",
        "points": 10,
        "stem": {"text": r"求函数 $z=\cos^2x+\cos^2y$ 在条件 $x-y=\dfrac{\pi}{4}$ 下的极值。"},
        "choices": [],
    },
]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--json", type=Path, default=Path("build/retranscribe-zhangyu4-paper3.json"))
    args = parser.parse_args()

    from npee_math_papers.core.store import PaperRecord
    from npee_math_papers.service import NpeeService

    service = NpeeService.create()
    store = service.context.store

    record = store.read_paper(SERIES_KEY, YEAR, SUBJECT, PAPER_NO)
    current = copy.deepcopy(record.questions)
    tail = [question for question in current if int(question["number"]) >= 18]
    if len(tail) != 5:
        print(f"预期 q18--q22 共 5 题，实际读到 {len(tail)} 题；已中止。")
        return 1

    rebuilt = copy.deepcopy(TRANSCRIBED) + tail
    rebuilt.sort(key=lambda item: int(item["number"]))

    print(f"{SERIES_KEY}-{YEAR}-{SUBJECT} paper {PAPER_NO}")
    print(f"  q1--q17：按页面图重转（{len(TRANSCRIBED)} 题）")
    print(f"  q18--q22：沿用现库（{len(tail)} 题）")
    print(f"  合计：{len(rebuilt)} 题")
    print()
    for question in rebuilt:
        text = (question.get("stem") or {}).get("text") or ""
        print(f"  q{question['number']:<3} [{question['section']}] {text[:72]}")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.apply:
        print()
        print(f"预览模式；加 --apply 写回。清单：{args.json.as_posix()}")
        return 0

    store.write_paper(
        PaperRecord(
            series_key=SERIES_KEY,
            year=YEAR,
            subject=SUBJECT,
            paper_no=PAPER_NO,
            questions=rebuilt,
        ),
        replace=True,
    )
    store.rebuild_index()
    store.write_release()
    print()
    print("已写回 paper 3，并重建索引与发布清单。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
