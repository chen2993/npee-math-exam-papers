# 提取规范（把一个 bundle 的 PDF 变成题库）

面向执行提取的 Agent。这份文档定义**所有 bundle 共用的那一部分**：角色分工、
题目形状、排版约定、工具调用顺序、报错对照。

**每个 bundle 的具体事实**（自然键、来源哈希、capture 与页码范围、题目结构）
不写在这里，而是由工具生成到该 bundle 的 staging 目录：

```powershell
python -m npee_math_papers.maintenance.extraction_brief --series lilin6 --year 2027 --subject math2 --write
# -> .npee-math-papers/staging/lilin6-2027-math2/BRIEF.md
```

简报里的哈希、页码取自来源与 capture 记录，题目结构取自同系列已完成的对照套卷，
因此不会与题库现状不一致。**先读简报，再按本文档执行。**

## 一、边界（不可协商）

- 题面**只来自 capture 页面 PNG 的视觉观察**。禁止 OCR、PDF 文本层、公式识别器、
  复制粘贴、凭记忆作答。回答"我记得这道题是……"不是提取。
- 不读答案、解析、勘误、答题卡、封面、广告页。
- 一个子代理只处理分给它的那一套卷，不越界写别的套卷。
- 路径一律仓库相对 `/`，禁止盘符、绝对路径与 `..`。

## 二、三个角色

把一次提取拆成三个角色，是为了让**转写**与**核对**不落在同一个上下文里：
转写员的幻觉只有换一个独立读者拿源图逐题核对才能发现。

| 角色 | 输入 | 产出 | 边界 |
| --- | --- | --- | --- |
| **A 转写** | 页面 PNG | `staging/<bundle>/paper-<N>.json` | 不调用任何写入工具 |
| **B 入库** | A 的 JSON | 题库 | 不读整页图；只处理分到的套卷 |
| **V 核对** | 入库文本 + 源页面图 | `staging/<bundle>/verify-paper-<N>.md`，必要时 `paper-<N>-fixed.json` | 不写题库 |

V 是必须的，不是可选的：本批次曾确认第 3 套的 Q1–Q10、Q12–Q16 与源页面完全不符
（转写员凭记忆编造，甚至混入了数学一才有的曲面积分）。V 逐题给出
`OK` / `MINOR` / `MISMATCH`，并附页面原文摘要作为证据。

## 三、题目形状（schema 3.0）

一套卷在读写两侧形状一致（`core/paper.py` 是唯一定义）：

```json
{
  "number": 1,
  "section": "choice",
  "points": 5,
  "stem": { "text": "...", "figures": [] },
  "choices": [
    { "label": "A", "text": "...", "figures": [] },
    { "label": "B", "text": "...", "figures": [] },
    { "label": "C", "text": "...", "figures": [] },
    { "label": "D", "text": "...", "figures": [] }
  ],
  "subparts": []
}
```

- `stem` 与 `subparts` 的块是 `{text, figures}`；选项是 `{label, text, figures}`。
- `section` 只能是 `choice` / `fill` / `solution`。
- `choice` 必须有且仅有 A/B/C/D 四项，标签顺序固定；`fill` / `solution` 不能带 `choices`。
- 子问放 `subparts`，每项 `{text, figures}`。
- 图形归属明确：题干图放 `stem.figures`，选项图放该选项的 `figures`，
  子问图放该子问的 `figures`。
- 图形优先 `kind:"tikz"` 内嵌自包含 `tikzpicture`；确无法重绘才用 `kind:"asset"`，
  并填 `path` 与 `exception_reason`。

每套卷的题数、分题型计数与分值以该 bundle 的简报为准（题库里各系列一致，
但简报是权威）。

## 四、排版约定

| 约定 | 说明 |
| --- | --- |
| `\ExamSelection` | 选择题题干结尾加此宏；选项文本**不要**带 `A.` 前缀 |
| `\ExamBlank.` | 填空题题干结尾加此宏（带句点）；填空题不带 `choices` |
| `（本题满分 X 分）` | 解答题题干以此开头，紧接题目内容 |
| `$...$` | 行内公式一律用它；**禁止 `$$` 块级公式** |
| `\dfrac` | 分式一律用它；**禁止 `\frac`** |
| `\text{...}` | 数学模式内不写中文，中文必须包起来 |
| `\begin{pmatrix}` / `\begin{cases}` | 矩阵与分段函数用它们，行分隔用 `\\` |
| 待审标记 | 不得残留 `[待核]` 等标记 |

题库只使用 `\ExamSelection` 与 `\ExamBlank` 两个项目自定义宏——不要引入新的。

## 五、执行流程

### A 转写

1. 逐页读本套的页面 PNG（先整体浏览，必要时放大单题）。
2. 逐题转写成 schema 3.0。
3. 把 JSON 数组写到 `staging/<bundle>/paper-<N>.json`。
4. 回报：题数、分题型计数、拿不准的转写（附页码与题号）、是否用到 figure。

### B 入库

```text
1. npee_validate_questions(questions=[...])      直到 ok: true
2. npee_ingest_paper(series_key, year, subject, paper_no, questions,
                     series_name, capture_id, replace=false)
3. npee_diagnose_paper(series_key, year, subject, paper_no)        复核渲染
```

- 校验失败时把修正后的数组回写同一个 staging 文件，保持交接产物一致。
- `paper already exists` 表示该套已写入：用 `npee_get_paper` 核对即可，**不要**加 `replace`。
- 复核发现问题时，改 staging 后用 `replace=true` 回写，再复检。

### V 核对

对第 1..N 题，在页面图上找到该题号的印刷题干，与入库 `stem.text` 的关键公式逐字比较，
再比较选项或子问。输出逐题结论与证据，例如：

```text
Q7 OK       | 页面 "设 D={(x,y)|..."，入库同
Q8 MISMATCH | 页面是矩阵秩命题，入库是导数题
```

存在 MINOR 或 MISMATCH 时，把修正后的完整题目数组写到
`staging/<bundle>/paper-<N>-fixed.json`（MISMATCH 的题按页面图重写，OK 的题原样保留）。

## 六、报错对照

| 报错 | 处理 |
| --- | --- |
| `contains block math` | 改用行内 `$...$` |
| `uses \frac` | 改用 `\dfrac` |
| `choice requires exactly four options` | 补齐 A/B/C/D |
| `contains CJK text or punctuation in math mode` | 用 `\text{...}` 包裹中文 |
| `pending visual-review marker` | 删除 `[待核]` |
| `paper already exists` | 该套已写入，不要再写 |

## 七、常见坑

- **`npee_diagnose_paper` 渲染较重**，客户端可能超时（>120s）。超时后先用
  `npee_get_paper` 确认题目已落盘，再决定是否重试。
- **`leaked_command: "arctan"` / `"arcsin"` 是已知误报**：它们是合法算子名，
  渲染文本层本来就长这样。其它 problem（命令名泄漏、数学模式泄漏、`[待核]`）必须修。
- **分值不要凭印象填**。题库里确实存在 `points=null` 的题；写错分值不会报错，
  但会让总分对不上，只能靠 V 逐题核对发现。
- 写入后索引与发布清单会自动重建，不需要手动维护。

## 八、相关文档

| 文件 | 内容 |
| --- | --- |
| [`AGENT-QUICKSTART.md`](AGENT-QUICKSTART.md) | Agent 总入口：术语、任务地图、全部工作流 |
| [`MCP-SETUP.md`](MCP-SETUP.md) | MCP 安装与 34 个工具清单 |
| `staging/<bundle>/BRIEF.md` | **该 bundle 的具体事实**（由工具生成） |
