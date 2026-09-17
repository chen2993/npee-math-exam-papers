# NPEE 维护 TODO —— TeX 编译修复 + 架构升级（已完成）

> 上一轮的交接文档见 `build/backup-before-fix/TODO.md.handoff-bak`（未提交）。
> 本文件记录**已完成的修复**与**验收证据**，并列出仍可选的后续项。
> 仓库根：`C:\Users\a3149\Desktop\jjb`（Windows + PowerShell 5.1）。

---

## 1. 问题回顾

对齐环境（矩阵/分段/数组）里 `\\` 是行分隔符。历史数据与构建器各有一类缺陷：

1. **数据层**：紧跟命令名的反斜杠串个数为**偶数**（`≥2`）时语义错误——
   - `\\lambda`（2 个）→ 渲染成"换行 + 字面文本 `lambda`"，**编译通过但显示错误**；
   - `\\hline`（2 个）→ 缺行分隔，XeLaTeX 报 `Misplaced \noalign`，**编译失败**；
   - `\\\\`（4 个及以上偶数，后不接命令）→ 矩阵/表格里**多出空行**。
2. **代码层**：`service/tex_builder.py` 的 `repair_alignment_rows()` 因命令保留名单
   不全，会把正确的 `\\\hline` / `\\\vdots` 删成一个反斜杠（改坏）。

判定标准（纯静态可算）：命令名前**偶数个（`≥2`）反斜杠 = 损坏**；奇数个正常。

---

## 2. 已完成的修复

### 2.1 构建器（代码层）

- `npee_math_papers/service/tex_builder.py`
  - 新增 `ALIGNMENT_ROW_COMMANDS`（`INLINE_TEX_COMMANDS` 的扩展超集），
    `repair_alignment_rows()` 改用它判断"命令名前 3 个反斜杠"是否应保留。
  - `repair_cases_rows()` 的同一类判断也换用 `ALIGNMENT_ROW_COMMANDS`，与前者一致。
  - **补修**：`repair_alignment_rows()` 的第一条规则把捕获从 `[A-Za-z0-9]+` 收窄为
    `[A-Za-z]+`。原贪心捕获会把"行分隔 + `\dfrac38`"读成 `\\` + 字面 `dfrac38`，
    再删掉一个反斜杠，于是 `\\\dfrac38`（正确）被改成 `\\dfrac38`（渲染成字面
    `dfrac38`）。`\sqrt2`、`\dfrac12x` 等同理。全库无 `\\\<数字>` 用例，改动安全。
- 实测：`build/confirm-bug.py` 显示 `\\\hline` / `\\\vdots` / `\\\lambda` 均被**保留**；
  `build/idempotent.py` 对规范写法 `idempotent=True`。

### 2.2 一次性修复工具（数据层）

`npee_math_papers/maintenance/fix_tex.py` **重写**为命令感知且幂等：

| 命令类别 | 判定 | 目标反斜杠数 |
| --- | --- | --- |
| 行级命令 `hline`/`cline`/`hdashline` | 必须紧跟行分隔 | `3` |
| 行内命令（`lambda`/`vdots` 等）位于单元格/行首（前为 `&` 或 `{`） | 单命令 | `1` |
| 行内命令跟在行分隔之后 | 行分隔 + 命令 | `3` |
| 非命令的纯行分隔串 | 偶数且 `≥4`（空行） | `2` |

- 只在 `cases|matrix|pmatrix|bmatrix|Bmatrix|vmatrix|Vmatrix|smallmatrix|array`
  环境体内改写；`--apply` 前先输出 diff 预览，改动写入 `build/tex-repairs.json`，
  经 `store.write_paper(replace=True)` + `rebuild_index()` + `write_release()` 落盘。
- 对无法用统一规则安全推断的 `chaoyue10-2025-math1/4 q15`（6 阶行列式，2/4/6 个
  反斜杠混杂）使用 `CANONICAL_OVERRIDES` 只重建 vmatrix 环境体，前后文字原样保留。
- **幂等**：对修复后的题库再跑 `fix_tex` 输出"需要修复：0 处"。

### 2.3 复核：确定性判定问题的静态扫描（新增能力）

- `core/tex_audit.py` 新增：
  - `iter_fields()`（字段寻址规则上移到核心层，`maintenance/audit_tex.py` 重新导出）；
  - `check_alignment_runs()` / `scan_alignments()`：只扫描对齐环境内的反斜杠串
    异常（丢反斜杠、缺行分隔、多余空行）。
  - `check_text()` 对行级命令给出"补一个"的提示，方向与行内命令区分。
- `service/tex_quality.py`（新增，`NpeeService.tex`）：`check_text` /
  `scan_alignments` / `audit_library` / `render_text` / `diagnose_field` /
  `diagnose_paper`。
- `mcp/server.py` 新增 6 个调试工具（薄适配 `NpeeService.tex`）：
  `npee_check_tex`、`npee_scan_alignments`、`npee_audit_tex`、`npee_render_tex`、
  `npee_diagnose_field`、`npee_diagnose_paper`。MCP 工具总数 28 → 34。
- `maintenance/verify_compile.py`（新增）：**逐套单独编译 + 渲染泄漏检测**。
  对每套卷构造仅含它自己的组卷并真编译，再从 PDF 文本层检测"命令名泄漏"。
  泄漏判定用数学斜体 Unicode（合法运算符 `\arcsin` 渲染为直立 ASCII，而被删反斜杠的
  `\lambda` 会渲染成数学斜体 `𝑎𝑟𝑐𝑠𝑖𝑛`），因此不会把运算符名误报为泄漏。
- `service/composition.py` + `service/tex_builder.py`：**修复组卷包经用例层编译**。
  `CompositionService.compile()` 会把 `composition.json` 复制到构建目录，导致
  `document.cover.path` 这类与组卷包同级的相对资源无法解析——正式组卷包
  `collections/jiaji-eighty-five/`（270 套 × 3 科目 × 4 版式）此前**经服务端必然失败**。
  现在 `compile()` 接受 `package_dir`，并新增 `compile_collection(path)`：把组卷包内的
  `.tex` 与 `assets/` 一并铺到生成的 `composition.json` 旁，`BuildOptions.package_dir`
  让构建器仍以原始包目录为包根。实测 12 份 PDF（含封面）全部生成。
- `service/tex_builder.py`：**`answers` 目标选项此前被校验但从未生效**。
  目标矩阵允许 `"answers"` 字段，`target_matrix()` 也接受它，但 `make_main()` 从未
  把它写进 `\documentclass`，于是"含答案版"与"学生版"产出一致。现按需追加
  ``answers`` 类选项（`\DeclareOption{answers}`），`answers=true` 时解答/答案槽内联显示。

---

## 3. 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 题库结构 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（60 bundle / 321 套 / 7062 题 / 70 图） |
| 可疑字段 | `python build\suspects.py` | `suspects = 0`，`papers affected = 0` |
| 构建器校验 | `python build\full-build-scan.py` | `papers=321 build_ok=321 build_fail=0` |
| 静态对齐扫描 | `NpeeService.tex.audit_library()` | `finding_count = 0` |
| 最小复现编译 | `python build\compile-smoke.py` | `ok: True`（此前 `Misplaced \noalign` 失败） |
| 全库真编译 | 按 30 套一组组卷编译 321 套 | 11 批全部 `OK`，`failing batches: 0` |
| **逐套单独编译 + 泄漏检测** | `python -m npee_math_papers.maintenance.verify_compile` | **321/321 编译通过，0 泄漏，fully ok=321** |
| **全版式 + 组卷包** | `python -m npee_math_papers.maintenance.verify_compile --matrix --collections` | **321 套 × 5 版式 = 1605 份全部通过；2 个组卷包通过；0 泄漏** |
| **全版式含主题/答案模式** | 同上（矩阵扩展到 7 个变体） | **321 套 × 7 变体 = 2247 份全部通过；0 泄漏** |
| 字段渲染 | 11 套受影响卷逐字段渲染 | 无命令名泄漏、无编译错误 |
| 数据一致性 | `fix_tex` 再跑一次 | 输出"需要修复：0 处"（幂等） |
| 中文数学检查 | `python -m npee_math_papers.maintenance.check_math_cjk` | `No CJK characters found directly in math mode.` |
| 架构边界 | `.\npee_math_papers\maintenance\test-architecture.ps1` | `Passed architecture audit` |
| 空白检查 | `git diff --check` | 无错误（仅 LF→CRLF 提示） |

本轮修复分两类落地：

1. **数据层**（`fix_tex.py`）修复 11 套对齐字段（清单见下）；
2. **构建器**（`tex_builder.py` 规则收窄）额外修复 4 套（`chaoyue10-2025-math2/7`、
   `yubingsen5-2024-math3/1`、`yubingsen5-2024-math3/3`、`zhangyu4-2025-math2/3`）中
   `\\\dfrac38` / `\\\sqrt2` 类的渲染泄漏。

数据层修复的 11 套：

```
chaoyue10-2025-math1/4   chaoyue10-2025-math2/7   yubingsen5-2024-math2/3
yubingsen5-2024-math2/4  zhangyu4-2024-math1/4    zhangyu4-2026-math1/1
liyanfang3-2022-math3/3  liyanfang3-2023-math1/2  zhangyu8-2023-math3/4
zhangyu8-2023-math3/8    zhangyu8-2025-math3/3
```

---

## 4. 关键文件与备份

| 路径 | 说明 |
| --- | --- |
| `npee_math_papers/maintenance/fix_tex.py` | 命令感知 + 幂等的一次性修复工具 |
| `npee_math_papers/service/tex_builder.py` | `ALIGNMENT_ROW_COMMANDS` 与两处判定 |
| `npee_math_papers/core/tex_audit.py` | 静态检查器 + 对齐扫描 + `iter_fields` |
| `npee_math_papers/service/tex_quality.py` | TeX 质量用例（新增） |
| `npee_math_papers/service/tex_debug.py` | 渲染调试器（复用核心 `iter_fields`） |
| `npee_math_papers/mcp/server.py` | 6 个新调试工具 |
| `build/backup-before-fix/*.yaml` | 修复前的 6 套原始副本（回退用） |
| `build/tex-repairs.json` | `fix_tex` 最近的改动清单 |

---

## 5. 可选后续（未阻塞交付）

- **构建器"修复层"前移**：`audit_tex` 仍报告少量 `render_repair` / `textcircled_in_math`
  等类别（仓库历史遗留），可按同样思路逐类前移到入库阶段，减少构建期改写。
- **空行归一的可视化复核**：`build/blankrow-check/` 已生成相关渲染图，可人工抽检
  `\\\\`（4 个）收敛为 `\\`（2 个）后的表格/矩阵行数。
- **`core/store.py` 进一步拆分**（576 行）：可把索引/发布清单部分独立成
  `core/index.py`，与本次 `tex_builder` 拆分同一思路。
- **CI 接入**：`pyproject.toml` 已就绪，可把 `pytest` + `verify_compile` 接进流水线。

---

## 4b. 架构升级（本轮已完成，详见 `docs/UPGRADE-PLAN.md`）

| 项 | 结果 |
| --- | --- |
| 测试与打包 | 新增 `tests/`（**125 项通过**）与 `pyproject.toml` |
| 依赖注入 | `BuildOptions.store`；构建器不再从全局环境解析题库 |
| 术语单源 | 新增 `core/domain.py`；7+ 模块的重复常量收敛为一处 |
| TeX 常量单源 | `core/tex.py` 拥有正则/命令集合，构建器复用 |
| God 模块拆分 | `service/tex_builder.py` **1570 → 370 行**；新增 `service/rendering/` 8 个模块 |
| 错误分类 | `NotFoundError`/`ConflictError` + `http_status_for`；HTTP 映射 404/409/400 |
| 行为不变 | 黄金快照 `tests/golden/rendering.json` 逐字节一致；321/321 编译通过 |

---

## 6. 环境要点（未变）

- 控制台 GBK：Python 脚本输出中文需 `sys.stdout.reconfigure(encoding="utf-8")`。
- PowerShell 5.1 不支持 heredoc / `&&`：多行脚本写临时 `.py` 到 `build/` 再执行。
- LaTeX 工具链：`xelatex` / `pdftoppm` / `pdftotext` / `pdfinfo` 均在
  `D:\texlive\2026\bin\windows`；渲染类在 `npee_math_papers/tex/`。
- `build/` 与 `.npee-math-papers/{sources,captures,logs,staging}` 不提交。

---

## 7. 前端可用性升级（本轮完成，详见 `docs/FRONTEND-RESEARCH.md` §6）

上一轮前端升级解决「能不能用」（路由、服务端状态、主题、测试）；本轮解决
「好不好用」：操作次数、等待反馈、误操作挽救。

### 7.1 异步编译（最大体验缺口）

此前「编译导出」是同步阻塞请求，全版式编译几十秒到几分钟内页面只能转圈，用户既不
知道进度也不敢离开，且无法取回产物。

| 项 | 结果 |
| --- | --- |
| 前端状态机 | `application/composition/useCompileFlow.ts`（`idle → submitting → running → succeeded/failed`，1.5s 轮询 + 已用时间） |
| 进度面板 | `features/composition/CompilePanel.tsx`（阶段、耗时、任务 ID、错误原文、逐产物下载） |
| 产物下载端点 | `api/routes.py` 新增 `GET /compositions/jobs/{id}/artifact?index=N`（原来异步任务只给服务器路径，浏览器取不到） |
| **跨页存活** | 编译状态提升到应用级 `CompositionWorkspace`；离开/返回组卷页不中断轮询、不丢结果 |

### 7.2 列表筛选与批量操作

| 项 | 结果 |
| --- | --- |
| 服务端全库搜索 | `/papers?q=`（新增 `service/library.py` 的 `query` 参数，**过滤先于分页**，`total` 描述筛选后集合） |
| 排序 | `/papers?order=`（`series`/`year-desc`/`year-asc`/`questions-desc`/`questions-asc`），契约常量收敛到 `core/domain.py` |
| 输入节流 | 新增 `shared/ui/SearchField`（停顿 280ms 提交、回车立即提交、`Esc`/× 清空） |
| 控件复用 | 新增 `features/catalog/PaperFilters`，套卷页与组卷选卷区共用；下拉框全部带标签 |
| 批量选择 | 「选择本页全部」「本页加入组卷」「移除本页已选」；工作区新增 `addPapers`/`removePapers` |
| 检索到题目 | 检索命中跳转 `/papers?paper=<自然键>`，落地直接打开该套卷抽屉 |
| 打印顺序 | 已选套卷支持拖动排序（`shared/hooks/useDragReorder`，原生 HTML5 DnD，无新依赖），▲/▼ 按钮保留 |

### 7.3 可达性与防误操作

- 题目抽屉：`Esc` 关闭、背景锁定滚动、焦点进入抽屉、顶部可直接「加入组卷」。
- 清空日志、清空/删除组卷：统一 `shared/ui/ConfirmDialog` 二次确认。
- 快捷键 `/`、`[`、`Ctrl/⌘+G`、`Ctrl/⌘+Shift+P`、`Ctrl/⌘+Shift+E`、`?`、`Esc`，
  由 `shared/hooks/useHotkeys` 统一处理并跳过输入中的按键。
- 编译状态放在独立 Context（`useCompile`），避免 1.5 秒一次的轮询重渲染所有读取
  草稿的页面（含数百行套卷表格）。
- 前端下载产物必须带 `index`：多版式编译有多个产物，不带索引只会取回第一个。
  该缺陷已由单元测试与 `build/ui-artifacts-check.py` 各锁定一次。

### 7.4 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 类型检查 | `npx tsc -b --force` | 通过（strict，零错误） |
| 前端测试 | `npx vitest run` | **74 项通过**（13 个文件） |
| 前端打包 | `npx vite build` | 通过；入口约 311 KB，`PaperFilters` 独立分包 |
| 后端测试 | `python -m pytest tests` | **141 项通过** |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（60 bundle / 321 套 / 7062 题 / 70 图） |
| 架构边界 | `.\npee_math_papers\maintenance\test-architecture.ps1` | `Passed architecture audit` |
| 端到端（生产形态） | `python build\ui5-check.py` | 全库搜索命中全部来自目标系列、排序顺序正确、`?paper=` 深链打开抽屉并渲染题目、组卷选卷区控件齐全 |
| 多产物下载 | `python build\ui-artifacts-check.py` | A3+A4 两个产物按索引分别取回（文件名 `[A3] x.pdf` / `[A4] x.pdf`），越界索引 404 |
| 拖动排序渲染 | `python build\ui6-check.py` | 已选列表渲染 3 个拖动把手与提示 |
| 空白检查 | `git diff --check` | 无错误（仅 LF→CRLF 提示） |

> 新增后端契约参数（`q` / `order`）同时暴露给 HTTP 与 MCP，人类界面与 Agent 看到
> 同一套语义；`service/library.py` 实现一次，两处适配器只做转发。

---

## 8. 操作日志：区分度 + 请求/响应正文（本轮完成）

### 8.1 之前的形态与问题

日志只有 `ts / surface / kind / name / status / duration_ms / detail`，
`detail` 里至多是一个**摘要**（HTTP 只有 query 与 path 参数；MCP 的入参被压成
`[3 项]` 这类占位符）。因此「这次调用到底发了什么、回了什么」在日志里根本没有答案，
而这恰恰是排查 Agent 行为时最常问的问题。

### 8.2 记录能力

| 项 | 结果 |
| --- | --- |
| 事件结构 | 新增 `request` / `response` / `status_code` / `epoch_ms` 四个字段（`service/events.py`） |
| 载荷裁剪 | 新增 `build_payload()`：**结构化裁剪**（长字符串就地截断、集合截断并标注「另 N 项」、层级过深折叠），而不是把序列化后的 JSON 从中间砍断——后者会让一个超大的 `stem.text` 吞掉同一对象里的其他字段 |
| 二进制 | PDF / 图片等只记录 `content_type` 与字节数，日志绝不成为产物副本 |
| HTTP 中间件 | `api/logging.py` 从 `BaseHTTPMiddleware` **改写为纯 ASGI 中间件**：读 body 必须碰这条路径，而 `BaseHTTPMiddleware` 会重新流式化响应、在流式响应上丢 `Content-Length` |
| 请求体预读 | 声明了 `Content-Length` 的请求在进入应用前先缓冲。只在应用主动读取时才捕获会漏掉两类真实场景：**忽略 body 的端点**，以及**在依赖解析阶段就被拒绝的请求**——而这正是最需要看到载荷的失败 |
| MCP | 记录**完整入参与返回值**（不再只存 `arguments` 摘要）；返回值解析回 JSON 便于折叠；`[{ok:false}]` 这类批量失败会统计 `failed_items` |
| 搜索 | 关键字检索**覆盖请求/响应正文**，可查「哪个请求带了 math3」 |

### 8.3 前端区分度

- **来源**：HTTP / MCP 各有左侧色条 + 标签（形状与颜色同时区分，不只靠颜色）；
- **HTTP 行**：方法徽章（GET 蓝 / POST 绿 / PUT·PATCH 琥珀 / DELETE 红）+ 真实状态码
  （2xx 绿 / 4xx 琥珀 / 5xx 红）；
- **MCP 行**：工具名加粗；
- **正文**：带「正文」徽章的行展开后，请求体与响应体并排显示（`features/logs/PayloadView.tsx`），
  JSON 逐层折叠、可复制；二进制显示为「二进制内容（类型），已记录大小但未保存正文」；
- **概览卡**：显示 MCP/HTTP 条数、含正文条数、5xx/4xx 计数。

### 8.4 顺带修掉的两个真实缺陷

| 缺陷 | 说明 | 修复 |
| --- | --- | --- |
| **日志页永远看不到新事件** | `EventLog.read()` 从文件头开始收集，凑够 `limit` 就停止，再整体反转。日志长于 `limit`（1792 条 vs `limit=300`）时，返回的是**最旧的 300 条倒序**，而不是「最近 300 条」。页面于是长期显示一天前的流量，新请求根本不出现 | 改为 `deque(maxlen=limit)` 滑动窗口 + 归档文件先读，取**最后** `limit` 条匹配项。新增 3 个回归测试（含轮转归档与过滤场景） |
| **展开的行会被自动刷新折叠** | 行 key 含列表索引，每 3 秒刷新时新事件使所有索引平移，React 重挂载整个列表，用户展开的行被关闭 | 改为 `ts|name`（毫秒精度可唯一标识事件），仅在真实重复时追加序号 |

### 8.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **158 项通过**（新增 `test_service_events.py` 13 项、`test_api_logging.py` 4 项） |
| 前端测试 | `npx vitest run` | **81 项通过**（新增 `PayloadView.test.tsx`、`eventKeys.test.ts`） |
| 类型检查 | `npx tsc -b --force` | 通过（strict，零错误） |
| HTTP 正文 | `python build\logging-check.py` | 请求体与响应体均被记录；二进制仅记大小；错误请求仍留正文 |
| MCP 正文 | `python build\mcp-logging-check.py` | 入参与返回值完整；失败调用记 `error` + 异常类型 |
| 生产形态 | `python build\logs-check.py` | 300 行渲染，其中 89 个状态码单元格、129 个「正文」徽章、210 个方法徽章 |
| 载荷可见 | `python build\logs-payload-check.py` | 最新事件带完整请求/响应正文；打包产物含载荷查看器与配色类 |
| 兼容性 | `test_service_events.py::test_read_still_accepts_the_previous_schema` | **1787 条历史事件（旧 schema）仍可正常读取**，缺失字段回退为空 |

> 日志目录仍被 git 忽略；新增字段对旧事件是**可选**的，因此升级不需要迁移历史日志。

---

## 9. 统一套卷存储模式：单一文档契约（本轮完成）

### 9.1 问题：三个表面各说各话

先纠正一个前提：**链路上早已没有 CSV**。事实源始终是
`.npee-math-papers/papers/<bundle>/<n>.yaml`；仓库里唯一的 CSV 是
`maintenance/source-queue/source-queue.csv`（空表头），而 `migrate_papers.py` 的 CSV
逻辑指向**已退役的 `app/data/papers/`，现在必然失败**——是历史遗留。"YAML→CSV→前端"
的印象来自 `collections/README.md` 与 `AGENTS.md` 里过时的措辞。

真正的问题是**缺少共享的线上表示**：

| 侧 | 形状 |
| --- | --- |
| 读取返回 | `{ summary: {…含派生字段…}, questions: [...] }` |
| 写入期望 | `{ paper: {…}, questions: [...] }` |

后果不只是"看着别扭"：`ingest_document` 用 `document.get("paper") or {}` 取值后
**回退到函数参数**，所以一个结构不符的载荷会"静默成功"，写入调用者从未指定的内容。
实测把读取结果直接回写也确实"成功"——靠的是默认值兜底，而不是契约。

### 9.2 契约：读写同形

新增 `core/paper.py`，成为套卷文档的唯一定义：

```json
{
  "schema_version": "3.0",
  "paper":     {"series_key": "...", "year": 2024, "subject": "math1", "paper_no": 1},
  "questions": [ ... ],
  "meta":      { …只读派生字段… }
}
```

**不变式：读取响应去掉 `meta` 就是一份合法写入载荷。**

| 规则 | 理由 |
| --- | --- |
| 文档键在顶层，派生字段进 `meta` | 去掉 `meta` 即得到写入载荷，机械可验证 |
| `meta` 字段写入即拒绝 | 防止载荷自称与题目不符的题数/名称 |
| 未知字段拒绝 | `paperNo` 这类拼写错误不再静默取默认值 |
| `content_hash` 自校验 | 携带则必须与服务端重算一致；**读响应里它被移入 `meta`**，否则"改一题再回写"会因回显的旧哈希而失败 |
| `schema_version`/`content_hash` 可缺省、给了就校验 | 兼容早期提取产物，同时拒绝过时版本 |
| 归一化只有一处（`normalize_questions`） | 存储写入、解析校验与哈希三者共用，避免"写入的哈希与重读不一致" |

### 9.3 落地范围

| 文件 | 变化 |
| --- | --- |
| `core/paper.py` | **新增**：`PaperIdentity`、`build_document`、`parse_document`、`derived_summary`、`merge_read_response`、`strip_meta`、`normalize_questions` |
| `core/store.py` | `PaperRecord.summary()/document()` 委托契约；`read_paper_document` 改用严格解析；`write_paper` 复用归一化；重导出 `PAPER_SCHEMA_VERSION` 保持公开名不变 |
| `service/library.py` | `get_paper` 返回 `文档 + meta` |
| `service/extraction.py` | `ingest_document(document, *, identity=None, replace=...)` 改用严格解析，去掉静默兜底 |
| `mcp/server.py` | 转发新签名，更新工具描述 |
| `frontend/` | `PaperDetail` → `PaperDocument`（`meta` 替代 `summary`） |
| `maintenance/test-architecture.ps1` | 登记 `core/paper.py` |
| 文档 | `ARCHITECTURE.md`、`APPLICATION.md`（新增契约章节）、`AGENT-QUICKSTART.md` |

### 9.4 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **176 项通过**（新增 `test_core_paper.py` 14 项 + 提取层 4 项） |
| 前端测试 | `npx vitest run` | **90 项通过** |
| 全库严格解析 | `python build\store-strict-check.py` | **321/321 解析成功，0 哈希不符，7062 题** |
| 契约端到端 | `python build\contract-check.py` | 读→写往返成功；改题后哈希变化；**6 类畸形载荷全部被拒**（只读字段/未知字段/错哈希/拼错键/缺字段/非法科目） |
| 无需迁移 | 同上 | 现有 YAML 已是该形状，**未改动任何题库文件** |
| 编译 | `python build\full-build-scan.py` | `papers=321 build_ok=321 build_fail=0` |
| 架构边界 | `.\npee_math_papers\maintenance\test-architecture.ps1` | `Passed` |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`，库级哈希 `b8737046…` 未变 |
| 空白检查 | `git diff --check` | 无错误（仅 LF→CRLF 提示） |

> 仍未做（等你决定）：是否让 API 也开放写入（当前写入为 MCP 专属），以及是否把
> `npee_list_bundles` 的过滤参数补齐到与 `npee_list_papers` 一致。

---

## 10. 前端只读边界 + 参数对齐（本轮完成）

### 10.1 结论：前端本就只读（现已显式锁定）

核查发现前端**从未**调用过题库写入端点，但这条边界此前没有被断言。现在由测试锁定：

| 检查 | 结果 |
| --- | --- |
| `POST/PUT/DELETE /api/papers` | 405 |
| 题库写方法（`ingest`/`ingest_document`/`delete_paper`/来源与捕获写方法） | **不在任何 HTTP 路由上** |
| 全部非 GET 路由 | 恰好 5 条：`/logs/clear`（清日志）、`/compositions/validate·build·compile·submit`（校验与产出 PDF 到 `build/`）——**均不写题库** |

新增 `test_the_http_surface_cannot_touch_the_paper_store` 与
`test_only_documented_non_get_routes_exist`（后者直接读 OpenAPI schema，因此新加一条
写路由会立刻失败）。

### 10.2 参数对齐：`list_bundles` 的过滤

此前 MCP 的 `npee_list_bundles` 在 **Python 里**过滤 `year`/`subject`，而
`GET /api/bundles` **根本不支持**这两个过滤——同一问题两边给出不同答案。

| 位置 | 变化 |
| --- | --- |
| `service/library.py` | `list_bundles` 增加 `years`/`subjects`，与 `list_papers` 同一套词汇；过滤只在用例层实现一次 |
| `api/routes.py` | `GET /bundles` 接受 `year`/`subject` |
| `mcp/server.py` | 删掉重复的 Python 过滤，改为转发参数 |
| 前端 | `BundleQuery` + `listBundles(query)`；套卷页把当前筛选一并传给 `useBundles`（此前只传 series，白拉全量） |

### 10.3 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **180 项通过**（+4） |
| 前端测试 | `npx vitest run` | **90 项通过** |
| 参数一致性 | `python build\parity-check.py` | 8 组过滤（含组合与空结果）**MCP 与 HTTP 条数完全一致** |
| 表面暴露面 | `python build\surface-parity.py` | MCP 34 工具 / HTTP 19 端点；仅 MCP 可达者全为写与诊断 |
| 只读边界 | `pytest tests/test_api_routes.py` | 写路由 405 / 不存在 404；题库统计在尝试写入前后不变 |
| 编译 | `python build\full-build-scan.py` | `papers=321 build_ok=321 build_fail=0` |
| 全库解析 | `python build\store-strict-check.py` | 321/321，0 哈希不符 |
| 架构 / 审计 | `test-architecture.ps1` · `audit_store` | `Passed` · `PASS` |

## 11. 日志布局 / 套卷查看 / 组卷操作 / 仓库清理（本轮完成）

### 11.1 操作日志：列对齐 + 去掉「正文」徽标

| 位置 | 变化 |
| --- | --- |
| `features/logs/LogPageRoute.tsx` | 删除 `log-payload-badge`（整行都可展开，徽标是噪音）；MCP 行与 HTTP 行补齐**占位单元格**（`log-cell-method` / `log-cell-slow` / 空 `log-code`），行头单元格数固定 |
| `styles/features.css` | `grid-template-columns` 由 `auto` 改为**固定轨道**：每个行头是独立 grid，`auto` 列按本行内容解析，没有「慢」徽标的行会变窄，导致其后的 成功/时长/时间 整体左移——这正是 MCP/HTTP 列不齐的原因 |
| `styles/responsive.css` | ≤900px 同时隐藏「慢」徽标**与其占位格**，剩余轨道与单元格数仍匹配 |

### 11.2 套卷查看：三级独立阅读器（与组卷解耦）

新增 `features/reader/`，路由 `#/reader`，三层全部写在 URL 上：

```text
系列 → 一卷的套卷 → 一套卷的 22 题
#/reader?series=…&year=…&subject=…&paper=…
```

| 位置 | 变化 |
| --- | --- |
| `features/reader/ReaderPageRoute.tsx` | 一级「卷」（`useBundles`）+ 二级套卷卡片；纯查看，**无勾选、无加入组卷、无编译** |
| `features/reader/PaperReader.tsx` | 三级：单列题面 + 吸顶跳转条（选择题/填空题/解答题 + 1..N 题号格），`IntersectionObserver` 高亮当前题 |
| `shared/question/QuestionView.tsx` | **新增**：从 `PaperDetailDrawer` 抽出图形/选项/整题渲染，抽屉与阅读器共用一份实现 |
| `features/catalog/PaperDetailDrawer.tsx` | 改为 import 共享渲染器；仍保留「加入组卷」（它是与组卷耦合的那条路径） |
| `frontend/src/app/routes.tsx` | 登记 `/reader`（工作区 → 套卷查看） |
| `styles/features.css` | 新增 `reader-*` 一节；≤1120px 单列 |

### 11.3 组卷页操作优化

| 项 | 变化 |
| --- | --- |
| 每行「加入」按钮 | **删除**；整行可点（`picker-row`，光标与悬停高亮），复选框内部点击 `stopPropagation` 避免双触发；行尾改为状态标签 `picker-state` |
| 表头全选 | 新增三态复选框（`indeterminate` 表示本页部分已选），可整页加入/移除 |
| 「删除当前组卷」 | 仅剩一个草稿时**禁用**（此前总是可点，弹确认框后必然失败） |
| 导入 JSON | **新增** `draftFromCompilePayload()`（`buildCompilePayload` 的精确逆运算）+ 文件选择按钮；导入总是**追加**新草稿，不覆盖 |
| 「首组题数」 | 仅 `解答结构 = 首组配对` 时显示（其余结构该值无任何作用） |
| PDF 份数 | 标题行显示「本次将生成 N 份 PDF」（`outputTargetCount()`，`output=both` 的三轴相乘即 8 份） |
| 编译完成播报 | `CompilePanel` 增加 `role="status" aria-live="polite"` 的隐藏文本（`.visually-hidden`） |
| `useCompositionWorkspace.ts` | `removePapers` 返回**实际移除数**；新增 `importDraft`（每次重新生成 id） |

### 11.4 清理与过期引用修正

| 项 | 变化 |
| --- | --- |
| `maintenance/migrate_papers.py` | **删除**：CSV 逻辑指向已退役的 `app/data/papers/`，必然失败；引用处（`audit_store`、`check_environment`、`service/rendering/catalogs.py`、`docs/AGENT-QUICKSTART.md` 工作流 C）改为指向 `npee_ingest_paper` |
| `frontend/src/domain/catalog/selectors.ts` | **删除**：零引用，且与 `models.ts` 的 `subjectNames` 重复 |
| `service/rendering/inline_tex.py` | 删除自带的 `balanced_group_end` 副本，改为 `from core.tex import balanced_group_end` |
| `collections/README.md` | 路径示例由旧措辞的 `app/data/` 前缀改为 `collections/`；题面来源由「注册表 + CSV」改为 `.npee-math-papers/papers/**/*.yaml` |
| `AGENTS.md` | 用例层约束由「不直接解析 CSV」改为「只读写 `.npee-math-papers`，不解析外部表格格式」 |
| `docs/APPLICATION.md` | 端点表补 `compositions/submit`、`jobs`、`jobs/{id}`、`jobs/{id}/artifact` |
| `docs/README.md` | 索引补 `UPGRADE-PLAN.md`、`FRONTEND-RESEARCH.md`、`GIT-DATA.md` |
| `docs/UPGRADE-PLAN.md` | P5 说明澄清：计划命名（`tex/repair.py` 等）与实际落地（`service/rendering/*`）的对应关系 |
| `docs/FRONTEND-RESEARCH.md` | §1 加注：本节路径属于被调研的**外部项目**，不是本仓库文件 |
| `build/doc-refs.py` | 校验器改为**按段落**判断上下文（外部调研 / 已退役 / 提案），并加显式 `ALLOWED_MISSING` 白名单；新增 `ROOT / "docs"` 解析基准。自测：临时插入一条不存在的路径会立即被报出 |
| `build/clean-build.py` | 清理 `build/`：保留编译产物（`_jiaji-compile/pdf`）、全部脚本与 JSON 报告、文档引用项；删除临时目录与一次性产物 |
| `build/` 已执行清理 | 删除 `_builder-test`、`_logs`、`backup-before-fix`、`blankrow-check`、`compositions`、`figure-cache`、`_jiaji-compile/generated` 等 12 项，释放 **29.9 MB** |
| 行尾 | 本轮改动引入的 CRLF 全部归一为 LF（`.gitattributes` 已锁定 `* text=auto eol=lf`） |

### 11.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **180 项通过** |
| 前端测试 | `npx vitest run` | **96 项通过**（+6：`draftFromCompilePayload` 往返、`outputTargetCount`） |
| 前端类型 | `npx tsc -b --force` | 无错误 |
| 前端构建 | `npx vite build` | 成功 |
| 日志页 DOM | `python build\logs-check.py` | 300 行全部有占位格；`log-payload-badge` = **0**；固定慢格 300 / 固定 method 格 98 |
| 日志页视觉 | `python build\logs-shot.py` · `logs-expanded-shot.py` | MCP/HTTP 的成功、时长、时间三列对齐 |
| 阅读器 | `python build\reader-check.py` | 22 个题目锚点、23 个跳转格、1 个 active 高亮 |
| 阅读器视觉 | `python build\reader-shot.py` | 一二级与三级布局正常 |
| 文档引用 | `python build\doc-refs.py` | 三节全部「无」 |
| 架构 / 审计 | `test-architecture.ps1` · `audit_store` | `Passed` · `PASS`（库级哈希 `b8737046…` 未变，321 套 / 7062 题） |
| 空白检查 | `git diff --check` | 无错误 |

---

## 12. 题目数据排版修正（本轮完成）

### 12.1 Σ／Π／⋃／∬ 的上下限落回正上正下（真实 bug）

类文件里的算子包装**从来没有生效过**，原因有两层，且互相掩盖：

| # | 问题 | 后果 |
| --- | --- | --- |
| 1 | 包装注册在 `\AtBeginDocument`。L3 钩子**按注册顺序**执行，而 `unicode-math` 在本类**之后**加载、注册得更晚，于是它把自己的 `\sum \prod \bigcup \iint \oint` 重新装回**裸 Unicode 数学字符**，把此前所有包装全部丢弃 | 上下限回到符号右下/右上 |
| 2 | 在导言区用 `\let\NPEEOriginalSum\sum` 抓原始算子，抓到的是 **amsmath 的旧 `\mathchar`**（`\sum@` = `\mathchar"1350`）。Cambria Math 下该码位渲染成**拉丁字母**：`Σ`→`P`、`∏`→`Q`、`⋃`→`S`、`⋂`→`T` | 修好上下限的同时把字形改坏 |

修法是**一处解决两个问题**：把「抓取原始算子」与「重装为带 limits 的算子」都搬到
`begindocument/end`——它在所有包的 `begindocument` 之后运行，因此既能拿到
unicode-math 的真字形，也不会再被覆盖。

### 12.2 积分上下限：区域名落到正下方

参考卷对**数值上下限**沿用期刊惯例写在右下角（`\int_0^1`、`\int_a^b`），这同时让
嵌在分式或矩阵格里的积分不会撑高行距，因此保持原样。**区域名**不同：`\int_L`、
`\oint_\Gamma` 读作「在 L 上的积分」，考研卷把它排在积分号正下方。

| 位置 | 变化 |
| --- | --- |
| `service/rendering/inline_tex.py` | 新增 `repair_integral_limits()` 与 `REGION_SUBSCRIPT_RE`：仅当 `\int` 的下标是**区域名**（大写拉丁字母，可再带上下标；或大写希腊命令）时补 `\limits` |
| `frontend/src/shared/tex/Tex.tsx` | 同名规则 `placeIntegralRegionLimits()`，保证 PDF 与浏览器呈现一致 |
| 修掉的自身缺陷 | 第一版用 `(?<![A-Za-z\\])` 排除前导字母，导致 `\displaystyle\int_L`（`\displaystyle` 紧贴 `\int`）漏匹配；改为只排除前导反斜杠 |
| 修掉的跨面不一致 | 前端 `normalizeOperatorLimits` 的操作符清单漏了 `oint`，于是 `\oint_L` 在 PDF 里居中、在浏览器里却在右侧 |

### 12.3 选择题排版：四合一 / 二合一 / 每行一个

`\NPEEChoicesOneLine`（四合一）**此前永远不可达**：`\NPEEChoices` 只在「二合一」与
「每行一个」之间二选一，且唯一阈值是 `.34\linewidth`，于是凡是落在 `.34` 与「二合一
单元格宽度」之间的选项都被判为「每行一个」，尽管它们明明放得下两个一行。

| 位置 | 变化 |
| --- | --- |
| `tex/npee-math-exam.cls` | `\NPEEChoices` 改为三档阶梯：`<.22\linewidth` 四合一、`<.45\linewidth` 二合一、否则每行一个。阈值按对应版式的单元格宽度折算（四合一格 `.235\linewidth`、二合一格 `.475\linewidth`），并留出 `\hfill` 与 `\NPEEChoiceIndent` 的余量 |

### 12.4 「全局 displaystyle」为什么没有采用

`\everymath{\displaystyle}` **做不到**把上下限移到正下方，且代价更高：

| 写法 | 结果 |
| --- | --- |
| `$\int_0^1 f$` | 上下限在右侧 |
| `$\displaystyle\int_0^1 f$` | 积分号变大，**上下限仍在右上/右下**（字形坐标：`1` 的横向中心落在积分号右侧） |
| `$\int\limits_0^1 f$` | 上下限真正居中于正上/正下 |

在 1156 条含积分的真实题干上的页数代价：

| 方案 | 页数 | 相对默认 |
| --- | --- | --- |
| 默认（现状） | 54 | — |
| `\everymath{\displaystyle}` | 61 | +7 |
| 类开关 `\NPEEIntLimitstrue`（`\limits` 实现） | 71 | +17 |
| 开关 + `\everymath` | 86 | +32 |

因此保留**类开关**（`\NPEEIntLimitstrue` / `\ExamSetup{operators/int-limits=always}`，
也可经 `document.hooks.preamble` 的包内 `.tex` 生效），并用最省的 `\limits` 实现
（`\mathop{\displaystyle}` 版本实测 +33 页，已弃用）。

### 12.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **194 项通过**（+14：区域积分规则、数值上下限保持、幂等、类负责其他算子） |
| 前端测试 | `npx vitest run` | **99 项通过**（+3：区域名落到下方、数值上下限留在右侧、类强制算子的集中判定） |
| 前端类型 / 构建 | `npx tsc -b --force` · `npx vite build` | 无错误 · 成功 |
| 全库语料测试不再抖动 | `corpus.test.ts` | 该用例本就渲染全库（321 套 / ~1.4 万块），实测 3.7s / 4.8s 逼近 vitest 默认 5s 上限；改为显式 60s 超时（属用例固有成本，非回归） |
| 字形回归 | 修复前后 A/B 对比编译 | 修复前出现 `P/Q/S/T` 拉丁字母，修复后**无** |
| 上下限位置 | 盒高/盒深 + 字形坐标 | Σ/∏/⋃/∬/∮ 全部正上正下；`\int_0^1` 保持右侧 |
| 开关语义 | 5 种设置路径（导言区 / 正文 `\ExamSetup` / 再关闭） | 全部符合预期 |
| 选择排版 | 全库 3207 道选择题 | **420 → 308 页（−26.7%），超框 0** |
| 全库真编译 | `python -m npee_math_papers.maintenance.verify_compile --matrix --collections` | **321/321 通过，0 泄漏；2 个组卷包通过** |
| 构建器扫描 | `python build\full-build-scan.py` | `papers=321 build_ok=321 build_fail=0` |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`，库级哈希 `b8737046…` 未变（321 套 / 7062 题） |
| 架构 / 文档引用 / 空白 | `test-architecture.ps1` · `build\doc-refs.py` · `git diff --check` | `Passed` · 三节「无」 · 无错误 |

> 题库 YAML **未改动**：以上全部是渲染层修复，`content_hash` 与库级哈希均不变。

---

## 13. 产品线：打印版 / 去掉宽松版 / 去掉水印（本轮完成）

### 13.1 水印与密级标记：默认关闭（真实 bug）

「不要加水印」表面上只是改两个默认值，实际不是。类文件在导言区**末尾无条件**
执行了一行：

```tex
\NPEESetSecurityLevel{3}
```

而该 setter 的契约是「设置等级即显示标记」——它内部会 `\NPEEEnableConfidentialMark`。
所以无论把 `\NPEEConfidentialMarkEnabledfalse` 写在哪里，都会被这一行重新打开，
每份产物都盖上「启用前 ★ 绝密」。

| 位置 | 变化 |
| --- | --- |
| `tex/npee-math-exam.cls` | 该行改为直接重建等级 3 的**文本**（`\NPEERebuildSecurityText` + `\renewcommand{\NPEESecurityLevel}{3}`），不再调用「设置即显示」的 setter；`\NPEEWatermarkEnabledfalse` 与 `\NPEEConfidentialMarkEnabledfalse` 成为真正的默认值 |
| `tex/CLASS-API.md` | 选项表默认值由 on 改为 off；示例改为 `watermark/show=false`；补注「设置 security/level 会同时显示标记」 |

A/B 实测（同一组卷、同一构建路径，仅替换类文件）：

| 类 | 结果 |
| --- | --- |
| 改动前 | 产物含「启用前 ★ 绝密」 |
| 改动后 | 产物**不含**，正文照常渲染 |

### 13.2 产品线：打印版取代宽松版

| 项 | 变化 |
| --- | --- |
| `a4-blank`（存储键不变） | 显示标签由「A4留白版」改为**「打印版」**；不再强制 A4，改为**与纸张无关**（A3 本来就补足 4 个逻辑页，因此在 A3 上等同于 `compact`）。存储键保留，避免迁移已写好的组卷包 |
| `spaced`（宽松版） | **退役**：仍是 schema 接受的存储值（旧组卷包继续可校验），但不再是默认、也不再出现在前端选项里。前端 `normalizeSpacing` 把存量 `spaced` 迁移到 `compact` |
| 默认产物 | 由「A4紧凑版」1 份改为**A3打印版 + A4打印版** 2 份 |
| `core/domain.py` | 新增 `PRODUCT_SPACINGS`（产品线）与 `DEFAULT_SPACING`，与 `SPACINGS`（schema 接受集）区分开；`SPACING_LAYOUT_REQUIREMENTS` 清空并转为通用规则表，校验层按数据查表而非硬编码 `a4-blank` |
| `service/composition.py` | `DEFAULT_DOCUMENT` / `DEFAULT_COMPILE` 改用 `DEFAULT_SPACING` 与 `PRINT_LAYOUTS`，默认矩阵覆盖两种纸张 |
| 前端 | `Spacing` 类型去掉 `spaced`；间距下拉改为「打印版 / 紧凑 / 两种间距」；页面与间距不再互相强制改写；新草稿默认打印版 |
| 组卷包 | `jiaji-eighty-five`、`chaoyue10-2024-2025`、`2024-yubingsen5-math1` 的 `spaced` 目标改为 `a4-blank`，并补齐缺失的 A3 打印版；去重后每包 4 个目标 |
| `maintenance/verify_compile.py` | 诊断矩阵补上 A3 打印版（`spaced` 保留其中，用于验证旧组卷包仍可编译） |
| MCP / CLI | `npee_build_composition` 的 `spacing` 默认值与 `--spacing` 可选值改为引用共享词汇表，不再各写一份 |

A3 打印版等价性实测（同一组卷分别编 `a3+compact` 与 `a3+a4-blank`）：
**页数、纸张尺寸、文本层三者完全相同**。

### 13.3 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **197 项通过**（+3：产品线与接受集分离、打印版标签、无纸张限制） |
| 前端测试 | `npx vitest run` | **100 项通过**（+1：退役模式迁移；改写 2 项：打印版不再强制 A4、`both` 不含已退役模式） |
| 前端类型 / 构建 | `npx tsc -b --force` · `npx vite build` | 无错误 · 成功 |
| 默认产物 | 真实组卷编译 | `[A3][][打印版]` + `[A4][][打印版]` 各 1 份，均无「启用前 ★ 绝密」，正文完整 |
| A3 等价性 | 两目标对照编译 | 页数 6 = 6、尺寸 1191×842 相同、文本层相同 |
| 组卷包校验 | `load_composition` | 3 个包全部通过，目标均为 4 个（A3/A4 × 紧凑/打印版） |
| 全库构建 | `python build\full-build-scan.py` | `papers=324 build_ok=324 build_fail=0` |
| 全版式真编译 | `python -m npee_math_papers.maintenance.verify_compile --matrix --collections` | **324/324 通过，0 泄漏；3 个组卷包通过** |

---

## 14. 提取文档规范化（本轮完成）

### 14.1 问题：提取简报是逐份手写的，必然漂移

按套卷提取题面时，每个子代理都要一份简报（自然键、来源哈希、capture 与页码、
题目结构、schema 形状、排版约定、调用顺序、报错对照）。此前这些是**手写**的，
同一批次里已经出现三类漂移：

- 措辞不一致：同一件事在不同简报里写法不同；
- 数字漂移：题目结构或分值抄错，甚至照搬另一个科目的结构；
- 新 bundle 要从头抄，容易漏掉边界条款（禁止项、只写 staging 等）。

### 14.2 做法：简报由题库事实生成

新增 `npee_math_papers/maintenance/extraction_brief.py`：

| 内容 | 来源 |
| --- | --- |
| 来源 PDF 与 sha256、页数 | `extraction.list_sources()` |
| capture_id 与页码范围 | `extraction.list_captures()` |
| 题数与分题型分值 | 同系列**同科目已完成**的对照套卷（取众数，个别 `points=null` 不污染结论） |
| 记号写法与全库出现次数 | 在 `papers/` 上**实测**，因此是可复核的事实而非记忆 |
| 无同类对照时 | 退回库级默认，并在简报里**显式标注**「这是默认结构，请复核」 |

用法：

```powershell
python -m npee_math_papers.maintenance.extraction_brief --series lilin6 --year 2027 --subject math2 --write
# -> .npee-math-papers/staging/lilin6-2027-math2/BRIEF.md
```

### 14.3 规范文档：所有 bundle 共用的部分单独成文

新增 `docs/EXTRACTION.md`，只写**不随 bundle 变化**的内容：边界、三角色分工
（转写/入库/核对）、题目形状、排版约定、执行流程、报错对照、常见坑。bundle 的
具体事实一律指向其生成的 `staging/<bundle>/BRIEF.md`。`AGENT-QUICKSTART.md` 的工作流 A 与
`docs/README.md` 的角色阅读表都已接入。

### 14.4 顺带修掉的两处文档失真

| 文件 | 问题 | 处理 |
| --- | --- | --- |
| `docs/MCP-SETUP.md` | 工具数写的是 **28**，实际已是 34（TeX 诊断工具加入后没更新），照做会以为安装失败 | 改为 34 |
| `docs/MCP-SETUP.md` | 工具清单**漏列**全部 6 个 TeX 诊断工具 | 补齐；已断言文档与 `server.py` 的 34 个工具一一对应 |

### 14.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **202 项通过**（+5：结构派生取众数、无对照时退回默认并标注、分值措辞、记号计数与题库一致、简报覆盖全部小节） |
| 简报生成 | `extraction_brief --series lilin6 --year 2027 --subject math2 --write` | 生成 `staging/<bundle>/BRIEF.md`；来源 sha256、capture 页码、22 题结构、8 条记号计数均与题库一致 |
| 边界情形 | 无 capture / 无对照套卷的 bundle | 正常生成，并给出「先登记来源/先建 capture」与默认结构警告 |
| 工具清单一致 | 文档 vs `mcp/server.py` | 34 / 34，无缺漏 |
| 文档引用 | `python build\doc-refs.py` | 三节全部「无」 |
| 架构 / 审计 / 空白 | `test-architecture.ps1` · `audit_store` · `git diff --check` | `Passed` · `PASS` · 无错误 |

> 本次只改文档与维护工具，**题库正文未改动**。
