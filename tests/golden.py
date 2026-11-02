"""Golden snapshot of generated TeX, used to prove refactors are behavior-preserving.

``capture()`` renders a fixed set of questions through the builder's public
functions and returns a stable, comparable structure. ``tests/test_rendering_golden.py``
asserts the committed snapshot still matches, so moving code between modules cannot
silently change the emitted TeX.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from npee_math_papers.core.render_model import to_render_questions  # noqa: E402
from npee_math_papers.service.tex_builder import (  # noqa: E402
    render_body,
    validate_inline_tex,
)

#: Text fields exercising the historical-write repairs: alignment rows, cases,
#: hline, vdots, doubled braces, unit exponents, operator limits and a graphic
#: choice. The snapshot protects exactly the behaviour the repairs implement.
INLINE_SAMPLES: tuple[str, ...] = (
    r"设 $x=\dfrac{1}{2}$。",
    r"$\begin{cases}a+b\exp\left(-\dfrac{x^2}{2}\right),&x>0,\\0,&x\leq 0,\end{cases}$",
    r"$\begin{array}{c|ccc}X&0&1&2\\\hline P&p&1-p&0\end{array}$",
    r"$\begin{vmatrix}a&b\\\vdots&\vdots\\c&d\end{vmatrix}$",
    r"$\begin{pmatrix}\lambda&0\\0&\lambda\end{pmatrix}$",
    r"$f(x)=\dfrac{1}{1+x}$，$x\in(0,1)$。",
    r"$\lim\limits_{n\to\infty}\dfrac{1}{n}=0$",
    r"$\left.\dfrac{\mathrm{d}y}{\mathrm{d}x}\right|_{x=0}=1$",
    r"表面积 $m/s^2$ 与 $x^{2}$ 的关系。",
    r"$F(x)=\begin{cases}0,&x<0,\\\Phi(x),&x\geq0,\end{cases}$",
)


def _render_questions() -> list[dict]:
    """A fixed question set covering choice/fill/solution and a graphic choice."""

    return [
        {
            "number": 1,
            "section": "choice",
            "points": 5,
            "stem": {"text": r"设 $f(x)=x^2$，则 $f'(1)=$\ExamSelection。", "figures": []},
            "choices": [
                {"label": "A", "text": "$0$", "figures": []},
                {"label": "B", "text": "$1$", "figures": []},
                {"label": "C", "text": "$2$", "figures": []},
                {"label": "D", "text": "$3$", "figures": []},
            ],
        },
        {
            "number": 11,
            "section": "fill",
            "points": 5,
            "stem": {"text": r"$\displaystyle\int_0^1\dfrac{x}{1+x^2}\,\mathrm{d}x=$ \ExamBlank。", "figures": []},
        },
        {
            "number": 19,
            "section": "solution",
            "points": 12,
            "stem": {"text": r"（本题满分 12 分）证明 $\lim\limits_{n\to\infty}x_n$ 存在。", "figures": []},
            "subparts": [
                {"text": r"（I）证明 $\{x_n\}$ 单调有界；", "figures": []},
                {"text": r"（II）求该极限。", "figures": []},
            ],
        },
        {
            # A stored score label must not print twice: the class re-prints the
            # score from ``points``, so the renderer strips this prefix.
            "number": 20,
            "section": "solution",
            "points": 10,
            "stem": {"text": r"（本题满分10分）", "figures": []},
            "subparts": [
                # A stored subpart ordinal is stripped (the class numbers it); an
                # in-text cross reference to another part is preserved.
                {"text": r"（I）求 $\lim\limits_{x\to0}\dfrac{f(x)}{x}$。", "figures": []},
                {"text": r"（II）在第（I）问的基础上，证明 $f$ 连续。", "figures": []},
            ],
        },
        {
            # A proposition sequence whose markers head inline math runs must
            # become a hanging list, with the formulas re-opened after each head.
            "number": 3,
            "section": "choice",
            "points": 5,
            "stem": {
                "text": r"设 $\mathrm{e}<x_1<x_2$，且 $①x_2\ln x_2>x_1\ln x_1$，$②x_1\ln x_2<x_2\ln x_1$，$③x_2\ln x_2<x_1\ln x_1$，$④x_1\ln x_2>x_2\ln x_1$。则下列不等式成立的是\ExamSelection",
                "figures": [],
            },
            "choices": [
                {"label": "A", "text": r"$②③$", "figures": []},
                {"label": "B", "text": r"$①②$", "figures": []},
                {"label": "C", "text": r"$①④$", "figures": []},
                {"label": "D", "text": r"$③④$", "figures": []},
            ],
        },
        {
            # A marker inside an alignment cell stays inline: it belongs to the
            # grid, not to the paragraph.
            "number": 4,
            "section": "fill",
            "points": 5,
            "stem": {
                "text": r"设有极限式 $\begin{array}{ll}①\displaystyle\lim_{n\to\infty}\cos n\cdot(\sqrt[n]{n}-1)=0;&②\displaystyle\lim_{n\to\infty}\sqrt n\cdot(\sqrt[n]{n}-1)=0;\\③\displaystyle\lim_{n\to\infty}\sqrt n\ln n\cdot(\sqrt[n]{n}-1)=0;&④\displaystyle\lim_{n\to\infty}n\cdot(\sqrt[n]{n}-1)=0,\end{array}$ 则正确的个数为\ExamBlank。",
                "figures": [],
            },
        },
    ]


def capture() -> dict:
    """Return the canonical snapshot used by the golden test."""

    return {
        "inline": [validate_inline_tex(text, "golden") for text in INLINE_SAMPLES],
        "body": render_body(to_render_questions(_render_questions()), occurrence=1),
    }
