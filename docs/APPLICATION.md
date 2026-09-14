# 应用说明

应用由人类前端与 Agent MCP 两个表面组成，二者共用同一用例层
`npee_math_papers.service`。

| 表面 | 目录 | 使用者 | 入口 |
| --- | --- | --- | --- |
| HTTP API | `npee_math_papers/api/` | 人类前端 | `python -m uvicorn npee_math_papers.api.main:app` |
| MCP | `npee_math_papers/mcp/` | Agent | `python -m npee_math_papers.mcp.server` |
| 启动器 | `npee_math_papers/launcher/` | 人类 | `python -m npee_math_papers` |
| 前端 | `npee_math_papers/frontend/` | 人类 | 由启动器托管 |

## 启动

```powershell
.\start-npee.ps1
```

启动器会拉起后端 API 与前端，并打印前端地址。端口可改：

```powershell
.\start-npee.ps1 -WebPort 5173 -ApiPort 8766
```

前端形态由启动器自动选择：存在 `frontend/dist/` 时用静态产物（无需 Node）；否则回退到
Vite 开发服务器。

## 数据边界

HTTP API 与 MCP 都只依赖 `NpeeService`，不直接读写题库文件。题库读写集中在
`npee_math_papers/core/store.py` 的 `PaperStore`。前端保存的是套卷自然键与组卷配置，
请求接口时才读取题面。

## 表面职责：前端只读

**人类前端是对题库的只读视图。** 题库正文的写入只经 MCP（Agent），因此浏览器里的
误操作不可能改到一套卷子。这条边界由 `tests/test_api_routes.py` 锁定：

- `POST/PUT/DELETE /api/papers` 一律 405；
- 题库写入方法（`ingest` / `ingest_document` / `delete_paper` / 来源与捕获的写方法）
  **不出现在任何 HTTP 路由上**；
- 全部非 GET 路由只有 5 条，且都不是题库写入：

| 路由 | 做什么 | 能改题库吗 |
| --- | --- | --- |
| `POST /logs/clear` | 清空操作日志 | 否 |
| `POST /compositions/validate` | 校验组卷与版本绑定 | 否 |
| `POST /compositions/build` | 由选择生成组卷文档 | 否 |
| `POST /compositions/compile` | 编译并产出 PDF 到 `build/` | 否 |
| `POST /compositions/submit` | 提交后台编译任务 | 否 |

两个表面共用同一套过滤词汇：

| 端点 | 工具 | 可过滤 |
| --- | --- | --- |
| `GET /api/papers` | `npee_list_papers` | series / year / subject / paper_no + `q` + `order` |
| `GET /api/bundles` | `npee_list_bundles` | series / year / subject |
| `GET /api/series` | `npee_list_series` | — |

过滤在用例层实现一次（`LibraryService`），适配器只做参数翻译——此前 MCP 的
`list_bundles` 在 Python 里过滤，而 HTTP 端点根本不支持同样的过滤，两边对同一问题
会给出不同答案。

## 题库存储

题库位于 `.npee-math-papers/`，一套试卷一个 YAML 文件：

```text
.npee-math-papers/papers/<series>-<year>-<subject>/<paper_no>.yaml
```

`core/registry.py` 维护系列注册表，`core/release.py` 维护内容哈希与版本绑定，
`core/store.py` 负责原子写与派生索引。全部规则集中于核心库，三个表面共享。

## API 端点

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 服务状态与题库统计 |
| GET | `/api/overview` | 统计、系列与套卷分组 |
| GET | `/api/series` | 系列列表 |
| GET | `/api/bundles` | 套卷分组列表 |
| GET | `/api/papers` | 分页套卷摘要，可按系列/年份/科目/套号过滤 |
| GET | `/api/papers/{series}/{year}/{subject}/{no}` | 单套题面：规范文档（`schema_version`/`paper`/`questions`）+ 只读 `meta`；`with_questions=false` 仅返回摘要 |
| GET | `/api/papers/{series}/{year}/{subject}/{no}/questions/{q}` | 单题 |
| GET | `/api/search` | 题干与选项检索 |
| GET | `/api/release` | 发布清单与内容哈希 |
| GET | `/api/figures/preview` | 把指定 TikZ 图形渲染为 SVG |
| GET | `/api/logs` | 操作日志（HTTP 与 MCP 合并时间线） |
| POST | `/api/logs/clear` | 清空日志 |
| POST | `/api/compositions/validate` | 校验组卷与版本绑定 |
| POST | `/api/compositions/build` | 由选择生成组卷文档 |
| POST | `/api/compositions/compile` | 编译组卷，`dry_run` 时返回报告 |

任一请求都会写入共享事件日志 `npee_math_papers/service/events.py`，
前端「操作日志」页读取它。

## 套卷文档契约

套卷在**存储、MCP 与 HTTP 三处只有一种形状**，定义在 `core/paper.py`：

```json
{
  "schema_version": "3.0",
  "paper":     {"series_key": "...", "year": 2024, "subject": "math1", "paper_no": 1},
  "questions": [ ... ],
  "meta":      {"natural_key": "...", "question_count": 22, "content_hash": "...", ...}
}
```

规则：

- **读写的唯一不变式**：读取响应**去掉 `meta`** 就是一份合法的写入载荷。客户端无需
  维护两套结构。
- `meta` 内的字段（`natural_key`、`question_count`、`section_counts`、`figure_count`、
  `bundle`、`series_name`、`content_hash`）由服务端派生，**写入时会被拒绝**，避免
  载荷自称与题目不符的计数或名称。
- 未知字段一律拒绝（例如把 `paper_no` 拼成 `paperNo` 会报错，而不是静默取默认值）。
- `content_hash` 是磁盘上的**自校验**：若文档携带它，必须与服务端由题目重算的结果一致。
- `schema_version` 与 `content_hash` 在**写入时可缺省**，以兼容早期提取产物；一旦提供
  就会被校验，因此过时的版本或不符的哈希仍会被拒绝。

写入入口：MCP 的 `npee_ingest_document(document, replace=...)`；`replace=true` 才能覆盖。

## 前端结构

```text
npee_math_papers/frontend/src/
├─ domain/          模型与选择器（catalog、composition）
├─ application/     会话 Hook 与端口
├─ infrastructure/  HTTP 网关、浏览器草稿存储
├─ features/        dashboard、catalog、composition、logs 页面
├─ shared/          KaTeX 渲染与通用 UI
└─ app/             组合根与外壳
```

前端只调用 HTTP API，不持有题库路径。
