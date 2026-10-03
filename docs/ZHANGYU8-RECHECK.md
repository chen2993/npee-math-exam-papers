# 张宇八套卷重新提取复核

> 本文由 `build/zy8_errata.py` 一并生成于 `build/zy8_record.py`，数据源是
> `build/zy8-v2/verdicts/` 与 `build/zy8-v2/fixes.applied.json`，不手工维护。

## 一、这一轮做了什么

题库里 12 个 `zhangyu8-*` bundle（96 套卷）的原提取结果被**独立重读一遍**，
再逐条回源页裁定。重读与裁定都只使用运行环境的原生多模态能力读页面 PNG，
没有用 OCR、没有读 PDF 文本层、也没有让重读者看到题库原文。

| 环节 | 做法 |
| --- | --- |
| 页面证据 | `build/zy8_v2_pages.py` 按 bundle 重新渲染，整页嵌入图直取原生像素（2025 三科恢复到 4961x7016，旧 capture 只有 1241x1754）；横向拼版按中缝切分 |
| 独立重读 | 每套卷一个单元，96/96 完成，产出 `build/zy8-v2/results/*.json` |
| 比对 | `build/zy8_compare.py`：规范化后比对，抹平纯排版差异，保留数学内容差异 |
| 归一化自检 | `build/zy8_norm_probe.py` 16/16、`build/zy8_texnorm_selftest.py` 25/25 |
| 分类 | `build/zy8_triage.py`（内容/图形/结构）、`build/zy8_signatures.py`（差异签名聚类）|
| 裁定 | 每 bundle 一个裁定单元，逐条回图给出四选一结论 |
| 落盘 | `python -m npee_math_papers.maintenance.apply_errata_file` |

比对总计：MINOR 295，MISMATCH 82，MISSING 0，OK 3，STYLE 1732
（OK = 逐字一致；STYLE = 仅排版写法差异；MINOR = 长文本的小差异；
MISMATCH = 规范化后内容不同）。其中进入裁定的 147 处结论如下。

| 裁定 | 条数 | 含义 |
| --- | --- | --- |
| BANK_WRONG | 67 | 题库识别错误，已按源页更正 |
| AGENT_WRONG | 27 | 题库与源页一致，是重读读错了 |
| NOTATION_ONLY | 110 | 数学内容相同，只是写法不同 |
| SOURCE_UNCLEAR | 1 | 源页本身无法判读 |

## 二、逐条更正（已写入题库）

共 66 处，涉及 31 套卷。

| 自然键 | 题号 | 字段 | 原录入 | 更正为 | 源页 |
| --- | --- | --- | --- | --- | --- |
| `2023/math1/zhangyu8/4` | 10 | stem.text | （整段重录） | 设总体 $X$ 在 $(a,b)$ 上服从均匀分布，其中 $a,b$ 为未知参数，若对于 $X$ 的一组样本观测值 $x_1,x_2,\cdots,x_{10}$，$a,b$ … | zhangyu8-2023-math1/p029.png |
| `2023/math1/zhangyu8/4` | 13 | stem.text | （整段重录） | 曲线 $y=e^{-\frac{x}{2}}\sqrt{\sin x}$ 在 $[0,2\pi]$ 部分与 $x$ 轴围成的图形绕 $x$ 轴旋转一周所成的旋转体的体积为 $\… | zhangyu8-2023-math1/p029.png |
| `2023/math1/zhangyu8/6` | 21 | subparts.2.text | （整段重录） | 求 $A^*-6E$ 的秩。 | zhangyu8-2023-math1/p051.png |
| `2023/math1/zhangyu8/8` | 8 | choices.D.text | （整段重录） | $U^{\alpha+1}$ | zhangyu8-2023-math1/p061.png |
| `2023/math2/zhangyu8/3` | 6 | stem.text | （整段重录） | 设 $z=f(u,v),u=x-2y,v=x+ay$，函数 $f$ 具有二阶连续偏导数，且 $\dfrac{\partial^2z}{\partial u^2}=\dfrac{… | zhangyu8-2023-math2/p020.png |
| `2023/math3/zhangyu8/3` | 21 | subparts.2.text | （整段重录） | 求 $\left(\boldsymbol{A}-\dfrac{3}{2}\boldsymbol{E}\right)^{100}$。 | zhangyu8-2023-math3/p025.png |
| `2023/math3/zhangyu8/4` | 18 | subparts.1.text | （整段重录） | 证明:当 $0<x<1$ 时，$x-\dfrac{1}{x}<2\ln x$； | zhangyu8-2023-math3/p030.png |
| `2023/math3/zhangyu8/8` | 18 | subparts.1.text | （整段重录） | 将 $x=x(y)$ 的微分方程 $\dfrac{\mathrm{d}^2x}{\mathrm{d}y^2}+(y+\sin x)\left(\dfrac{\mathrm{d}… | zhangyu8-2023-math3/p063.png |
| `2024/math1/zhangyu8/5` | 1 | stem.text | （整段重录） | 函数 $f(x)=\dfrac{x\|x-1\|}{\sin\pi x}$ 的可去间断点的个数为\ExamSelection | zhangyu8-2024-math1/p034.png |
| `2024/math1/zhangyu8/7` | 2 | choices.C.text | （整段重录） | $f''_{yx}(0,0)=1$ | zhangyu8-2024-math1/p050.png |
| `2024/math1/zhangyu8/7` | 19 | subparts.1.text | （整段重录） | 存在 $\xi\in(0,1)$，使得 $f'(\xi)<2$； | zhangyu8-2024-math1/p053.png |
| `2024/math2/zhangyu8/1` | 6 | choices.A.text | （整段重录） | $y'''+2y''=0$ | zhangyu8-2024-math2/p001.png |
| `2024/math2/zhangyu8/5` | 4 | stem.text | （整段重录） | 设 $f(x)$ 是以 $2$ 为周期的连续函数，$\int_0^2f(x)\,\mathrm{d}x=1$，$g(x)$ 是过点 $(-\dfrac{1}{2},0)$ 和 … | zhangyu8-2024-math2/p029.png |
| `2024/math2/zhangyu8/5` | 21 | stem.text | （整段重录） | 设 $f(x)$ 在 $[-a,a]$（$a>0$）上二阶可导，且 $f(-a)=-1,f(a)=1,f'(-a)=f'(a)=0,\|f''(x)\|\leq1$。证明： | zhangyu8-2024-math2/p034.png |
| `2024/math2/zhangyu8/5` | 21 | subparts.2.text | （整段重录） | $a>\sqrt{2}$。 | zhangyu8-2024-math2/p034.png |
| `2025/math1/zhangyu8/5` | 8 | choices.B.text | （整段重录） | $P(\overline{A}\,\overline{B})>P(\overline{A})P(\overline{B})$。 | zhangyu8-2025-math1/p018.png |
| `2025/math1/zhangyu8/5` | 8 | stem.text | （整段重录） | 设随机事件 $A,B$ 满足 $0<P(A)<1,0<P(B)<1$，则 $P(AB)>P(A)P(B)$ 的充要条件是\ExamSelection | zhangyu8-2025-math1/p018.png |
| `2025/math1/zhangyu8/6` | 7 | choices.A.text | （整段重录） | $r(\boldsymbol{A}\ \ \boldsymbol{AB})=r(\boldsymbol{A})$。 | zhangyu8-2025-math1/p022.png |
| `2025/math1/zhangyu8/6` | 7 | choices.B.text | （整段重录） | $r\left(\boldsymbol{AB}^\mathrm{T}\ \ \boldsymbol{AB}^\mathrm{T}\boldsymbol{B}\right)=r(… | zhangyu8-2025-math1/p022.png |
| `2025/math1/zhangyu8/6` | 7 | choices.D.text | （整段重录） | $r\begin{pmatrix}\boldsymbol{A}^\mathrm{T}\boldsymbol{A}\\\boldsymbol{B}^\mathrm{T}\bold… | zhangyu8-2025-math1/p022.png |
| `2025/math1/zhangyu8/6` | 8 | choices.A.text | （整段重录） | $AC=\varnothing$。 | zhangyu8-2025-math1/p022.png |
| `2025/math2/zhangyu8/2` | 3 | stem.figures[0].latex | （整段重录） | \begin{tikzpicture}[scale=1.0] \draw[->] (-1.9,0) -- (2.0,0) node[below right] {$x$}; \d… | zhangyu8-2025-math2/p007.png |
| `2025/math2/zhangyu8/2` | 16 | stem.text | （整段重录） | 设 $\mathbf{A}=\begin{pmatrix}a&&\\&b&\\&&a\end{pmatrix}$，$\mathbf{P}=\begin{pmatrix}2&1&… | zhangyu8-2025-math2/p009.png |
| `2025/math2/zhangyu8/6` | 7 | stem.figures[0].latex | （整段重录） | \begin{tikzpicture}[scale=0.9,>=stealth] \draw[->] (-0.5,0) -- (4.4,0) node[below right]… | zhangyu8-2025-math2/p024.png |
| `2025/math3/zhangyu8/3` | 2 | stem.text | （整段重录） | 设常数$m>0,n>0$，则$\int_0^n\sqrt{x}\left[\dfrac{m}{x}\right]\,\mathrm{d}x$（$[\cdot]$是取整符号）的敛… | zhangyu8-2025-math3/p011.png |
| `2025/math3/zhangyu8/4` | 21 | stem.figures[0].latex | （整段重录） | \begin{tikzpicture}[>=stealth,thick,scale=0.9]\coordinate (T) at (0,1.4);\coordinate (L)… | zhangyu8-2025-math3/p018.png |
| `2025/math3/zhangyu8/6` | 7 | choices.A.text | （整段重录） | $r(A\quad AB)=r(A)$。 | zhangyu8-2025-math3/p024.png |
| `2025/math3/zhangyu8/6` | 7 | choices.B.text | （整段重录） | $r(AB^{\mathrm T}\quad AB^{\mathrm T}B)=r(AB^{\mathrm T})$。 | zhangyu8-2025-math3/p024.png |
| `2025/math3/zhangyu8/8` | 19 | stem.text | （整段重录） | 求 $\displaystyle \sum_{n=1}^{\infty}\dfrac{\left[2+(-1)^n\right]^n}{n\cdot 6^n}$ 的值。 | zhangyu8-2025-math3/p033.png |
| `2026/math1/zhangyu8/3` | 5 | choices.B.text | （整段重录） | $AP_2^{\mathrm T}P_1^9=B$。 | zhangyu8-2026-math1/p032.png |
| `2026/math1/zhangyu8/3` | 7 | stem.text | （整段重录） | 设 $A$ 为 $n$ 阶方阵，有下列结论：\n①若 $A$ 的全部顺序主子式为正，则 $A$ 正定；\n②若 $A$ 相似于对角矩阵 $\Lambda$，则 $A$ 与 $\… | zhangyu8-2026-math1/p033.png |
| `2026/math1/zhangyu8/4` | 4 | stem.text | （整段重录） | 若级数 $\sum_{n=1}^{\infty}\|u_nv_n\|$ 发散，则\ExamSelection | zhangyu8-2026-math1/p045.png |
| `2026/math1/zhangyu8/4` | 7 | stem.figures[0].latex | （整段重录） | \begin{tikzpicture}[scale=1.0,line width=0.5pt] \coordinate (P) at (2.15,4.35); \coordin… | zhangyu8-2026-math1/p047.png |
| `2026/math2/zhangyu8/1` | 7 | stem.text | （整段重录） | 设 $f(x)$ 在 $(0,+\infty)$ 内可导，以下结论：
①若 $\lim f(x)$ 存在，则 $\lim f'(x)$ 存在；
②若 $\lim f'(x)$ … | zhangyu8-2026-math2/p002.png |
| `2026/math2/zhangyu8/2` | 6 | choices.B.text | （整段重录） | $f'_x(x,y),f'_y(x,y)$不连续，$f(x,y)$不可微。 | zhangyu8-2026-math2/p010.png |
| `2026/math2/zhangyu8/2` | 6 | choices.C.text | （整段重录） | $f_x(0,0),f_x(0,0)$均存在。 | zhangyu8-2026-math2/p010.png |
| `2026/math2/zhangyu8/2` | 6 | choices.D.text | （整段重录） | $f^{xy}(0,0)$存在，$f_x(0,0)$不存在。 | zhangyu8-2026-math2/p010.png |
| `2026/math2/zhangyu8/2` | 20 | subparts.1.text | （整段重录） | $f(x,y)$的表达式； | zhangyu8-2026-math2/p014.png |
| `2026/math2/zhangyu8/2` | 20 | subparts.2.text | （整段重录） | $f(x,y)$的极值。 | zhangyu8-2026-math2/p014.png |
| `2026/math2/zhangyu8/3` | 10 | stem.text | （整段重录） | 设 $A$ 为 $n$ 阶方阵，有下列结论：
①若 $A$ 的全部顺序主子式为正，则 $A$ 正定；
②若 $A$ 相似于对角矩阵 $A$，则 $A$ 与 $A$ 合同；
③若… | zhangyu8-2026-math2/p019.png |
| `2026/math2/zhangyu8/4` | 4 | choices.C.text | （整段重录） | $-\dfrac{z}{z+1}(e^{-x}-e^{-y})$ | zhangyu8-2026-math2/p026.png |
| `2026/math2/zhangyu8/4` | 4 | choices.D.text | （整段重录） | $-\dfrac{z}{z+1}(e^{-x}+e^{-y})$ | zhangyu8-2026-math2/p026.png |
| `2026/math2/zhangyu8/4` | 16 | stem.text | （整段重录） | 设 $\boldsymbol{\alpha}_1=\begin{pmatrix}4\\1\\2\end{pmatrix},\ \boldsymbol{\alpha}_2=\be… | zhangyu8-2026-math2/p028.png |
| `2026/math2/zhangyu8/5` | 5 | choices.C.text | （整段重录） | $2\mathrm{e}^{3}3$ | zhangyu8-2026-math2/p034.png |
| `2026/math2/zhangyu8/6` | 10 | stem.text | （整段重录） | 设 $n$ 阶方阵 $A=(a_1,a_2,\cdots,a_n)$，$B=(\beta_1,\beta_2,\cdots,\beta_n)$，$AB=(y_1,y_2,\cd… | zhangyu8-2026-math2/p043.png |
| `2026/math2/zhangyu8/7` | 5 | choices.A.text | （整段重录） | $f:(x,y)$ 连续，$f(x,y)$ 可微。 | zhangyu8-2026-math2/p050.png |
| `2026/math2/zhangyu8/7` | 5 | choices.B.text | （整段重录） | $f'(x,y)$ 连续，$f(x,y)$ 不可微。 | zhangyu8-2026-math2/p050.png |
| `2026/math2/zhangyu8/7` | 5 | choices.C.text | （整段重录） | $f:(x,y)$ 不连续，$f(x,y)$ 可微。 | zhangyu8-2026-math2/p050.png |
| `2026/math2/zhangyu8/7` | 5 | choices.D.text | （整段重录） | $f:(x,y)$ 不连续，$f(x,y)$ 不可微。 | zhangyu8-2026-math2/p050.png |
| `2026/math2/zhangyu8/7` | 9 | choices.D.text | （整段重录） | $a_1,a_2,\cdots,a_r$ 中至少有一个向量能由其余向量线性表示。 | zhangyu8-2026-math2/p051.png |
| `2026/math2/zhangyu8/7` | 9 | stem.text | （整段重录） | $n$ 维向量组 $a_1,a_2,\cdots,a_r\ (3\leq r\leq n)$ 线性相关的充分必要条件是\ExamSelection。 | zhangyu8-2026-math2/p051.png |
| `2026/math2/zhangyu8/7` | 10 | stem.text | （整段重录） | 若 $A,A^{\circ},B$ 都是 $n\ (n>2)$ 阶非零矩阵，且 $A'$ 是 $A$ 的伴随矩阵，$AB=O$，则 $r(B)=$\ExamSelection。 | zhangyu8-2026-math2/p051.png |
| `2026/math2/zhangyu8/7` | 19 | stem.text | （整段重录） | 设 $f(x)$ 在 $\left[0,\dfrac{3}{2}\pi\right]$ 上连续，在 $\left(0,\dfrac{3}{2}\pi\right)$ 内是函数 … | zhangyu8-2026-math2/p053.png |
| `2026/math2/zhangyu8/7` | 19 | subparts.1.text | （整段重录） | 证明 $f\left(\dfrac{3}{2}\pi\right)>0$； | zhangyu8-2026-math2/p053.png |
| `2026/math2/zhangyu8/8` | 2 | stem.text | （整段重录） | 设 $f(x)$ 在 $(0,+\infty)$ 内可导，对于以下结论
①若 $\lim f(x)$ 存在，$\lim f'(x)$ 存在，则 $\lim_{x\to+\inf… | zhangyu8-2026-math2/p058.png |
| `2026/math2/zhangyu8/8` | 8 | choices.B.text | （整段重录） | $D_1,D_2,\cdots\cdots,D_n$ 为等差数列。 | zhangyu8-2026-math2/p059.png |
| `2026/math2/zhangyu8/8` | 8 | stem.text | （整段重录） | 设 $n$ 阶行列式 $\begin{vmatrix}2&1&0&\cdots&0\\1&2&1&\cdots&0\\0&1&2&\cdots&0\\\vdots&\vdots… | zhangyu8-2026-math2/p059.png |
| `2026/math2/zhangyu8/8` | 10 | stem.text | （整段重录） | 设 $a_1,a_2,\cdots\cdots,a_n$ 是 $n$ 个 $n$ 维的线性无关向量，$\boldsymbol{\alpha}_{n+1}=k_1\boldsym… | zhangyu8-2026-math2/p059.png |
| `2026/math3/zhangyu8/3` | 5 | choices.A.text | （整段重录） | $AP_1^9P_2^{\mathrm T}=B$ | zhangyu8-2026-math3/p009b.png |
| `2026/math3/zhangyu8/3` | 5 | choices.B.text | （整段重录） | $AP_2^{\mathrm T}P_1^9=B$ | zhangyu8-2026-math3/p009b.png |
| `2026/math3/zhangyu8/3` | 5 | choices.C.text | （整段重录） | $P_1^9P_2^{\mathrm T}A=B$ | zhangyu8-2026-math3/p009b.png |
| `2026/math3/zhangyu8/3` | 5 | choices.D.text | （整段重录） | $P_2^{\mathrm T}P_1^9A=B$ | zhangyu8-2026-math3/p009b.png |
| `2026/math3/zhangyu8/4` | 3 | choices.A.text | （整段重录） | $\displaystyle\int_0^1\ln\left[1+\dfrac{f(x)}{n}\right]\mathrm{d}x$。 | zhangyu8-2026-math3/p013b.png |
| `2026/math3/zhangyu8/4` | 5 | choices.C.text | （整段重录） | $\begin{pmatrix}1&0&0\\2&1&0\\3&\dfrac43&1\end{pmatrix}\begin{pmatrix}1&0&0\\0&3&0\\0&0&… | zhangyu8-2026-math3/p014a.png |
| `2026/math3/zhangyu8/4` | 5 | choices.D.text | （整段重录） | $\begin{pmatrix}1&0&0\\2&-1&0\\3&\dfrac43&1\end{pmatrix}\begin{pmatrix}1&0&0\\0&-3&0\\0&… | zhangyu8-2026-math3/p014a.png |
| `2026/math3/zhangyu8/4` | 15 | stem.text | （整段重录） | 设$\boldsymbol{\alpha}_1=\begin{pmatrix}4\\1\\2\end{pmatrix}$，$\boldsymbol{\alpha}_2=\beg… | zhangyu8-2026-math3/p014b.png |

## 三、判为「重读读错」的条目（题库保持不变）

**zhangyu8-2023-math1**

- p3 q17 `figure1`：卷(三)第4页(页脚锚点「考研数学命题人终极预测卷(三) 第4页(共8页)」已核对)该题正文右侧确实印有图形：x、y 坐标轴带箭头，原点 O，曲线 y=f(x) 自 (0,1) 起下降并在 ln 2 右侧与 x 轴相交于 A，直线 L 自 y 轴截距下降交 x 轴，x=ln 2 处有竖直虚线，曲线与 L 之间及曲线与 x 轴之间均有斜线阴影。题库 tikz 的要素（O、1、y=f(x)、L、A、\ln2、两处 pattern 阴影）与源页一致；重读该字段为空字符串，漏掉源…
- p8 q9 `figure1`：卷(八)第3页(页脚锚点「考研数学命题人终极预测卷(八) 第3页(共8页)」已核对)印题目所附 2×4 概率分布表: 上行为 X_i | −1 | 0 | 1，下行为 P | 1/4 | 1/2 | 1/4。题库 tikz 把 X_i 置于上行(y=1.5)、P 置于下行(y=0.5)，行序与源页一致，故题库对；重读的 tikz 把 P 放在上行(y=1.5)、X_i 放在下行(y=0.5)，行序与源页相反，故重读错。按复核口径，“同一个符号出现在不同位置”不属于写法差异…

**zhangyu8-2023-math2**

- p3 q18 `figures`：源页（脚注：考研数学命题人终极预测卷(三) 第4页(共8页)）第18题第(2)问右侧印有图：xOy 坐标系，曲线 y=f(x) 在 y 轴上过 1，虚线标出 x=ln 2，直线 L 过曲线在 x=ln 2 处的切点，标出与 x 轴交点 A，曲线与 L 之间的两块阴影区域。题库记 1 图正确，重读记 0 图漏图。
- p3 q18 `figure1`：源页同一图经放大核对：坐标轴、曲线 y=f(x)、切线 L（标注 L）、x=ln 2 处虚线、交点 A、y 轴截距 1 与两块阴影线均与题库 tikzpicture 的构成一致，题库有图而重读为空。
- p3 q21 `figures`：源页（脚注：考研数学命题人终极预测卷(三) 第7页(共8页)）第21题右侧印有图：两段上半圆弧（左段自 -a 到 O，右段自 O 到 2a），x 轴标出 -a、O、a、2a，阴影区域画斜线。题库记 1 图正确，重读记 0 图漏图。
- p3 q21 `figure1`：源页同一图放大后可见：左半圆 y=√(a²-x²) 与右半圆 x²+y²=2ax 的两段弧、纵轴 y、横轴 x、刻度标签 -a/O/a/2a 及阴影斜线，与题库 tikzpicture 示意一致；重读无图。

**zhangyu8-2023-math3**

- p5 q10 `choiceA`：源页选项 A 印「$y_\alpha y_{1-\alpha}=1.$」。四个选项的首下标在版面上是同一字形的同一字符：重读自己在选项 C、D 把该首下标认作 α（写成 $y_{\frac{\alpha}{2}}$），又在 A、B 的第二个下标（$1-\alpha$）里认作 α，却唯独把 A、B 的首下标写成 a——同一行同一字形不可能既是 α 又是 a；且题干同一行有「对给定的 $\alpha(0<\alpha<1)$，数 $y_\alpha$ 满足 $P\{|Y|>y…
- p5 q10 `choiceB`：源页选项 B 印「$y_\alpha y_{1-\alpha/2}=1.$」，首下标与 A、C、D 首下标为同一字形（即 α）；重读把首下标误作 a（写成 $y_a$），却在同一字段的第二个下标写成 \alpha，自相矛盾。题库正确。
- p5 q10 `stem`：源页题干印「设随机变量 $X$ 服从标准正态分布,$X_1,X_2,X_3,X_4$ 为来自总体 $X$ 的简单随机样本,设 $Y=\dfrac{X_1^2+X_2^2}{X_3^2+X_4^2}$,对给定的 $\alpha(0<\alpha<1)$,数 $y_\alpha$ 满足 $P\{|Y|>y_\alpha\}=\alpha$,则有」——同一个 α 在同句出现三处（$0<\alpha<1$、$=\alpha$、以及两处 $y$ 的下标），字形一致；题库的 $y_\…

**zhangyu8-2024-math1**

- p7 q18 `sub1`：源页 p052（卷(七) 第4页）第18(1) 放大后印「求 a_n 的表示式；」——第三字为「示」（宝盖头下「二+小」），非「达」；题库「表示式」与源页一致。

**zhangyu8-2024-math2**

- p1 q2 `figure1`：源页（套一 第2页）该图只有一组坐标轴（左 v(m/s)、右 t(s)、原点 O），三块阴影 15/20/10 依次画在同一坐标系上，由 t_1、t_2、t_3 处的竖直虚线分隔；题面文字写明「图中实线和虚线分别为甲和乙的速度曲线」，即同一图上实线一条、虚线一条。题库 tikzpicture 正是单坐标系三区。重读稿改用 3 个独立坐标系（3 个 scope，各画 x、y 轴与 O），与原图结构不符。
- p7 q5 `stem`：源页（套七 第2页）第 5 题文字为「……x 表示时间，则以下 3 条曲线」＋三幅图＋「对应关系正确的是」，题干以「对应关系正确的是」收束后再列选项 A–D；题库与源页一致，重读稿在「以下 3 条曲线」后直接接 \ExamSelection，漏掉「对应关系正确的是」。

**zhangyu8-2025-math1**

- p1 q8 `figures`：第一套第3页（页脚「第3页」、居中标题「25 张宇八套卷（数一）· 第一套」已核对）第 8 题题干下方确实印有图形：三幅并列的概率密度曲线，横轴右端标 $x$、刻度标 $-1,O,1$，纵轴旁分别标 $f_1(x)$、$f_2(x)$、$f_3(x)$，图下分别标 (a)(b)(c)。题库记 1 组图与源页相符，重读记 0 图为漏记。（裁片 ad2-zhangyu8-2025-math1-p1_q8_fig.png，约 1.07 倍原页宽）
- p1 q8 `figure1`：第一套第3页第 8 题图：图 (a) 顶点在 $x=0$、两腰在 $-1$ 与 $1$ 处落到横轴的折线三角形；图 (b) 为在 $-1$ 与 $1$ 处带空心端点、两端有竖直虚线的水平线段；图 (c) 为在 $-1$ 与 $1$ 处带空心端点的折线，两腰在原点落到横轴。题库 tikz 的三幅子图与源页逐一相符（含 $f_1/f_2/f_3$ 标签与 (a)(b)(c) 图注），重读该字段为空字符串，系漏记源页图形。（裁片 ad2-zhangyu8-2025-math1-…
- p3 q3 `figure1`：第三套第9页（页脚「第9页」、居中标题「25 张宇八套卷（数一）· 第三套」已核对）第 3 题图：带箭头的 $y$ 轴（上方标 $y$）与 $x$ 轴（右端标 $x$）、原点 $O$，一条自 $y$ 轴截距起上升并在右侧趋于水平的 S 形曲线，$x_1$、$x_2$ 两处自曲线向 $x$ 轴画竖直虚线，刻度标 $x_1$、$x_2$。题库 tikz 具备 $O$、$x_1$、$x_2$ 竖直虚线与对应曲线形状，与源页要素一致；重读 tikz 缺少 $y$ 轴箭头外的 $y…
- p4 q1 `choiceA`：第四套第12页（页脚「第12页」、居中标题「25 张宇八套卷（数一）· 第四套」已核对）第 1 题选项 A 印「（1）（4）．」——括号为圆括号、内为阿拉伯数字 1 与 4，与题干中四条结论的编号（1）（2）（3）（4）同形。题库 $\left(1\right)\left(4\right)$ 写法与源页相符；重读作「①④．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q1_AB.png，约 2 倍原页宽）
- p4 q1 `choiceB`：第四套第12页第 1 题选项 B 印「（2）（3）．」，编号为圆括号加阿拉伯数字。题库 $(2)(3)$ 与源页相符；重读作「②③．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q1_AB.png）
- p4 q1 `choiceC`：第四套第12页第 1 题选项 C 印「（1）（2）（4）．」，编号为圆括号加阿拉伯数字。题库 $(1)(2)(4)$ 与源页相符；重读作「①②④．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q1_CD.png）
- p4 q1 `choiceD`：第四套第12页第 1 题选项 D 印「（3）．」，编号为圆括号加阿拉伯数字。题库 $(3)$ 与源页相符；重读作「③．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q1_CD.png）
- p4 q3 `choiceA`：第四套第12页第 3 题选项 A 印「（1）（3）．」，编号为圆括号加阿拉伯数字。题库 $(1)(3)$ 与源页相符；重读作「①③．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q3_AB2.png，约 2 倍原页宽）
- p4 q3 `choiceB`：第四套第12页第 3 题选项 B 印「（1）．」，编号为圆括号加阿拉伯数字。题库 $(1)$ 与源页相符；重读作「①．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q3_AB2.png）
- p4 q3 `choiceC`：第四套第12页第 3 题选项 C 印「（2）（4）．」，编号为圆括号加阿拉伯数字。题库 $(2)(4)$ 与源页相符；重读作「②④．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q3_CD2.png）
- p4 q3 `choiceD`：第四套第12页第 3 题选项 D 印「（4）．」，编号为圆括号加阿拉伯数字。题库 $(4)$ 与源页相符；重读作「④．」（带圈序号）与源页字形不符。（裁片 ad2-zhangyu8-2025-math1-p4_q3_CD2.png）
- p4 q21 `figure1`：第四套第15页（页脚「第15页」已核对）第 21 题图：左上节点与右下节点之间的菱形交通网络，顶部有自上方指向左节点的箭头标 $a$、自左节点向左的箭头标 $40$、自左节点向右的箭头标 $100$，四条内部边分别标 $x_1$（右上节点→左节点）、$x_2$（右上节点→右节点）、$x_4$（左节点→下节点）、$x_5$（下节点→右节点，箭头指向右上），中间水平边 $x_3$ 箭头指向右，底部为自下节点向下的箭头标 $b$。题库 tikz 的节点拓扑、边标签 $x_1$–…

**zhangyu8-2025-math2**

- p8 q9 `choiceA`：源页 p032（卷(八)，页脚「第31页」已核对）第9题选项 A 印「充要条件.」——「条」之前为「充」「要」两个字（6 倍放大裁片 ad3-zhangyu8-2025-math2-p8_q9_A_hi.png：「要」上部为「覀」形、下部为「女」，与「分」的八字结构截然不同；同页选项 B「必要非充分条件」、C「充分非必要条件」均含「充分」二字，字形可与 A 的「要」对照）。题库作「充要条件」与源页一致；重读作「充分条件．」漏掉「要」字，把充要条件误作充分条件。

**zhangyu8-2026-math2**

- p3 q21 `stem`：页脚「考研数学命题人终极预测卷(三) 第 7 页(共 8 页)」。题干 y305-415 印「计算 ∫∫_D (2x+y)/x^{3/2} dxdy，其中 D 是由抛物线 y^2=2x 与直线 x+y=4，x+y=12 所围成的区域.」。关键是分母的几何：主分式横杠在 y344-347（x403-498）。横杠下方是先一枚「3」（x452-467 y352-369）、再一段短横（x449-465 y377-379）、再一枚「2」（x454-464 y387-396），而它…
- p7 q9 `choiceA`：源页该选项印「对于任意一组不全为零的数 k1, k2, ……, 都有 k1α1+k2α2+…+kᵣαᵣ=0.」；「不全为零」确为汉字「零」（雨字头，8倍放大清晰）。线性组合内的向量为希腊 α（单层椭圆带右下伸尾，与题库 \boldsymbol{\alpha} 对应），非拉丁 a；重读写作 \boldsymbol{a} 与源页不符，题库对

## 四、方法与边界

- 页面证据只来自 PNG 的原生多模态观察；裁片放大（3–20 倍）用于分辨上下标、
  转置/伴随、绝对值与上划线、`\cdot` 与 `\times`、虚实线与空心圈。
- 重读单元**不得打开** `.npee-math-papers/papers/`、`index/`、`release.json`；
  裁定单元看到的是复核包里的题库原文，不再回读原始文件。
- 比对工具的口径是「数学内容」而非「字符串」：它抹平 `\dfrac`/`\frac`、
  `\mathrm{e}`/`e`、`f'_x`/`f_x'`、圈码与括号序号等写法差异，
  但保留乘号种类、下标、指数、系数、不等号严宽、汉字选字等真正的差异。
  归一化器本身有自检（见上表），避免把噪声当成错误、也避免把错误当成噪声。
- 源页印错也照源页录：题库的契约是忠实转写源页，是否更正由人工决定。

## 五、验收证据

```powershell
python -m npee_math_papers.maintenance.audit_store          # 结构一致性
python -m npee_math_papers.maintenance.check_math_cjk       # 数学模式中的中文
python -m npee_math_papers.maintenance.verify_compile       # 逐套真编译 + 泄漏检测
python build\zy8_norm_probe.py                             # 比对口径自检
python build\zy8_texnorm_selftest.py                       # 规范化自检
python build\zy8_checkfixes.py                             # 勘误落盘前独立复核
python build\zy8_figcheck.py                               # 改动的图形过渲染器
```

勘误成品（分科目）见 `dist/zhangyu8-errata/`，源文件见 `composition/zhangyu8-errata/`。
