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

---

## 15. 分式大小按位置判定（本轮完成）

### 15.1 问题：一律 `\dfrac` 会撑出行高

原规则是「一律 `\dfrac`、禁止 `\frac`」，但 TeX 按**当前数学样式**决定分式大小，
而下列位置**已经是降一级的样式**：

- 上下标（`x^{...}`、`\int_0^{...}`）；
- 分式自身的分子/分母（`\dfrac{...}{...}` 的两个参数）。

在这些位置写 `\dfrac`，会把 TeX 刚降下来的分式**重新放大**，反而撑出行高：

| 写法 | 高度 | 结论 |
| --- | --- | --- |
| 正文 `\dfrac{a}{b}` | 14.8pt | ✅ 正确 |
| `x^{\dfrac{a}{b}}` | **24.3pt** | ❌ 比正文还高 |
| `x^{\frac{a}{b}}` | 13.3pt | ✅ 正确 |
| `x^{\tfrac{a}{b}}` | 18.5pt | ❌ 仍然过大 |
| `\dfrac{\arctan\dfrac{1}{x}}{\sec x}` | **30.6pt** | ❌ |
| `\dfrac{\arctan\frac{1}{x}}{\sec x}` | 23.5pt | ✅ |

参考卷也是这个惯例：`\int_0^{\pi/2}` 与 `-\frac{x}{T}` 都是 script 体。

### 15.2 判据与实现

| 位置 | 处理 |
| --- | --- |
| `core/tex.py` | 新增 `fraction_positions()`：逐处判定 `script` / `nested` / `body`。按每个花括号组是被 `^_` 还是**分式参数**打开的来区分；`\dfrac` 有**两个**参数，且参数里可能再套分式，故参数计数用**栈**（单一计数器会被第一个嵌套分式冲掉，进而错判外层分母） |
| 同上 | `fraction_size_corrections()` 返回 `{偏移: 目标命令}`，服务端与前端共用同一套判据 |
| `service/rendering/inline_tex.py` | 新增 `repair_fraction_sizes()`，在渲染输出时纠正 |
| `frontend/src/shared/tex/Tex.tsx` | 同名规则 `normalizeFractionSizes()`，逐用例验证与服务端**输出一致** |
| `core/tex_audit.py` | 静态审计把大小不符报为 `fraction_size`（数据质量），覆盖嵌套情形 |

### 15.3 只纠正、不拒收

校验**不做硬拒**：题库读取时会重新校验，硬拒会让 245 套存量卷**无法加载**。
因此 contract 是——渲染层纠正输出，审计层报告数据质量，只有新写入才严格检查。
这两条测试断言也因此改写（`test_a_mis_sized_fraction_still_ingests`）。

### 15.4 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 修复规模 | 全库扫描 | **858 处 / 245 套卷**（script 739、nested 119） |
| 后端测试 | `python -m pytest tests` | **206 项通过**（+2：位置分类覆盖嵌套、纠正是双向的） |
| 前端测试 | `npx vitest run` | **101 项通过**（+1 且加强：嵌套与第二参数） |
| 前端类型 | `npx tsc -b --force` | 无错误 |
| 全库真编译 | `verify_compile --matrix` | **327/327 通过，0 泄漏** |
| 构建器扫描 | `python build\full-build-scan.py` | `papers=327 build_ok=327 build_fail=0` |
| 不被误伤 | `\sqrt{\dfrac{1}{x}}`、`\left(\dfrac{a}{b}\right)`、`\overline{...}` | 判定为 body，保持 `\dfrac`（这些位置不降级） |
| 题库审计 | `audit_store` | `PASS` |
| 文档引用 / 架构 / 空白 | `doc-refs` · `test-architecture.ps1` · `git diff --check` | 三节「无」 · `Passed` · 无错误 |

> 题库 YAML 未改动：全部是渲染层纠正，`content_hash` 与库级哈希不变。
> 已推送：`origin/main` = `126b11b`。

---

## 16. 仓库清理 + 题库与来源页面比对（本轮完成）

用户诉求：**清理文件树、删去无关 build 文件，然后对整个题库做一次与来源页面的比对，
深入分析识别问题，并写一份 `勘误清单.MD`。**

### 16.1 build/ 清理：从 186 MB 降到 25 MB

`build/` 是 git 忽略的工作区。上一轮清理后**又长回 186 MB**，
这次不是新增了文件，而是上一轮的清理规则**只认「文档引用与否」**，
而临时探针（`_z4p`、`_cy10*`、`_lfcheck`、`_ws-*.md` 逐卷工作表、页面放大图……）
一旦被某份文档提过一次，就永久留存。

新规则是**按命名约定判断**：以 `_` 开头的一律视为临时，
**即使文档仍在引用也照删**（文档在同一轮里更新）。同时把
`chaoyue10-2024-2025`、`chaoyue10-2024-2025-a4-blank` 加入 `KEEP_ALWAYS`
（它们是交付物 PDF 所在），其 `generated/` 列入 `DROP_INSIDE`。

| 项 | 清理前 | 清理后 |
| --- | --- | --- |
| 文件数 | 2715 | **101** |
| 体积 | 185.7 MB | **25.0 MB** |
| 顶层目录 | 24 | **3**（`_jiaji-compile`、两个 chaoyue 产物目录） |

`build/clean-build.py` 仍支持 `--apply` 前先演练（默认只报告）。
删除前有**路径守卫**：解析后必须仍在 `build/` 内，否则拒绝执行。

### 16.2 比对方法与新增工具

题面只来自页面 PNG 的原生视觉观察（源 PDF 是扫描件，无文本层，不用 OCR）。
为了让结论**可复算**，把一次性探针固化成 4 个脚本：

| 脚本 | 作用 |
| --- | --- |
| `build/store-scan.py` | 识别质量全库扫描：章节标题／水印／行内换行／重复选项／缺分／跨卷重复 |
| `build/store-duplicates.py` | 整题级别的跨卷重复检测（错配的最强指纹） |
| `build/imposition-scan.py` | 探测哪些来源 PDF 是**拼版**（横向页占比 ≥ 0.9） |
| `build/page-overlaps.py` | capture 页码占用冲突 ＋ 逐页图像哈希比对 |
| `build/leak-check.py` | 真编译指定套卷，检查 PDF 文本层的泄漏（重复标题／水印） |

### 16.3 核心发现：拼版 PDF 导致的卷次错位（A 级）

`.npee-math-papers/sources/zhangyu4-2026-math1/source.pdf` 是**拼版文件**：8 个物理页全部横向，
**每一物理页并排两个逻辑页**。于是 `capture.json` 记录的页码与逻辑页号对不上，
`unit-003` 记 `[4,5]` 实际取到「卷二的第 1、2 页 ＋ 卷三的第 3 页」。

后果：**入库 paper 3 混了两套卷**——q1–q17 来自预测卷（二），
q18–q22 来自预测卷（三）。实测同一 bundle 内 paper 2 与 paper 3：

| 指标 | 数量 |
| --- | --- |
| 题干完全相同（数学归一化） | **15 / 22**：q1,2,3,4,5,7,8,9,10,11,12,13,14,15,17 |
| 选项组完全相同 | **10 / 22**：q1–q10 |
| 整题完全相同 | 1：q1 |

而 paper 3 的 q18–q22 与 paper 2 确实不同——这正是「混卷」的指纹。

全库共 **4 个 bundle 是拼版**：`zhangyu4-2026-math1`、`zhangyu4-2026-math3`、
`liyanfang3-2026-math3`、`zhangyu8-2026-math3`。其余 3 个的页码记录是连续自洽的，
**所以问题不是「拼版」本身，而是「拼版文件的页码口径没有统一」**。

> 复算：`python build\imposition-scan.py`

### 16.4 新发现：渲染层未覆盖的三类「泄漏」（B 级）

这三类的共同点：**编译通过、结构校验通过、但印出来是错的**。
`audit_store`（查结构）与 `audit_tex`（查 TeX 语法）都不管内容语义，
所以此前没有任何检查能发现它们。三类都是**对受影响套卷真实编译后
检查 PDF 文本层**确认的，不是推断：

| 类别 | 规模 | 实测证据 |
| --- | --- | --- |
| 题干自带**章节标题** | 9 处 / 3 套卷 | 编译后「一、选择题：…」出现 **6 次**（应为 3 次），且第二次紧跟题号：`1. 一、选择题：1～10 小题…` |
| 题干携带**公众号水印** | 13 处 / 6 套卷 | 编译后 PDF 文本层出现「（公众号：风中羽小易）」，有的独占整个题干 |
| 行内数学里的**游离 `\\`** | 13 个字段（20 处）/ 4 套卷 | `$f_1(x)=y_2(x),\\ f_2(x)=y_1(x)$` 被排成两行；`(|α_1|)²=k_1` 被拆成三行 |

判别规则的要点：`\\` 在**对齐环境**（`array`/`matrix`/`cases`/`substack`）内
是行分隔符，**合法**；只有对齐环境之外、且位于**数学模式内**的 `\\` 才是缺陷。
`build/store-scan.py` 按此实现（用栈跟踪环境深度与宏深度，并跟踪 `$` 状态）。

### 16.5 新发现：重复选项中的「凭空生成」（B 级）

| bundle | paper | 题号 | 判定 |
| --- | --- | --- | --- |
| `yubingsen5-2024-math1` | 1 | q6 | **识别错误**：A 丢了转置 `A^T`→`A`，于是 A 与 B 完全相同 |
| `yubingsen5-2025-math2` | 4 | q4 | **凭空生成**：源页 C 是**空白**，入库却填了 `$1$`，与 D 撞车 |
| `liyanfang3-2026-math2` | 1 | q5 | **原文如此**：源卷 C、D 两行本就相同，录入忠实 |

第二类尤其值得注意：它不是「漏读」而是「补出一个原文没有的值」，
因此**不能只靠「选项重复」这个信号去修**——必须回页面确认，
否则会把 `liyanfang3-2026-math2` 这种忠实记录也「修」坏。

### 16.6 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **206 项通过** |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（61 bundle / 327 套 / 7194 题） |
| 架构边界 | `.\npee_math_papers\maintenance\test-architecture.ps1` | `Passed` |
| 来源哈希 | 逐份比对 `source.json` 的 `sha256` | **61/61 通过**（0 不符） |
| 识别扫描 | `python build\store-scan.py` | 6 类共 **162 条候选** |
| 跨卷重复 | `python build\store-duplicates.py` | **1 组**（即 16.3 的 zhangyu4） |
| 拼版探测 | `python build\imposition-scan.py` | 4 个 bundle 拼版 |
| 页码冲突 | `python build\page-overlaps.py` | 33 组 / 7 个 bundle（2 组图像相同=合法共享页，31 组图像不同） |
| 泄漏复现 | `python build\leak-check.py` | `checked=5 leaked=5 clean=0`（5 套受影响卷全部复现） |
| 文档引用 | `python build\doc-refs.py` | 三节「无」 |
| 空白检查 | `git diff --check` | 无错误 |

### 16.7 交付物

- **`勘误清单.MD`**（仓库根，约 18 KB）：七节，含结论摘要、逐条证据、
  「待人工确认」、明确为 0 的检查项，以及 9 条修复优先级。

> 本轮**未改动题库正文与代码**：只清理了 `build/`、新增了 4 个可复算脚本，
> 并写出勘误清单。上表 1–9 项修复待用户确认后再动题库（题库受 Git 版本管理，
> 按 `AGENTS.md`，写入真实题库前必须显式指定）。

---

## 17. 数学字体改为 Times 家族（本轮完成）

用户诉求：**"我们的字体和他好像有一些不一样……分析出字体，然后告诉我"**，
确认后要求改动并编译。

### 17.1 差异定位：正文一致，**只有数学公式不同**

对成品 PDF 与来源 PDF 的**嵌入字体表**逐字符统计（不靠观感推断）：

| | 正文拉丁 | 正文中文 | **数学公式** |
| --- | --- | --- | --- |
| 原卷 | Times New Roman | SimSun | **Times New Roman Italic + Symbol** |
| 我们（改前） | Times New Roman ✅ | SimSun ✅ | **Cambria Math** ❌ |

原卷的公式是**两个字体拼出来的**：字母走 Times New Roman Italic，
符号（`∑ ∫ ∞ → ≤`）走 Adobe Symbol —— 即字处理软件时代的公式编辑器产物。
因此原卷的公式与正文同族；Cambria Math 是微软 2006 年为 Office 另做的字体，
笔画更重、字面更方，`a` 是双层结构，这才是"看起来不一样"的根源。

### 17.2 根因：类文件里的一句假设从未被核实

`npee-math-exam.cls` 原先写着：

```
% The reference examination source uses Cambria Math.  Prefer it when the
% Windows font is available ...
```

**这个前提是错的。** 遍历全部 61 份来源 PDF 的嵌入字体（18 份带文本层）：

| 统计 | 结果 |
| --- | --- |
| 使用 **Cambria Math** 的来源 | **0 份** |
| 使用 Times 家族（`TimesNewRoman*`）的来源 | 绝大多数带文本层来源 |
| 使用 `SymbolMT`（符号）的来源 | 6 份 |
| 其余 | `FSMathType`/`PMExtra`（字处理公式编辑器）、`MPDFAA+*` |

### 17.3 改动

| 位置 | 变化 |
| --- | --- |
| `tex/npee-math-exam.cls` L473–485 | 数学字体链改为 **TeX Gyre Termes Math → XITS Math → Latin Modern Math**（原为 Cambria Math → TeX Gyre Termes Math → Latin Modern Math） |
| 同上 | 注释改写：说明为何用 Times 家族，并记录"来源未使用 Cambria"这一实测结论 |
| 同上 L704–707 | 「legacy `\mathchar` 在别的字体里会渲染成拉丁字母」的注释改为与字体无关的通用表述（原注释指名 Cambria，改后会误导） |

选用 **TeX Gyre Termes Math**（GUST 出品的 Times 免费同族数学字体）为主，
XITS Math 为次选，Latin Modern Math 兜底（随 TeX Live 必装）。

### 17.4 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **206 项通过** |
| 成品嵌入字体 | 编译 `euclid3/2026/math2/3` | `TeXGyreTermesMath-Regular`（改前为 `CambriaMath`） |
| 全库构建器扫描 | `python build\full-build-scan.py` | `papers=327 build_ok=327 build_fail=0` |
| **逐套真编译 + 泄漏检测** | `python -m npee_math_papers.maintenance.verify_compile` | **327/327 通过，0 泄漏** |
| 算子字形 | `\sum \prod \iint \oint \lim` 各取一卷目视 | σ/∏/∬/∮ 均正确，上下限在**正上正下** |
| 圈码字形 | `\textcircled{n}` 抽检 | 正常（`CMSY10` 提供合成圈，**改前改后一致**，非本轮引入） |
| 交付物 | `python build\compile-chaoyue.py` | 12 份 PDF 全部生成 |
| 题库审计 | `audit_store` | `PASS`（61 bundle / 327 套 / 7194 题） |
| 架构 / 文档 / 空白 | `test-architecture.ps1` · `doc-refs` · `git diff --check` | `Passed` · 三节「无」 · 无错误 |

### 17.5 一个必须验的回归点

类文件自身记录过：**在导言区抓取算子会拿到 amsmath 的 legacy `\mathchar`，
在其它字体下会渲染成拉丁字母**（`Σ`→`P`、`∏`→`Q`）。换字体正是会触发这一路径的
改动，因此本轮**逐套编译 327 套并逐个检查了 `∑ ∏ ∬ ∮` 的实际字形**，
确认仍走 `begindocument/end` 里抓取的 unicode-math 真字形，没有回归。

> 成品 PDF 见 `build/chaoyue10-2024-2025/pdf/`（12 份，含 A3/A4 × 打印/紧凑 × 三个科目）。
> 题库 YAML 与 `content_hash` 未改动：只改了排版类的字体选择。

---

## 18. 圈码 ①②③④ 还原度不足（本轮完成）

用户诉求：**"我们的①②③④这种带圈数字还原度也不高，分析分析"**。

### 18.1 现象

成品里的圈码与来源不同：数字是**衬线 Times 数字**、外面套一个**几何细圆圈**，
圈与数字之间空隙偏大、整体比正文高；来源用的是 **SimSun 自带的圈码字形**
（数字与圈是同一套设计，笔画粗细呼应，尺寸与正文协调）。

### 18.2 根因：一次「查不到就画一个」的查询**永远查不到**

类文件的取字逻辑是「先问字体有没有 U+2460，有就用真字形，没有就画一个圆」：

```
\NPEECircledFace\fontsize{10.5pt}{10.5pt}\selectfont
\iffontchar\font"2460 \char"2460 \else \NPEECircledDigitFallback{...} \fi
```

实测 `\fontname\font` 的结果是 **Times New Roman**，而 Times 没有 U+2460，
于是 `\iffontchar` **每次都答「没有」**，圈码**永远**走画圆分支 —— 哪怕 SimSun 明明有这个字形。

原因是类文件随后那一行：

```
\renewcommand{\NPEECircledFace}{\NPEEBodyFace}   % ← 罪魁
```

`\NPEEBodyFace` 是 `\newCJKfontfamily` 定义的 **CJK 字体族**。在 CJK 族里，
`\fontname\font` 报的仍是**拉丁底层字体**（Times New Roman），而不是 CJK 字体；
`\iffontchar` 因此问错了对象。**换任何 CJK 字体都查不到**。

### 18.3 对照实验（实测）

| 写法 | `\fontname\font` | `\iffontchar\font"2460` |
| --- | --- | --- |
| `\NPEECircledFace`（＝CJK 族，改前） | Times New Roman | **NO** ← 因此总走画圆 |
| `\NPEEBodyFace`（CJK 族） | Times New Roman | **NO** |
| `\newfontfamily\PlainSimSun{SimSun}`（**普通族**） | **SimSun** | **YES** ✅ |

根因不在「SimSun 没有圈码」，而在**用 CJK 族去做字形查询**。

### 18.4 改动

类文件里 `\NPEECircledFace` 本来就是用 `\newfontfamily` 定义的**普通族**
（每个分支都有 `\newfontfamily\NPEECircledFace{...}`），正确。
**只需删掉那行把它改指 CJK 族的 `\renewcommand`**，并补上说明为什么不能改。

| 位置 | 变化 |
| --- | --- |
| `tex/npee-math-exam.cls` L546–553 | 删除 `\renewcommand{\NPEECircledFace}{\NPEEBodyFace}`；注释改为说明「必须是普通族，CJK 族会让 `\fontname\font` 报错字体、导致查询恒假」 |

改动是**一行删除**，未新增任何宏。

### 18.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 取字路径 | 探针打印 `\fontname\font` 与 `\iffontchar` | `SimSun` / `YES`（改前 `Times New Roman` / `NO`） |
| 成品嵌入字体 | 抽检圈码所在页 | 圈码来自 `SimSun`，**不再**需要 `CMSY10` 合成圈 |
| 后端测试 | `python -m pytest tests` | **206 项通过** |
| 全库构建器扫描 | `python build\full-build-scan.py` | `papers=327 build_ok=327 build_fail=0` |
| **逐套真编译 + 泄漏检测** | `python -m npee_math_papers.maintenance.verify_compile` | **327/327 通过，0 泄漏** |
| 交付物 | `python build\compile-chaoyue.py` | 12 份 PDF 全部重新生成 |
| 题库审计 / 架构 | `audit_store` · `test-architecture.ps1` | `PASS` · `Passed` |

### 18.6 第二处：`\textcircled{N}`（80 处）此前走的是另一条渲染路径

修完上面那处后复检发现，题库里圈码其实有**两种写法**，而它们此前**渲染结果不同**：

| 写法 | 处数 | 修复前 | 修复后 |
| --- | --- | --- | --- |
| 原始 Unicode `①`（多为 `$①x>0$` 形态） | 513 | 画的圆圈 | SimSun 真字形 ✅ |
| `\textcircled{N}`（含 `$\text{\textcircled{1}}$`） | **80** | 仍走 `\textcircled` → **CSS 合成圈**：Times 数字 ＋ 组合圈 `U+20DD` | SimSun 真字形 ✅ |

两种写法在**来源里印出来是同一个字形**，却因入口不同而分叉：
`\textcircled` 是 LaTeX 的标准宏，与圈码字体无关，因此不受上面那处修复影响。

**做法**：在渲染层把两种写法**归一**——`content.py` 新增 `normalize_textcircled()`，
把 `\textcircled{N}`（裸用或包在 `\text{\textcircled{N}}` 里）改写为等价的原始 Unicode 圈码，
再进入原本就有的 `format_circled_markers()` 布局决策。这样两种写法**必然同形**，
而不是各自去修两条渲染路径。

| 位置 | 变化 |
| --- | --- |
| `service/rendering/content.py` | 新增 `normalize_textcircled()` 与两条正则；`format_circled_markers()` 入口先调用它 |
| 同上 | 越界值（如 `\textcircled{11}`）原样透传，不猜 |

归一后实测：`euclid3-2026-math2/3` 与 `yubingsen5-2025-math1/1` 的圈码全部由
**SimSun** 提供（`size=10.46`，与正文协调），不再出现 `CMSY10` 合成圈。

### 18.6 覆盖面

题库中共 **513 处**使用圈码，全部经 `\newunicodechar{①}{...}` 或 `\ExamCircledNumber`
汇入同一个 `\NPEECircledDigit`，因此**一处修复即全库生效**；另有 32 处
`\textcircled{N}` 走 `\textcircled`（不改动，它本来就正确）。

> 题库 YAML 与 `content_hash` 未改动：改的是排版类的一行字体选择，
> 加上渲染层的一处写法归一；两条路径都不触碰题面文本。

---

## 19. 题库大清洗：手写序号改为统一模板（本轮完成）

用户诉求：**"对 yaml 数据库做一次大清洗，很多地方还是题目人工标注 1234，
这个得要改成我们提供的模板，然后 .cls 也要改改——`\n①\n②\n③\n④\n` 这样，
和正常内容严格换行区分，我们主要是末尾的 `\n` 没有实现。"**

### 19.1 根因：`\n` 的机制早就在，坏在**定义**上

存储层与渲染层的约定本来就有：

| 环节 | 行为 |
| --- | --- |
| `service/rendering/inline_tex.py` | 把存储里的 `\n` 改写为 `\NPEEQuestionContinuation`（**早就有**） |
| `tex/npee-math-exam.cls` | `\NPEEQuestionContinuation` = `\par\noindent\hspace*{4.8mm}\ignorespaces` |

问题出在 `4.8mm` 的悬挂缩进。它是为「换行后接一个悬挂列表项」设计的，
但**任何**换行后面的内容都会被缩进。用户说的"末尾的 `\n` 没有实现"正是这个：

```
① 甲；
② 乙。
    则正确的个数为（  ）      ← 收尾那句被缩进了 4.8mm，看起来像列表的一部分
```

实测对比（同一段文字）：

| 写法 | 收尾句起点 |
| --- | --- |
| 无末尾 `\n` | `x0 = 51.0`（与正文齐平）✅ |
| 有末尾 `\n`（改前） | `x0 = 64.6`（被缩进 4.8mm）❌ |
| 有末尾 `\n`（改后） | `x0 = 51.0`（与正文齐平）✅ |

### 19.2 改动：`\par` 就够，缩进是多余的

| 位置 | 变化 |
| --- | --- |
| `tex/npee-math-exam.cls` | `\NPEEQuestionContinuation` 改为 `\par\ignorespaces`，删掉 `\noindent\hspace*{4.8mm}`；补注释说明为何只留 `\par` |

`\par` 单独用是**刻意**的：水平模式下它结束当前行；**垂直模式下它是空操作**，
因此重复的或末尾的换行不会多开一个空段落把后文顶下去。实测末尾写 1 个或 2 个 `\n`
版面完全一致。

### 19.3 数据清洗：三类手写序号

`tex/npee-math-exam.cls` 与文档约定「选择题里的并列结论用圈码、解答题的小问放
`subparts`」，但历史数据里存在三类手写序号。新增两个维护工具处理，都是**幂等**的。

| 工具 | 处理 | 规模 |
| --- | --- | --- |
| `maintenance/migrate_circled_sequence.py` | 行内 `①②③④` → `\n①\n②\n③\n④\n` 模板；裸 `\NPEEQuestionContinuation` 与裸 `\par` 归一为 `\n`；数学模式开头的 `$①…$` 把圈码提出数学模式 | **210** 字段 / 153 套 |
| `maintenance/migrate_manual_enumeration.py` | ① 选择题 `（1）（2）…` → 圈码模板（含答案键 `（1）（3）` → `①③`）② 解答题 `（1）（2）…` → 拆进 `subparts` ③ 选择题误存 `subparts` 的命题 → 并回题干 | **37** 字段 / 23 套 |

清洗后全库 **545** 个字段使用 `\n` 模板。

**清扫前后对比**：

| 检查项 | 清洗前 | 清洗后 |
| --- | --- | --- |
| 题干含裸 `\NPEEQuestionContinuation` | 12 | **0** |
| 题干含裸 `\par` | 3 | **0** |
| 行内 `①②③④` 未分行 | 490 | **0** |
| `（1）（2）` 手写序号 | 23 | **0** |
| 选择题误带 `subparts` | 18 | **0** |
| 数学模式开头的 `$①…$` | 8 | **0** |

### 19.4 三个真实难点（都不是机械替换能解决的）

| # | 难点 | 处理 |
| --- | --- | --- |
| 1 | **`\ne`、`\nabla`、`\nu` 会被误当成换行** | 三条正则都加渲染层同款守卫：不是「前面有反斜杠」也不是「后面跟字母」才算换行。实测这四个命令清洗后逐字节不变 |
| 2 | **`（1）（3）` 答案键不连续** | 不能用「连续序号」的判据；改为「整条文本除去序号后为空」才算引用，`（1）（3）`→`①③`，普通句子里的 `(2)` 不受影响 |
| 3 | **`（1）…` 是"命题"还是"小问"** | 按 `section` 判定：`choice` 是并列命题 → 圈码模板；`solution` 是子问 → `subparts`。**不能只看文本** |
| 4 | **解答题题干本身就是 `（1）…（2）…`**（无前导文字） | 拆进 `subparts` 后题干为空，而契约要求题干非空；用渲染层已有的 `{}` 占位（不打印任何内容），实测版面与来源一致 |

另有一类**必须保持原样**的：选择题答案是「个数」（`$1$`…`$4$`）而非「序号」。
工具用 `count_key()` 识别纯数字并跳过——这类题的题干写「正确的个数为」，
选项是数量，改成圈码就错了。

### 19.5 顺带修掉的自身缺陷

写工具时用测试暴露并修掉 4 个自己的 bug：

- `re.sub` 的**替换串**会把 `"\n"` 解释成真实换行，插入的是换行符而不是两字符标记；
  改用回调函数返回字面量。
- 正文里的换行标记去重时漏了守卫，会把 `\ne` 截断。
- 拼 `stem + subparts` 时有前导/尾随标记未清，产出 `\n\n` 双重换行。
- `choice_statements` 里用「最后一个 `；`」定位收尾句，遇到公式内的分号会切错；
  改为以 `\ExamSelection` 为锚点向前找。

### 19.6 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests` | **206 项通过** |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（61 bundle / 327 套 / 7194 题） |
| 构建器扫描 | `python build\\full-build-scan.py` | `papers=327 build_ok=327 build_fail=0` |
| **逐套真编译 + 泄漏检测** | `python -m npee_math_papers.maintenance.verify_compile` | **327/327 通过，0 泄漏** |
| 残留检查 | 全库再扫 `\NPEEQuestionContinuation` / 裸 `\par` / 行内圈码 / 手写序号 / 选择题带 subparts | **全部为 0** |
| 幂等 | 两个工具各再跑一次 | 输出「需要改写：0 处」 |
| 具体套卷 | `chaoyue10-2024-math1/1`（圈码）、`zhangyu8-2025-math1/8`（手写序号）、`yubingsen5-2025-math2/1`（子问拆分） | 编译并目视确认版面与来源一致 |

### 19.7 提取规范同步

`docs/EXTRACTION.md` 增补「命题序列与换行（必须遵守）」一节：给出完整模板、
明确**末尾的 `\n` 也要写**、说明选项里的答案组合不加 `\n`、解答题小问放 `subparts`。
表格里「命题序列」一行重写，并新增「手写序号 `（1）（2）` → 禁止」一行，
使后续提取不再产生同类问题。

---

## 20. 勘误清单落地：A 级卷次错位修复 + 打印版改名与前置页（本轮完成）

用户诉求：**按 `勘误清单.MD` 继续修复，并把交付物里的 `a4-blank` 直接改名
`print`**；同时设计打印版：**A4 每套卷 4 页、封面后留一页空白页、目录凑成偶数页**。
允许并行调度子代理（本轮子代理全部被限流，最终由主代理直接完成）。

### 20.1 A 级：`zhangyu4-2026-math1` paper 3 卷次错位（已修复）

上一轮只修好了 **capture**（`unit-003` 页码由 `[4, 5]` 改为 `[5, 6]`，补采物理页 6），
但**从未按卷（三）重转入库的 paper 3**——实测 paper 2 与 paper 3 仍有 15 道题干
逐字相同、10 道选项组相同，正是「前半来自卷二、后半来自卷三」的混卷指纹。

| 项 | 值 |
| --- | --- |
| 重转来源 | `captures/zhangyu4-2026-math1/unit-003/pages/p0006.png`（左半 = 卷三第 1 页 q1–q8，右半 = 第 2 页 q8–q17） |
| 保留 | q18–q22 取自卷三第 3 页（`p0005.png`），入库本就正确 |
| 工具 | `maintenance/retranscribe_zhangyu4_paper3.py`（默认演练，`--apply` 才写库） |
| 复核 | 重转后 paper 2 与 paper 3 **0 道题干相同**（原为 15 道）；`store-scan` 的 `cross_paper_duplicate` 归零 |
| 视觉证据 | 编译 paper 3 后逐页目视：第 1 页 q1–q7、第 2 页 q8–q17 与卷三源页逐题一致（q3 的 $\boldsymbol n\cdot\boldsymbol\alpha=0$、q6 的三阶矩阵、q7 的四向量命题均对） |

### 20.2 `a4-blank` → `print`：一次真实的选项 token 冲突

改名不是字符串替换那么简单：类文件里 `print` **已经是主题**（白底印刷色）的
选项 token，而 `a4-blank` 是间距。一个 LaTeX 选项 token 只能有一个含义，
**重复 `\DeclareOption` 会被静默丢弃**（实测：同名的第二个声明生效，第一个失效）。

| 位置 | 变化 |
| --- | --- |
| 类：主题 | `print` 改名 **`plain`**（`normal` / `white` 别名保留）；`\ExecuteOptions` 同步改 `a3,plain,spaced` |
| 类：间距 | `a4-blank` 改名 **`print`**；`a4-blank` 保留为历史别名，行为不变 |
| 类：内部标志 | `\NPEEAfourBlank` → `\NPEEPrintDeliverable`，注释里的「blank」概念一并改写 |
| 生成器 | `service/rendering/document.py` 把主题值 `print` 映射为类 token `plain`；间距逐字输出。默认 A4 打印版现在生成 `\documentclass[a4,plain,print]{npee-math-exam}` |
| 词汇表 | `SPACINGS` 增 `print` 并保留 `a4-blank`；`PRODUCT_SPACINGS = ("compact", "print")`；`SPACING_LABELS["print"] = 打印版`；`DEFAULT_SPACING = "print"` |
| 数据/前端/文档 | 两个组卷包的 4 个目标、`collections/2024-yubingsen5-math1.json`、前端 `Spacing` 类型与下拉、`normalizeSpacing`（`a4-blank` → `print`）、`CLASS-API.md` / `HUMAN-GUIDE.md` / `AGENT-QUICKSTART.md` 全部同步 |
| build 脚本 | `compile-chaoyue-a4blank.py` → `compile-chaoyue-print.py`；`make-chaoyue-collection.py`、`clean-build.py` 同步 |

### 20.3 打印版前置页：封面后留白页 + 目录凑偶数页

需求是双面打印时**每套卷都从右手页开始**，所以难点在前置页而不是正文——
正文本来就由 `\NPEEEnsureCompactMinimumPages` 补足到 4 个逻辑页（A4 打印版）。

| 新命令（类） | 作用 |
| --- | --- |
| `\NPEECoverBlankSheet` | 封面后补一页空白页；**仅在打印版生效**。生成器在 cover 之后调用（此时 collection 尚未开始，故只依赖已应用的 spacing policy） |
| `\NPEERecordTocFirstPage` / `\NPEERecordTocLastPage` | 把目录的首末页码写入 aux，供下一趟读取 |
| `\NPEEPadContentsToEvenPages` | 目录页数为奇数时补一页空白页；首趟 aux 缺失时**按「未知」跳过**，不会凭猜测补页 |

分两趟收敛是刻意的：补页写在目录之后，因此**不会移动目录自身的页码**，
第二趟读到的首末页稳定，第三趟结果不再变化。

**实测**（A4 / 数学一 / 3 套卷，同一组卷包分别编打印版与紧凑版）：

| 目标 | 总页数 | 结构 |
| --- | --- | --- |
| 打印版 | 16 | p1 封面 → **p2 空白** → p3 目录 → **p4 空白** → p5 第 1 套（p5–p8）→ p9 第 2 套 → p13 第 3 套 |
| 紧凑版 | 12 | p1 封面 → p2 目录 → p3–p6 第 1 套 → …（**前置页完全不变**） |

每套卷恰好 4 页、每套都落在奇数页（5 / 9 / 13），目录占偶数页（2 页）。

### 20.3b 第 9 项：剥离存储层分值标签（补充完成）

用户确认后执行。新增 `maintenance/strip_stored_score_labels.py`，**复用渲染层的
`strip_solution_score_label`**，因此「分值标签」只有一处定义。

- 清理 **85 处 / 16 套**（原清单记 83 处；本轮重扫按实际命中数为准）；
- 组卷包中与现状不符的 `content_hash` 一并重钉——顺带发现 `jiaji-eighty-five`
  在 HEAD 上就有 **270/270 条引用是过期钉**（前几轮改过题库但没重钉），
  现已全部与题库对齐，`verify_bindings` 三个组卷包全部 `ok: True`；
- 清理后全库「题干含 `本题满分`」**为 0**，成品 PDF 输出不变（渲染层本就剥离）。

### 20.4 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests -q` | **206 项通过** |
| 前端测试 | `npx vitest run` | **102 项通过** |
| 前端类型 / 构建 | `npx tsc -b --force` · `npx vite build` | 无错误 · 成功 |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（61 bundle / 327 套 / 7194 题） |
| 识别扫描 | `python build\store-scan.py` | 候选由 6 条降到 **1 条**（仅剩已判定「原文如此」的重复选项）；`cross_paper_duplicate` **0** |
| **逐套真编译 + 泄漏检测** | `python -m npee_math_papers.maintenance.verify_compile` | **327/327 通过，0 泄漏** |
| 打印版前置页 | 编译 3 套卷并读 PDF 文本层 | 16 页；空白页恰在 p2、p4；每套 4 页且起始页为奇数 |
| 紧凑版不受影响 | 同组卷编紧凑版 | 12 页，无多出空白页 |
| 空白检查 | `git diff --check` | 无错误 |

仍待人工确认的一项：**`liyanfang3-2026-math2/1/5` 的重复选项**——
已逐字回图核对，源卷 C、D 两行本就同印「既不充分也不必要条件」，
**录入忠实，不是缺陷**，因此保持原样（修它会改坏忠实记录）。

---

## 21. 读者勘误落地：22 条逐条回图核对（本轮完成）

用户诉求：**「别的 Agent 修复了一些问题，你继续修复，同步写文档记录工作状态。」**
数据源是读者提交的 `贾基八十五套卷勘误收集.xlsx`（22 条，在作者本机下载目录）。
上一轮修掉的是「题库 vs 来源页面」扫描清单（`勘误清单.MD`）；这一轮修的是**读者回执**，
两者有交集但不等价（读者的第 2 条正是上一轮已修的转置问题）。

### 21.1 先把两类错误分开，再决定改不改

读者提交的是「这题应该是什么」，对题库来说却有两种完全不同的性质：

| 性质 | 判据 | 处理 |
| --- | --- | --- |
| **识别错误**（我们的转写缺陷） | 回源页看不一致 | 直接修，修完与源页逐字一致 |
| **来源书自身有误** | 回源页看**一致** | 默认不改——题库的契约是忠实转写源页，改它就是有意偏离来源 |

所以判定标准不是「谁说得对」，而是**源页印的是什么**。22 条里 17 条落在第一类、
4 条落在第二类（另有 1 条一半一半）。

### 21.2 落地：19 处字段，11 套卷

逐条目视核对（`build/page-probe.py` 出整页图与放大裁片）后写入：

| # | 自然键 · 题 | 原状 | 修正 | 源页证据 |
| --- | --- | --- | --- | --- |
| 3 | `2025/math1/chaoyue10/6` q3 | `xy^2\boldsymbol{j}` | `xy^2z\boldsymbol{j}` | `p0073` 印 `xy²zj` |
| 5 | 同上 q13 | `\dfrac{y^2}{z^2}` | `\dfrac{y}{z^2}` | `p0078` 分子是 `y` |
| 6 | 同上 q17 | `f'_y(x,y)=2(y+1)e^x` | `f''_{xy}(x,y)=2(y+1)e^x` | `p0080` 印混合二阶偏导 |
| 17 | `2025/math2/chaoyue10/6` q6 | `\int_0^{\cos\theta}` | `\int_0^{\frac{1}{\cos\theta}}` | `p0027` 上限是叠分数 `1/cosθ` |
| 18 | 同上 q8 | `$A'$`、`\operatorname{tr}[(A-E)^2]` | `$A^*$`、`\operatorname{tr}[(A-E)^*]` | `p0028` 两处都是伴随 |
| 19 | 同上 q12 | `n\left[f\left(\frac1n\right)\right]^n` | `\left[nf\left(\frac1n\right)\right]^n` | `p0028` `n` 在方括号内 |
| 22 | 同上 q19 | `f''_{yy}` | `f''_{xy}` | `p0030` |
| — | `2025/math3/chaoyue10/6` q18 | `f''_{yy}` | `f''_{xy}` | `p0081`（勘误未提，同题比对发现） |
| 9 | `2024/math1/chaoyue10/2` q15 | `r(A^4+2A^3-3E)` | `r(A^2+2A-3E)` | `p0008`（同页的 `α₁` 与源页一致，未改） |
| 10 | 同上 q18 | `f''(t)+f'(t)=1` | `f''(t)+f(t)=1` | `p0008` 第二项无撇号 |
| 21 | 同上 q10 选项 A | `\left|\frac{X_1-X_2}{X_3+X_4}\right|` | `\frac{X_1-X_2}{|X_3+X_4|}` | `p0007` 分子无绝对值、分母有 |
| 12 | `2024/math1/chaoyue10/3` q6 | `A^*` 与 `C^T` | `A^*` 与 `C^*` | `p0011` 两者都是星号 |
| — | `2024/math2/chaoyue10/3` q9 | `A^*` 与 `C^{\mathrm{T}}` | `A^*` 与 `C^*` | `p0012`（勘误未提，同题比对发现） |
| 7 | `2024/math1/zhangyu8/1` q4 | `((2y)^3-3y)` | `(2y^3-3y)` | `p0002` 印 `2y³` |
| 16 | `2024/math1/zhangyu8/2` q4 | `I_2=\int_\Gamma f\,\mathrm{d}y` | `I_2=\int_\Gamma f\,\mathrm{d}s` | `p0010` 是弧长微元 |
| 13/14 | `2024/math2/zhangyu8/1` q2 图 | 实线/虚线整体画反 | 两条曲线样式对调 | `p0001` 源图 15 段虚线在上、20 段实线在上、10 段虚线在上 |
| 11 | `2025/math2/zhangyu4/4` q17 | `\int_0^xe^{t^2}` | `\int_0^{\frac{1}{x}}e^{t^2}` | `p0013` 上限是 `1/x` |
| 15 | `2024/math1/liyanfang3/1` q15 | `a_{ij}+A_{ij}=1` | `a_{ij}+A_{ji}=1` | `p0002` 第二项下标 `ji` |

其中两处**读者没提**：同一道题在数三/数二卷次里也有，逐科目比同题时发现同一批识别走样，
一并修正（数三 `f''_{xy}`、数二 `C^*`）。反过来，数一 `zhangyu8-2024-math1/1` q2 的
同一张「甲乙赛跑」图本来就画对，说明数二那处是**同一张图的另一份转写走样**——只修数二。

### 21.3 5 条属来源书自身有误，默认不改（待用户决策）

| 位置 | 源页现状 | 读者主张 | 说明 |
| --- | --- | --- | --- |
| `2024/math2/chaoyue10/5` q18 | `∫₀ˣ t²[y(t)+1]dt` | 应为 `[y'(t)+1]` | 按原式解得 `y` 含 `e^{±√2x}`；补撇号后化简为 `y=e^{2x}-x`，疑源书漏印 |
| `2025/math1/chaoyue10/6` q8 ④ | `P(A∪B̄)P(AB̄)≤P(A)P(B)` | 去掉上划线 | **数三同题就印 `P(A∪B)P(AB)`**（③ 亦作 `A^c-B`），读者很可能对照的是数三版；会改答案，建议先看官方答案 |
| `2024/math1/zhangyu8/2` q5 | 第一块印 `B CB`、第二块印 `B BC` | 统一为 `B BC` | 读者自己注明「这是张宇八套卷勘误、非文件错误」 |
| `2024/math1/chaoyue10/2` q15 | `(A-E)x=0` 的基础解系印 `α₁` | 应为 `α₃`（数三同题正是 `α₃`） | 照印则题干自相矛盾（`α₁` 是 `A` 的特征向量，`(A-E)α₁≠0`） |
| `2024/math1/chaoyue10/2` q4 选项 B | 左侧 `∮_L`、右侧 `∫_L` | 两侧都用 `∮_L` | 与 A/C/D 体例不一致，属漏印 |

这 5 条（含 21.2 里 q15 的 `α₁` 部分）在工具里放在 `SOURCE_FIXES`，默认**只报告不写**；
用户确认后一条命令落盘：

```powershell
python -m npee_math_papers.maintenance.apply_reader_errata --apply --include-source-fixes
```

### 21.4 新增工具与文档

| 路径 | 作用 |
| --- | --- |
| `npee_math_papers/maintenance/apply_reader_errata.py` | 22 条勘误的权威清单：每条带源页路径、目视依据、前后串；默认演练，`--apply` 落盘并重建索引/发布清单，同时重钉组卷包 `content_hash` |
| `build/page-probe.py` | 回图工具：整页渲染 / 放大裁片 / ink 密度切行定位（扫描件看下标、上划线、叠分数） |
| `build/check-bindings.py` | 组卷包绑定校验 ＋ `$subject` 模板引用钉的过期检查 |
| `docs/READER-ERRATA.md` | **读者勘误处理文档**：22 条逐条结论、标签→自然键映射、待决策项、复算命令 |

勘误标签映射不按名字硬套，而是按题面回图确定（例：读者的「24 张宇第二套 q4」实为
**张宇八套卷**第二套 q4，不是张宇四套卷）。映射表见 `docs/READER-ERRATA.md` 第三节。

### 21.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（61 bundle / 327 套 / 7194 题 / 70 图） |
| 后端测试 | `python -m pytest tests -q` | **206 项通过** |
| **逐套真编译 + 泄漏检测** | `python -m npee_math_papers.maintenance.verify_compile` | **327/327 通过，0 泄漏** |
| 组卷绑定 | `python build\check-bindings.py` | 三个组卷包 `ok=True`；`$subject` 钉 `stale=0`（改动后按原口径重钉 2 条） |
| 幂等 | `apply_reader_errata --apply` 再跑一次 | 「已写回 0 处改动」（全部已是目标值） |
| 架构 / 空白 | `.\npee_math_papers\maintenance\test-architecture.ps1` · `git diff --check` | `Passed` · 无错误（仅 CRLF 提示） |
| **成品目视复核** | 编译 9 套受影响卷（A4 打印版 37 页 + 数三单卷 6 页）逐页读图 | `rot` 题已含 `xy²z`；`1/cosθ`、`[n f(1/n)]ⁿ`、`tr[(A-E)^*]`、`2y³`、`C^*`、`I₂=∫ds`、`A_{ji}`、`f''_{xy}` 均按修正后排版；甲乙赛跑图与源图一致（实线在前/后段在下、中段在上）；未改的 `α₁`、`P(A∪B̄)` 保持与源页一致 |

> 题库 YAML 只改了 11 套 × 19 处字段；`content_hash`、`index/`、`release.json` 随
> `store.write_paper` 重建，组卷包钉同步对齐。本轮**没有**动 `.cls` 与渲染层。

---

## 22. 读者版勘误清单（LaTeX）+ 目录改名 composition/dist（本轮完成）

用户诉求（按对话顺序）：先把勘误清单做成给读者看的成品（Word → 改 LaTeX）；格式
「年份-试卷名-套数 / 题号: 原内容 -> 正确内容，变动处标红/绿」；随后要求
**顶部标题居中、不放其他文本**，**数学一/二/三分三份 PDF**，**去掉横线**，
**套卷名做二级标题**，**所有勘误合在一起**（必要时用括号标识）；另外：
**组卷目录改名 composition、编译产物放 dist、清理无关与失效文件**。
Git 历史重建与开源准备**用户暂缓**（先审阅几轮，再看前端）。

### 22.1 读者版清单：三份 PDF

| 项 | 说明 |
| --- | --- |
| 源 | `composition/jiaji-eighty-five/errata/errata-body.tex`（正文与版式）+ `errata-math1/2/3.tex`（三份驱动，各设科目后 `\input` 正文）——勘误随组卷包存放 |
| 产物 | `dist/jiaji-eighty-five/errata/贾基八十五套卷勘误清单-数学{一,二,三}.pdf`（各 1 页） |
| 版式 | 标题居中；套卷名为二级标题（左对齐加粗）；**条目只有一行**：`题号：原内容 → 正确内容`；红=原印刷、绿=更正；源书笔误用 `（原书）` 标注 |
| 内容 | 24 条 = 已修正 19 + 原书笔误 5，不再分「已修正 / 原书笔误」两个部分，按科目分段后合并排列（题号升序） |

实现要点（都是实测踩到的）：

* Word 版先做过一版（docx-js + Word 转 PDF 目视校对），按用户要求改 LaTeX 后**删除**；
* 三份 PDF 用「驱动文件 + 共用正文」实现（`\ifx` 比对 `\ErrataFlag`），
  **宏名不能用 `\flagM1` 这种字母+数字**——TeX 会把控制序列读成 `\flagM`，
  比较恒为假、正文整段消失（已改为 `\flagA/B/C`）；
* 首版 `④`（U+2463）在 Latin 字体里缺字形，改为「8（第 4 个结论）」；
* 三份 PDF 逐页读图复核：无缺字、无溢出，条目顺序与题号一致。

### 22.2 目录改名：`collections/` → `composition/`，产物 → `dist/`

| 项 | 从 | 到 |
| --- | --- | --- |
| 组卷包根 | `collections/` | `composition/` |
| 服务默认输出 | `build/compositions/<id>/output` | `dist/<id>` |
| 组卷包声明的输出 | `build/output`、`build/chaoyue10-2024-2025/output` | `dist/<composition-id>` |
| 校验开关 | `verify_compile --collections` | `verify_compile --compositions` |
| `.gitignore` | — | 新增 `/dist/`（产物不入库） |

同步改动：`README.md`、`docs/README.md`、`docs/ARCHITECTURE.md`、
`docs/AGENT-QUICKSTART.md`、`docs/UPGRADE-PLAN.md`、`composition/README.md`、
架构审计脚本（`test-architecture.ps1` 的必需目录/文件）、`service/composition.py`
（docstring 与默认输出目录）、`maintenance/apply_reader_errata.py`、
`maintenance/verify_compile.py`，以及 build/ 下的编译驱动脚本。

> 本节之前的小节里出现的 `collections/` 是**历史记录**，当时的目录就叫这个名字。

### 22.3 编译产物（实测）

| 包 | 产物位置 | 结果 |
| --- | --- | --- |
| `jiaji-eighty-five` | `dist/jiaji-eighty-five/pdf/` | **12 份**（3 科目 × A3/A4 × 打印/紧凑），829 s |
| `chaoyue10-2024-2025` | `dist/chaoyue10-2024-2025/pdf/` | **12 份**，160 s |
| 读者版勘误清单 | `dist/贾基八十五套卷勘误清单-数学{一,二,三}.pdf` | 3 份，各 1 页 |

`dist/<composition-id>/` 只放成品（`pdf/`）；生成的 `.tex`、aux 与日志等中间件写在
`build/<composition-id>/generated/`，可随时删除。

### 22.4 清理（实测）

`build/clean-build.py` 的规则随之更新：**产物已搬到 `dist/`，`build/` 只放可再生的中间件**，
因此不再有「必须保留的产物目录」。本轮删除：

| 类别 | 规模 |
| --- | --- |
| 临时探针与裁剪图（`_*.py`、`_show/`、`_v/`） | 约 48 MB |
| Word 版草稿（`make-errata-docx.cjs`、`docx2pdf.ps1`、`errata.docx/pdf`） | — |
| 旧产物目录（`build/chaoyue10-2024-2025/`、`build/compositions/`、`dist/demo-comp/`） | 4.5 MB |
| 失效报告（`*-now*.json`、`circled-seq*.json`、`manual-enum2/3.json`、`page-overlaps.json`） | 0.2 MB |
| 缓存（`.pytest_cache/`、`__pycache__/`） | — |

保留：文档引用的验证脚本与编译驱动（`store-scan`、`check-bindings`、`page-probe`、
`verify-errata-render`、`compile-chaoyue`、`collection-compile` 等）、
`tests/`（206 项回归测试）、题库与组卷包。

### 22.5 验收证据（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests -q` | 通过（改名后重跑） |
| 题库审计 | `python -m npee_math_papers.maintenance.audit_store` | `PASS`（61 bundle / 327 套 / 7194 题 / 70 图） |
| 架构边界 | `.\npee_math_papers\maintenance\test-architecture.ps1` | `Passed`（必需目录已改为 `composition/`） |
| 组卷绑定 | `python build\check-bindings.py` | 三个组卷包 `ok=True`，`$subject` 钉 stale=0 |
| 全量编译 | `python build\collection-compile.py` · `python build\compile-chaoyue.py` | 12 + 12 份 PDF 全部生成 |
| 读者版清单 | 三份 PDF 逐页读图 | 无缺字、无溢出 |
| 空白检查 | `git diff --check` | 无错误 |

---

## 23. 勘误归档到组卷包 + 套卷页去组卷（本轮完成）

用户诉求：**「整理一下文件夹，勘误应该放在套卷内」**；
**「前端套卷界面不要组卷功能，只负责看试卷列表和查看题目，降低耦合度」**。

### 23.1 勘误随组卷包存放

| 项 | 从 | 到 |
| --- | --- | --- |
| LaTeX 源 | `docs/errata/` | `composition/jiaji-eighty-five/errata/`（`errata-body.tex` + 三份驱动） |
| 编译产物 | `dist/贾基八十五套卷勘误清单-数学*.pdf` | `dist/jiaji-eighty-five/errata/`（README 里说明了包内附件的约定） |

编译改为把中间文件与 PDF 一起写到 `dist/`（`xelatex -output-directory="…"`），
源目录只剩 `.tex`；`.gitignore` 兜住就地编译产生的 aux/log。

### 23.2 套卷页只读

浏览与组卷此前共用一个选择器：套卷页为了渲染复选框与批量按钮，必须拿到
`CompositionWorkspace`，两个功能因此无法单独演化。

| 项 | 变化 |
| --- | --- |
| 数据流 | 套卷页不再依赖工作区；选择、排序、编译留在「组卷」页 |
| 选择器 | 删除 `useCatalogSelection`（抽屉 + 草稿二合一）→ 新增只管抽屉的 `usePaperDrawer`（保留 `?paper=` 深链） |
| 列表 | 去掉复选框列、批量条、行内「加入组卷」、「打开组卷」；行内只留「查看题目」 |
| 抽屉 | `PaperDetailDrawer` 去掉「加入组卷」，只渲染题面（`Esc`、滚动锁不变） |
| 文案 | 路由描述、HUMAN-GUIDE、套卷查看页脚注同步 |
| 回归防线 | 新用例断言套卷页**不得**出现组卷控件（`加入组卷`/`打开组卷`/复选框），抽屉不得出现组卷按钮 |

### 23.3 验收（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 前端类型 | `npx tsc -b --force` | 通过（strict，零错误） |
| 前端测试 | `npx vitest run` | **101 项通过**（17 个文件） |
| 前端构建 | `npx vite build` | 通过（套卷页分包 6.3 KB） |
| 勘误清单 | 三份 `xelatex` 重新编译（新路径） | 各 1 页，无缺字 |
| 题库 / 架构 | `audit_store` · `test-architecture.ps1` | `PASS` · `Passed` |
| 空白检查 | `git diff --check` | 无错误 |

### 23.4 套卷页视觉修正（同轮）

截图复核（`build/papers-shot.py`，Chrome headless，桌面 1500×1100 与移动 520×1000）
发现三处错位，逐项修好：

| 现象 | 根因 | 修法 |
| --- | --- | --- |
| 结果总数「327 套」压在搜索框右缘 | 计数仍是筛选栏的 `trailing`，而搜索框 `flex: 1` 把整行占满；`.tool-count` 的 `margin-left: auto` 无处可让 | 计数移到标题行（`.title-count`），与「刷新」同组；筛选栏只剩控件 |
| 「刷新」孤零零挂在右上 | 标题行右侧原本有三个按钮，去掉组卷后只剩一个，视觉重量落空 | 计数 + 刷新成组，靠右对齐；移动端 `.is-readonly` 下按钮不再被拉满整行 |
| 表头「操作」与右侧按钮不同列对齐 | 列宽规则按 7 列（含复选框列）写死，删列后宽度套错列；末列左对齐而按钮右对齐 | 按 6 列重写 `:nth-child` 宽度（34/9/10/14/9/24%），末列 `text-align: right`；删掉不再使用的 `.table-bulk-bar` 规则 |

顺带修掉一个同页可见缺陷：题干里的存储层换行标记 `\n` 之前**原样显示**（抽屉里能看到
字面量 `\n`）。`shared/tex/Tex.tsx` 现在把它转成 `<br />`，判据与迁移工具一致
（前面不是反斜杠、后面不跟字母，因此 `\nu`/`\ne`/`\nabla` 不受影响），行尾标记不产生空行；
新增 3 个用例锁定（换行生效、控制词不被截断、行尾不留断行）。

---

## 24. 前端精简：括号渲染、删两页、清死代码（本轮完成）

用户诉求：**「选择题的括号显示有 bug，渲染成方框了」**、
**「题目检索和套卷查看可以直接删去，不需要」**、
**「对前端进行一次升级，删去无关/失效的死代码」**。

### 24.1 选择题括号：`\square` → 全角括号

`shared/tex/Tex.tsx` 把 `\ExamSelection` 映射成 `\;\square\;`，浏览器里就画出一个方框，
读者会以为题目漏排。原卷印的是「（　　　）」留白，因此改为
`\text{（\hspace{1.5em}）}`（先在同版 KaTeX 上逐个候选实测，确认 `\hspace` 在 `\text`
里能正常撑开、不报错，见 `build/katex-probe.cjs`）。新增用例断言**不再出现 `□`**、
且渲染出全角括号。

### 24.2 删去「题目检索」与「套卷查看」

| 项 | 变化 |
| --- | --- |
| 页面 | 删除 `features/search/`（含 `excerpt.ts` 与用例）、`features/reader/`；路由表去掉 `/search`、`/reader`（侧栏只剩 仪表盘 / 套卷 / 组卷 / 版本清单 / 操作日志） |
| 端到端接口 | `CatalogGateway` 去掉 `search` / `getQuestion`，`HttpCatalogGateway` 同步删除（HTTP 侧端点仍保留，供 MCP 与外部调用） |
| 快捷键 | `/` 改为「跳到套卷列表并聚焦搜索框」（原来打开已删除的检索页） |
| 截图 / 检查脚本 | 删除 `build/ui5-shot.py`、`build/reader-check.py`、`build/reader-shot.py`；`build/ui5-check.py` 改为核对新的套卷页（列表只读、标题行总数、排序、筛选、`?paper=` 抽屉、括号渲染） |

### 24.3 死代码清理

先写两个只读探针再动手，避免"凭感觉删"：

| 工具 | 作用 | 结果 |
| --- | --- | --- |
| `build/frontend-dead-exports.py` | 找出只在自己文件里出现的导出 | 首轮 24 个候选 → 清理后 **0** |
| `build/frontend-dead-css.py` | 找出样式表里没有源码引用的类（会把 `` `button-${variant}` `` 这类**运行时拼接前缀**算作已用） | 18 个候选 → 真死只有 `.search-bar`、`.search-bar-field`、`.table-bulk-bar`（已删）；工具补上前缀规则后候选为 **0** |
| `build/frontend-unused-check.py` | 未被引用的 import | `no unused imports found` |

实际删除：未被调用的查询钩子 `useSeries` / `useCompileJobs` / `useCompileJob` /
`useSubmitCompile` / `useCompileNow` / `useLibraryFacets` 与 `queryKeys.jobs` / `job`；
只剩定义的 `questionFigures`、`subjectLabel`、`ReleaseEntry`、`SearchResult`、
`SearchMatch`、`QuestionContext`；search / reader 两段 CSS 与 `responsive.css` 里的残留。
其余「只有本文件引用」的导出（`RouteDefinition`、`Block`、`Choice`、`Section`、
`LibraryStats`、`LogStats`、`OpeningSettings`、`PRODUCT_SPACINGS` 等）改为**内部类型**，
不对外暴露但保留其表达力。

### 24.4 验收（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 类型 | `npx tsc -b --force` | 通过（strict，零错误） |
| 前端测试 | `npx vitest run` | **98 项通过**（16 个文件；删掉检索/阅读页用例，新增 4 项 TeX 用例） |
| 前端构建 | `npx vite build` | 通过；入口 312 KB，KaTeX 随套卷页分包（273 KB） |
| 死代码 | 三个探针 | 未引用导出 0、未引用 import 0、死 CSS 0 |
| 端到端（生产形态） | `python build\ui5-check.py` | 列表只读（组卷控件确认不存在）、总数在标题行、排序 2027→2022、筛选 32 行全为 zhangyu8/math1、`?paper=` 抽屉渲染题目、**括号为全角** |
| 目视复核 | `python build\papers-shot.py 1500 1100 drawer` | 四道选择题均显示「（　　）」，侧栏只剩五项 |
| 题库 / 架构 / 空白 | `audit_store` · `test-architecture.ps1` · `git diff --check` | `PASS` · `Passed` · 无错误 |

---

## 25. 组卷包可编辑 + 间距与留白分离（本轮完成）

用户诉求：**「优化一下前端组卷，让 composition 的也能被前端使用、修改」**、
**「间距和打不打印无关，打印的核心是留白，间距也只影响大题」**，
并提示**可以从历史里恢复旧的间距代码**。

### 25.1 间距与留白拆成两个正交的轴

修前两者挤在同一个 token 里：`spacing=print` 既是"打印交付"，又顺手把解答题排版
改成紧凑；`a4-blank` 同理。于是"给解答题留书写空间"和"给卷子补空白页"无法共存。

| 轴 | 取值 | 作用范围 | 实现 |
| --- | --- | --- | --- |
| **间距** | `compact` / `spaced` | **只影响解答题**：自然连排 / 17–18 共用一页、之后每题独占一页 | `\NPEESetCompactSpacing` / `\NPEESetSpacedSpacing`，由 `\NPEEApplyTargetSpacingPolicy` 选择 |
| **留白** | `print` 开 / 关 | **只加空白**：每套卷补足整页、封面后加空白页、目录凑偶数页 | `\NPEEApplyTargetPrintPolicy{1|0}` 控制 `\ifNPEEPrintDeliverable` |

旧的间距定义本来就在历史里（`\NPEESetSpacedSpacing` 把 `\NPEECompactfalse` 与
`\NPEEAnswerLayouttrue` 配对），本轮把它从"退役"状态恢复成正式词表；
`\NPEEEnsureCompactMinimumPages` 更名 `\NPEEEnsurePrintMinimumPages` 并只由留白
开关驱动，旧名保留为别名以免历史 `.tex` 失效。

历史兼容：组卷包里的 `print` / `a4-blank` 读成「compact + 留白」，行为与改前逐字一致
（`core.domain.split_spacing_axes` 是唯一折算处）。三个正式组卷包的 target 已归一化。

### 25.2 组卷包进前端

| 层 | 新增 |
| --- | --- |
| 用例层 | `CompositionService.list_packages / load_package / save_package`（写入前校验、路径带穿越守卫、`$subject` 模板按 `compile.subjects` 折算真实套数） |
| HTTP | `GET /compositions/packages`、`GET /compositions/packages/{id}`、`PUT /compositions/packages/{id}` |
| MCP | `npee_composition_packages`、`npee_composition_package`、`npee_composition_package_save`（工具总数 34 → 37） |
| 前端 | 组卷页新增「仓库组卷包」一栏：点一下打开成新草稿（原包不动），「保存回 <包名>」写回原文件；写回权限绑定草稿 id，副本不会误覆盖 |
| 死设置清理 | `document.solution` 与前端 `structure/pairCount` 控件是"写了不生效"的字段（生成器一直用间距覆盖它），删掉；后端仍接受该字段以兼容旧包，但不再使用其值 |

### 25.3 验收（实测）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 后端测试 | `python -m pytest tests -q` | 通过（206 项；新增/改写间距、留白、API 白名单用例） |
| 前端测试 | `npx vitest run` | **99 项通过**（16 个文件） |
| 前端类型 / 构建 | `npx tsc -b --force` · `npx vite build` | 零错误 · 通过 |
| **四组合真编译** | 2024 张宇八套卷第 1 套，A4 | 紧凑5页 / 紧凑+留白6页 / 宽松9页 / 宽松+留白10页 |
| 宽松版目视 | 逐页读图 | 17–18 共用一页，19 起每题独占一页并留出作答空白 |
| 组卷包仓库 | `list_packages()` | 三个包，套数 60 / 270 / 3，目标数 4 / 4 / 1 |
| 题库审计 / 架构 | `audit_store` · `test-architecture.ps1` | `PASS` · `Passed` |

> 后端测试本轮共 **207 项通过**；组卷包列表复算：`chaoyue10-2024-2025` 60 套 /
> 4 个产物，`jiaji-eighty-five` 270 套 / 4 个产物，`three-subject-template-smoke`
> 3 套 / 1 个产物（`build/check-packages.py` 可随时复跑）。

---

## 26. 组卷页去默认草稿 + 清掉无效按钮（本轮完成）

用户反馈：**「前端界面很乱，不要默认的组卷包，全靠导入就行。然后有些按钮按不了，
是完全无效的，你优化一下」**。

### 26.1 先量，再改

用 Playwright 驱动真实页面（静态服务器 + 注入 API 基址，与启动器同形态）枚举每个
控件的禁用状态、逐个点击观察 DOM/请求变化，并记录失败请求。结论：
**空状态下 11 个控件禁用、页面没有默认内容**，其中「保存回组卷包」在从未打开过包时
永远不可用；选卷行末尾的「加入」是纯装饰胶囊，看着像按钮却点了没反应。

### 26.2 改动

| 项 | 变化 |
| --- | --- |
| 默认草稿 | 工作区起始为空（原来自动造一个「数学试卷集」）；删除允许删到零，删空后显示空状态 |
| 空状态 | 只有「导入组卷 JSON」+ 仓库组卷包列表 + 「新建空组卷」，不再渲染空转的工具栏/设置面板 |
| 页头动作 | 图标按钮改为带文字的「编译导出 / 导入 / 导出」，导入入口与空状态共用一个隐藏 file input |
| 保存回包 | 按钮只在当前草稿确实来自某个包时渲染，不再出现永久禁用的图标 |
| 选卷行 | 「加入 / 移除」改为真按钮（原来是无响应的胶囊标签） |
| 题数回填 | 导入/打开组卷包后从套卷目录回填题数与系列名，未回填时不显示「0 题」 |
| 面板高度 | 已选面板 `min-height` 380px → 180px |
| 死代码 | 删除 `allSubjects`、`renameActiveDraft`、`.picker-state` 样式 |

### 26.3 验收（实测）

| 检查 | 结果 |
| --- | --- |
| 前端测试 | `npx vitest run` **100 项通过**（工作区用例改写为"先新建/导入再操作"，并新增"删到零"契约） |
| 类型 / 构建 | `npx tsc -b --force` 零错误 · `npx vite build` 通过 |
| 空状态 | 0 个禁用按钮；只显示导入入口与仓库组卷包 |
| 打开组卷包 | 「导出」触发下载 `composition-*.json`、「导入」打开文件选择框、「编译导出」发出 `POST /api/compositions/submit` 并进入轮询；无页面异常、无失败请求 |
| 死代码探针 | 未引用导出 0、未引用 import 0、死 CSS 0 |
| 后端 / 架构 / 空白 | `pytest` **207 项通过** · `audit_store` PASS · `test-architecture.ps1` Passed · `git diff --check` 干净 |
