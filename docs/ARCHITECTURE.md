# 架构

本项目是一套「MCP 服务 + 题库数据库」。所有规则集中在一个核心库，MCP、HTTP 与前端都是
它的薄适配器，因此行为不会分叉。

```text
npee_math_papers/                  Python 包
├─ core/                           纯库：规则与存储的唯一实现
│  ├─ canonical.py                 自然键、规范 JSON、内容哈希
│  ├─ domain.py                    领域术语唯一来源（科目/题型/版式/ID 语法）
│  ├─ paper.py                     套卷文档契约（读写同形的唯一形状）
│  ├─ tex.py                       行内 TeX 与 TikZ 校验
│  ├─ questions.py                 schema 2.0 校验（兼容入口）
│  ├─ question.py                  schema 3.0 强类型题目模型
│  ├─ serialize.py                 YAML 文档（LaTeX 用字面量块）
│  ├─ store.py                     题库存储：原子写、索引、发布清单
│  ├─ sources.py                   来源 PDF 与页面捕获
│  ├─ registry.py                  系列注册表
│  ├─ release.py                   内容哈希与发布清单
│  ├─ composition.py               组卷契约与校验
│  ├─ render_model.py              schema 3.0 -> 渲染模型
│  └─ figure_render.py             TikZ -> SVG（磁盘缓存）
│
├─ service/                        用例层，三个表面共享
│  ├─ context.py                   装配：store、registry、managers
│  ├─ library.py                   浏览、读取、检索、清点
│  ├─ extraction.py                登记来源、捕获、写入题目
│  ├─ capture.py                   来源 PDF -> 页面 PNG
│  ├─ composition.py               组卷构建、校验、编译
│  ├─ tex_builder.py               组卷编译编排（对外入口）
│  ├─ tex_quality.py               TeX 质量用例（静态检查/渲染诊断）
│  ├─ rendering/                   编译内部构件
│  │  ├─ paths.py                  仓库/组卷包路径安全解析
│  │  ├─ text.py                   单行字符串与 TeX 转义
│  │  ├─ inline_tex.py             行内 TeX 校验与历史写法修复
│  │  ├─ validation.py             渲染模型校验
│  │  ├─ catalogs.py               由题库解析组卷引用的论文
│  │  ├─ content.py                题干/选项/子问/图形渲染
│  │  └─ document.py               版式目标、封面、Hook、水印、命名
│  ├─ events.py                    跨进程事件日志（JSONL）
│  └─ facade.py                    NpeeService
│
├─ mcp/                            Agent 的 MCP 工具（28 个）
├─ api/                            人类前端的 HTTP 接口
├─ launcher/                       本地启动器
│  ├─ main.py                      拉起 API 与前端
│  └─ static_server.py             提供 dist/ 并注入 API 地址（生产形态）
├─ frontend/                       人类网页管理台（React + Vite）
│  ├─ preferences/                 偏好中心：主题/密度/字号/强调色 → CSS 变量
│  ├─ app/                         组合根：Provider、路由表、布局、工作区
│  ├─ application/                 用例钩子（TanStack Query）与端口
│  ├─ domain/                      纯模型与选择器（无框架依赖）
│  ├─ infrastructure/              HTTP 网关（含 API 基地址解析）
│  ├─ shared/                      UI 基础件（Button/Field/Surface/Toast…）
│  ├─ features/                    页面（仪表盘/套卷/组卷/版本/日志/偏好）
│  └─ styles/                      tokens.css + app/features/responsive
├─ tex/                            LaTeX 排版类
└─ maintenance/                    迁移、审计、环境检查、提取简报生成

composition/                       组卷配置（只引用自然键）
dist/                              编译产物（PDF，不入库）
.npee-math-papers/                 题库数据库
```

## 边界

- 规则只在 `core/` 实现一次，任何适配器都不重复实现校验。
- `service/` 是唯一读写题库的位置。
- `mcp/` 与 `api/` 只把传输翻译成用例调用，逻辑极薄。
- `frontend/` 只调用 HTTP 接口，看不到题库路径。
- `tex_builder` 通过共享渲染模型读取题库，从不写入。

## 存储

```text
.npee-math-papers/
├─ papers/<series>-<year>-<subject>/<paper_no>.yaml   权威，一套一文件
├─ registry.json                                      系列名称与启用状态
├─ release.json                                       内容哈希与库级哈希
├─ index/                                             派生索引，可重建
├─ sources/<bundle>/source.pdf                        来源（不提交）
├─ captures/<bundle>/<capture>/pages/p####.png        页面证据（不提交）
└─ logs/events.jsonl                                  操作日志（不提交）
```

题目文件用 YAML 字面量块，因为正文是 LaTeX：反斜杠无需转义，行长可读。
索引、发布清单与 bundle 元数据不含 LaTeX，用紧凑 JSON。

## 数据流

```text
浏览    .npee-math-papers/papers -> NpeeService.library    -> HTTP JSON | MCP
写入    MCP 工具                 -> NpeeService.extraction -> 校验 -> 原子写 -> 重建索引
组卷    套卷选择                 -> NpeeService.composition -> 封印 content_hash -> TeX -> PDF
校验    组卷文档                 -> 重算 content_hash -> 漂移即拒绝
日志    HTTP / MCP 调用          -> events.jsonl -> 前端「操作日志」页
```

## 设计模式

- **单一核心库**：校验、哈希与契约在 `core/` 实现一次。
- **单一术语源**：科目、题型、版式、ID 语法等定义只在 `core/domain.py` 出现一次。
- **端口与适配器**：HTTP 与 MCP 是 `NpeeService` 的可互换适配器。
- **原子写**：每次写入都是临时文件 + 改名，读者不会看到半成品。
- **派生索引**：`index/` 与 `release.json` 可重建，不是事实源。
- **内容哈希绑定**：组卷封印它编写时所用的题目版本。
- **追加式事件日志**：跨进程汇总调用记录，供前端统一查看。
- **依赖注入**：`NpeeService` 绑定数据根；构建器经 `BuildOptions.store` 接收同一
  题库，绝不自行从全局环境解析，因此多库/临时库/测试都渲染正确题库。
- **分层错误**：`core/errors.py` 的 `http_status` 让 HTTP 适配器把「未找到/冲突/
  校验失败」映射为 404/409/400，而 MCP 仍以 `{"ok": false, "error": ...}` 返回。

## 工程设施

- `pyproject.toml` 声明包元数据、运行依赖与 `pytest` 配置。
- `tests/` 覆盖核心模型、存储、用例层、HTTP/MCP 适配器、TeX 规则与渲染；
  `tests/golden/rendering.json` 是生成 TeX 的黄金快照，保证重构不改变产物。
- 前端用 `vitest` + `testing-library`（`src/**/*.test.tsx`），覆盖域逻辑、偏好、
  网关、组卷工作区、路由表与关键组件。
- 前端设计令牌集中在 `styles/tokens.css`：组件只消费 CSS 变量，因此主题/密度/
  字号/强调色的切换是一次 DOM 变量写入，而不是组件重渲染。
- 前端路由使用 **hash** 历史：生产由静态服务器提供 `dist/`，无 SPA 回退，
  路径式深链刷新会 404；hash 不受影响。API 基地址由启动器注入 `index.html`
  （`window.NPEE_API_URL`），运行时可解析，无需为不同端口重新构建。

```powershell
python -m pytest                       # 全部单元/契约测试
python -m npee_math_papers.maintenance.verify_compile --matrix --compositions  # 端到端
cd npee_math_papers/frontend; npm run typecheck; npm test; npm run build      # 前端
```

## 运行时

```text
题库数据库 -> NpeeService -> { HTTP API -> 前端,  MCP -> Agent }
组卷 -> CompositionService.compile -> tex_builder -> XeLaTeX -> PDF
```

生成的 TeX、日志与 PDF 位于被忽略的 `build/` 下。
