# Agent 快速上手

你是一个可以调用 MCP 工具的 Agent。本文档帮你用最短路径完成题库工作。

## 一、MCP 服务名

```
npee-math-papers
```

它同时是项目名、Python 包名来源与数据根目录名。配置见
[`MCP-SETUP.md`](MCP-SETUP.md)。

## 二、术语

| 术语 | 含义 | 示例 |
| --- | --- | --- |
| series | 出版社系列 | `zhangyu8` |
| paper | 一套试卷 | `paper_no=7` |
| bundle | 系列 + 年份 + 科目 | `zhangyu8-2024-math1` |
| capture | 一次页面切分批次 | `unit-007` |

**自然键**：`year/subject/series_key/paper_no`，例如 `2024/math1/zhangyu8/7`。
所有工具都用这四个字段定位一套卷。

`subject` 只有三个取值：`math1`、`math2`、`math3`。

## 三、三十秒任务地图

| 你想做的事 | 调用 |
| --- | --- |
| 看题库规模 | `npee_library_stats` |
| 有哪些系列 | `npee_list_series` |
| 找某系列的套卷 | `npee_list_papers(series_key="zhangyu8")` |
| 读一套卷的题目 | `npee_get_paper(series_key, year, subject, paper_no)` |
| 读单题 | `npee_get_question(..., question_no=7)` |
| 检索题目 | `npee_search_questions(query="平面")` |
| 看某个图形 | `npee_render_figure(...)` |
| 写入一套卷 | `npee_ingest_paper(...)` |
| 组卷并编译 | `npee_build_composition` → `npee_composition_submit` → `npee_composition_job` |
| 静态检查一段 TeX | `npee_check_tex(text)` |
| 扫描对齐环境反斜杠（单段 / 全库） | `npee_scan_alignments(text)` / `npee_audit_tex()` |
| 渲染一段 TeX 看效果 | `npee_render_tex(text)` |
| 诊断字段 / 整套卷渲染 | `npee_diagnose_field(text)` / `npee_diagnose_paper(...)` |
| 查看别人刚做了什么 | 前端「操作日志」页 |

## 四、典型工作流

### 工作流 A：写题（把 PDF 变成题库）

```text
1. npee_capture_available()              确认渲染环境可用
2. npee_capture_pdf(...)                 渲染 PDF 页面为 capture
3. （读取页面图，逐题转写为 schema 3.0 题目数组）
4. npee_validate_questions([...])        落盘前自检
5. npee_ingest_paper(..., replace=False) 写入题库
```

第 2 步会把 PDF 按你给的页码范围渲染成 PNG，答案页与排除页永不渲染。
第 3 步是唯一需要你视觉判断的环节：观察 PNG，转写题目。

若 PDF 已经渲染过，跳过第 2 步，直接从第 3 步开始。

### 工作流 B：组卷出 PDF

```text
1. npee_list_papers(series_key=..., year=...)   选套卷
2. npee_build_composition(selections=[...])     生成组卷（自动封印版本）
3. npee_composition_compile(composition, dry_run=True)   先试编译
4. npee_composition_compile(composition, dry_run=False)  真编译
```

`npee_build_composition` 的 `selections` 每项为：

```json
{"series_key": "zhangyu8", "year": 2024, "subject": "math1", "paper_no": 7}
```

编译前工具会重新核对每套卷的 `content_hash`。若题库在该卷被选后发生过变化，
编译会直接失败并告诉你哪些卷变了，不会渲染出不一致的内容。

**长编译用异步提交**：真编译要跑多趟 XeLaTeX，可能几十秒到数分钟。用同步工具
容易超时，改用后台任务：

```text
1. npee_composition_submit(composition, dry_run=False)   立即返回 job_id
2. npee_composition_job(job_id)                          轮询状态
3. npee_composition_jobs()                               查看最近任务
```

任务状态：`queued` → `running` → `succeeded` / `failed`。
成功时 `artifacts` 给出 PDF 路径；失败时 `error` 给出原因。
绑定校验在提交时同步完成，过期组卷立刻返回失败，不占用后台任务。

### 工作流 C：从别的形态批量导入

题库只有一种写入路径：`npee_ingest_paper` / `npee_ingest_document`（schema 3.0 或旧 2.0，
写入时自动转换）。若你手上是 CSV、旧 JSON 或其他形态，先在自己的脚本里转成题目数组，
再逐套调用写入工具：

```text
1. npee_validate_questions([...])          先自检
2. npee_ingest_paper(series_key, year, subject, paper_no, questions, replace=...)
```

写入后 `index/` 与 `release.json` 自动重建，不需要额外的迁移脚本。

### 工作流 D：TeX 调试（反斜杠 / 渲染核对）

"能编译"不等于"渲染正确"：矩阵里少一个反斜杠会让 `\lambda` 变成字面字母 `lambda`。
用以下工具快速定位：

```powershell
# 1) 静态检查一段文本（丢反斜杠、块级数学、\frac、未闭合数学模式…）
npee_check_tex("$\\begin{array}{c|ccc}X&2\\\\hline P\\end{array}$")

# 2) 只扫描对齐环境内的反斜杠串异常（空行 / 缺行分隔 / 丢反斜杠）
npee_scan_alignments("$\\begin{pmatrix}a\\\\\\\\b\\end{pmatrix}$")

# 3) 全库静态扫描（秒级），返回受影响套卷与逐字段问题
npee_audit_tex()

# 4) 用真实排版类渲染，拿 PDF/PNG 与文本层肉眼核对
npee_render_tex("$\\begin{pmatrix}\\lambda&0\\\\0&1\\end{pmatrix}$")

# 5) 逐字段诊断一套卷：检测命令名泄漏成字面字母、数学模式泄漏、待核标记
npee_diagnose_paper(series_key="zhangyu8", year=2023, subject="math3", paper_no=4)
```

对齐环境的约定：`\\`（2 个）是行分隔；命令名前反斜杠串为**偶数**即为损坏，
行级命令（`hline` 等）应为 3，行内命令（`lambda` 等）应为 1。
一次性修复工具：`python -m npee_math_papers.maintenance.fix_tex`（先预览，
确认后加 `--apply`）。

## 五、套卷文档结构（schema 3.0）

一套卷在**读写两侧形状完全一致**（`core/paper.py` 是唯一定义）：

```json
{
  "schema_version": "3.0",
  "paper": {"series_key": "zhangyu8", "year": 2024, "subject": "math1", "paper_no": 3},
  "questions": [ ... ]
}
```

`npee_get_paper` 的返回是这个文档**加上一个只读的 `meta` 块**（自然键、题数、分题型
计数、图形数、内容哈希）。因此：

```
读：get_paper(...)              → { schema_version, paper, questions, meta }
写：ingest_document(去掉 meta)   → 直接回写，无需转换
```

写入时 `meta` 里的任何字段都会被拒绝（它们是派生的），未知字段也会被拒绝。改完题目
回写不需要手动维护 `content_hash`——它由服务端重算。

### 题目结构

题干、每个选项、每个子问都是统一的「文本块 + 图形数组」：

```json
{
  "number": 7,
  "section": "choice",
  "points": 5,
  "stem": { "text": "设 $f(x)=x^2$，则", "figures": [] },
  "choices": [
    { "label": "A", "text": "$0$", "figures": [] },
    { "label": "B", "text": "", "figures": [{ "kind": "tikz", "latex": "\\begin{tikzpicture}...", "description": "图形选项", "path": null, "exception_reason": null }] }
  ],
  "subparts": []
}
```

要点：

- `section` 只能是 `choice`、`fill`、`solution`；
- `choice` 必须有 A/B/C/D 四个选项，标签顺序固定；`fill`/`solution` 不带 `choices`；
- 图形归属明确：题干图放 `stem.figures`，选项图放该选项的 `figures`，子问图放该子问的 `figures`；
- 图形优先用 `kind: "tikz"` 内嵌 LaTeX；确实无法重绘才用 `kind: "asset"` 并给出 `path` 与 `exception_reason`；
- 行内公式用 `$...$`，分式用 `\dfrac`，禁止 `$$` 块级公式与 `\frac`。

## 六、校验失败怎么办

工具返回的 `ok: false` 或抛错会给出具体字段与原因。常见几类：

| 报错 | 原因 | 处理 |
| --- | --- | --- |
| `contains block math` | 用了 `$$...$$` | 改为行内 `$...$` |
| `uses \frac` | 用了 `\frac` | 改为 `\dfrac` |
| `pending visual-review marker` | 残留 `[待核]` | 补全或确认后删除 |
| `paper already exists` | 自然键重复 | 确认后传 `replace=true` |
| `content_hash ... changed` | 题库在组卷后变过 | 重新 `build_composition` 再编译 |
| `CJK ... in math mode` | 中文直接写在数学模式 | 包进 `\text{...}` |

## 七、写入约定

- 所有写入工具在落盘前完成结构校验，失败不会改动任何文件；
- 覆盖既有套卷必须显式 `replace=true`；
- 写入后索引与发布清单会自动重建，你不需要手动维护。

## 八、查看你刚刚做了什么

前端「操作日志」页把 MCP 工具调用与 HTTP 请求合成一条时间线，包含工具名、入参摘要、
成功/失败、耗时。写入类操作若失败，会在这里看到错误摘要。

## 九、维护命令

```powershell
python -m npee_math_papers.maintenance.audit_store            # 题库一致性审计
python -m npee_math_papers.maintenance.audit_store --rebuild  # 重建索引与发布清单
python -m npee_math_papers.maintenance.check_math_cjk         # 扫描数学模式中的中文
python -m npee_math_papers.maintenance.check_environment      # 环境检查
python -m npee_math_papers.maintenance.verify_compile         # 逐套单独编译 + 渲染泄漏检测
python -m npee_math_papers.maintenance.verify_compile --limit 20 --json build/compile-verify.json
python -m npee_math_papers.maintenance.verify_compile --matrix  # a4/a3 × 紧凑/宽松/打印版 + cream 主题 + 含答案
python -m npee_math_papers.maintenance.verify_compile --matrix --collections  # 再加 collections/ 正式组卷包
```

`verify_compile` 是"每套卷都能正常编译且渲染正确"的端到端证据：它把每套卷单独
组卷真编译，再从 PDF 文本层检测命令名泄漏（如 `\lambda` 被删反斜杠后渲染成字面
`lambda`）。合法运算符（`\arcsin` 等）本身就会渲染成同样的 ASCII 词，因此该工具
用数学斜体 Unicode 区分，避免把运算符误报为泄漏。

`--matrix` 让每套卷在全部版式（a4/a3 × 紧凑/宽松/打印版，另加 cream 主题与
`answers=true` 含答案模式，共 7 个变体）下各编一份；
`--collections` 还会编译 `collections/<id>/composition.json`（含封面、前言与 Hook
等包内 `\input` 资源）。

## 十、边界

- 不读答案、解析、勘误、答题卡、封面、广告页；
- 题面只来自页面 PNG 的视觉观察，不使用 OCR、文本层或公式识别器；
- 路径一律使用仓库相对 `/`，禁止绝对路径与 `..`。
