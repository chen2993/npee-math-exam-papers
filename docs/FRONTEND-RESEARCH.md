# 前端升级：参考系统研究与设计决策

> 目标：把管理台从「单文件状态 + 条件渲染 + 一个 470 行全局样式表」升级为
> 可扩展的后台形态。研究了三类优秀系统，每类吸收其核心模式。

## 1. 参考系统

> 本节出现的路径均属于被调研的**外部项目**（vue-vben-admin、ant-design-pro、refine），
> 不是本仓库的文件，仅用于说明借鉴来源。

### 1.1 vue-vben-admin（35.6k★，Vue3 后台的事实标准）

调查路径：`apps/web-antd/src/**`、`packages/@core/preferences/src/**`。

**吸收的模式**

- **偏好中心（preferences）**：全部外观与行为开关集中在一个类型化对象
  （`AppPreferences`），默认值在 `config.ts`，通过 `use-preferences.ts` 读写并
  持久化。关键点是**偏好 → CSS 变量**（`update-css-variables.ts`）：组件不读状态，
  只消费 `--radius` / `--font-size-base` / `--color-primary` 等变量，因此换主题
  无需改组件。
- **内置主题预设**：`BUILT_IN_THEME_PRESETS` 是「主题名 → 主色」的静态表，
  自定义主题用空色值回退到手选颜色。
- **路由分层**：`router/routes/core.ts`（静态）与 `routes/modules/*`（业务）分离，
  `router/guard.ts` 统一守卫。
- **布局模式**：`sidebar-nav` / `header-nav` / `header-side` / `full-content`
  等由偏好切换，移动端强制降级。

### 1.2 ant-design-pro（38.8k★，中后台模板的开创者）

调查路径：`config/routes.ts`、`config/defaultSettings.ts`、`src/pages/**`。

**吸收的模式**

- **路由即菜单**：`config/routes.ts` 用声明式数组同时描述路径、菜单名、图标、
  权限与嵌套结构；菜单由路由派生，不另写一份。
- **`defaultSettings.ts`**：布局/主题/标题/logo 作为单一配置对象，与业务解耦。
- **列表页范式**：查询区（`搜索 + 筛选 + 操作`）→ 表格 → 分页，三者状态互通；
  每页配套 `_mock.ts` / `service.ts` / `data.d.ts`，页面逻辑与数据访问分离。

### 1.3 refine（35.6k★，React 内部工具框架）

调查路径：`packages/core/src/components/**`。

**吸收的模式**

- **资源（resource）抽象**：CRUD 逻辑围绕「资源」声明，列表/详情/编辑复用同一套
  数据钩子。
- **错误边界与回退页**：`error/index.tsx`、`config-error`、`welcome` 等把异常状态
  当一等公民，而不是散落的 `if (error) return <div/>`。
- **可撤销队列**：`undoableQueue` 把「可撤销操作」抽象为队列，统一成功/失败通知。

### 1.4 其他对照

| 系统 | 借鉴点 |
| --- | --- |
| shadcn/ui | 组件是「你的代码」，而非黑盒依赖；`clsx` 组合类名 |
| TanStack Query | 服务端状态独立缓存，自带 loading/error/refetch |
| TanStack Table | 排序/筛选/分页是 headless 能力，与渲染解耦 |

## 2. 当前前端的问题

| # | 问题 | 证据 |
| --- | --- | --- |
| F1 | **无路由**：`AppShell` 用 `useState<View>` + 条件渲染，无法深链、刷新丢页、无浏览器历史 | `AppShell.tsx` |
| F2 | **无服务端状态层**：每个页面各自 `useEffect + useState + AbortController` 手写请求 | `useCatalogSession`、`LogPage` |
| F3 | **API 未用尽**：`/search`、`/release`、`/papers/.../questions/...`、`/compositions/jobs` 完全没接 | `ports.ts` |
| F4 | **无主题/偏好**：外观硬编码在 470 行 `styles.css`，无暗色、无密度、无强调色 | `styles.css` |
| F5 | **无错误边界/回退页**：异常只能整页 `app-error`，无 404、无降级 | `AppShell.tsx` |
| F6 | **无测试**：前端零测试 | 无 `*.test.*` |
| F7 | **打包无分包**：单 bundle 502 KB | `vite build` |
| F8 | **状态耦合**：`AppShell` 同时承担布局、路由、业务动作（导出/编译），已成新 god 组件 | `AppShell.tsx` 209 行 |

## 3. 升级设计

### 3.1 分层（保持既有 `domain/application/infrastructure/features` 契约）

```text
src/
├─ app/                 组合根、路由表、Providers
│  ├─ router.tsx        路由表（借鉴 antd-pro：路由即菜单）
│  └─ providers.tsx     QueryClient + Theme + Toast
├─ preferences/         偏好中心（借鉴 vben）
│  ├─ types.ts          类型化偏好对象
│  ├─ defaults.ts       默认值 + 主题预设
│  ├─ store.tsx         Provider + localStorage 持久化
│  └─ apply.ts          偏好 → CSS 变量
├─ domain/              纯模型与选择器（保持无框架依赖）
├─ application/         用例与数据钩子（改为 TanStack Query）
├─ infrastructure/      HTTP 网关（补全 search/release/questions/jobs）
├─ shared/              UI 基础件（Button/Panel/Table/Toast/ErrorBoundary…）
└─ features/            页面（由路由装配）
```

### 3.2 关键决策

| 决策 | 理由 |
| --- | --- |
| 用 **react-router + hash 路由** 替换 `useState<View>` | 深链、刷新保持、前进后退；路由表同时生成侧栏菜单。**必须用 hash**：生产环境由 `python -m http.server` 提供 `dist/`（无 SPA 回退），路径式深链刷新会 404，hash 不受影响 |
| 用 **TanStack Query** 管服务端状态 | 统一 loading/error/retry/缓存；删除各页面手写 `useEffect` 请求 |
| 引入**偏好中心 → CSS 变量** | 暗色/密度/强调色/圆角可实时切换且持久化；组件只消费变量 |
| **设计令牌**（tokens.css）+ 组件级样式 | 取代单一 `styles.css`，令牌集中、组件样式就近 |
| **代码分割**（路由级 lazy） | 首屏只加载当前页，降低 bundle |
| **错误边界 + 回退页** | 单页异常不拖垮整站；404/加载失败有明确界面 |
| **vitest + testing-library** | 让前端首次具备可回归的测试网 |

### 3.3 外观（不改变产品语义）

保持“学术、纸感”的既有观感：衬线标题 + 无衬线正文、青绿强调色、米色画布；
新增暗色主题与三档密度，均通过令牌驱动。

## 4. 验收

| 验收项 | 结果 |
| --- | --- |
| `npm run typecheck` | 通过（strict，零错误） |
| `npm run test` | **42 项通过**（域逻辑 / 偏好 / 网关 / 工作区 / 路由表 / Toast / 摘要裁剪） |
| `npm run build` | 通过；入口 **305 KB**（原 502 KB 单包），六个页面路由级分包，KaTeX 独立 chunk（263 KB，仅题目预览页加载） |
| 路由深链 | `#/papers?series=zhangyu8`、`#/search?q=级数` 可直接打开（hash 路由，静态服务器下刷新不 404） |
| 偏好持久化 | 主题/密度/字号/强调色/圆角写入 localStorage，刷新保持；跟随系统主题实时响应 |
| 新接入的接口 | `/search`、`/release`、`/papers/.../questions/...`、`/compositions/jobs*` 均在界面可用 |
| 端到端（生产形态） | 用启动器的真实流程（`_frontend_service` + 静态服务器 + API）实测：仪表盘显示 **321 套 / 7062 题 / 7 个系列 / 库级哈希**，套卷、检索、版本清单、组卷、日志五页均渲染真实数据 |

## 5. 顺带修复的既有缺陷（由新测试/实测发现）

| 缺陷 | 说明 | 修复 |
| --- | --- | --- |
| **生产形态下前端必然连不上 API** | 构建产物调用相对 `/api`，而生产由 `python -m http.server` 提供静态文件：既无代理也无 SPA 回退，`/api/*` 直接 404 → 页面永远显示「题库服务不可用」。启动器导出的 `NPEE_API_URL` 无人读取（代码只认构建期 `VITE_API_BASE_URL`） | 新增 `launcher/static_server.py`：提供 `dist/` 的同时把 API 基地址注入 `index.html`；新增 `infrastructure/http/apiBaseUrl.ts` 在运行时解析基地址（构建期变量 → 注入的全局 → `?api=` 参数 → 开发代理） |
| **CORS 只允许 5173** | `--web-port` 换端口后 API 拒绝前端请求 | 启动器按实际 web 端口写入 `NPEE_CORS_ORIGINS` |
| **组卷 id 可能非法** | `buildCompilePayload` 只把下划线换成连字符，大写字母会导致后端 `composition_id` 校验失败 | 统一归一化为 `^[a-z0-9][a-z0-9-]*$` |
| **检索摘要泄漏 LaTeX** | 检索命中是题面子串，服务端按 120 字截断会切断 `$…$`，渲染出裸命令 | 新增 `balancedExcerpt()`：在最后一个平衡的数学段边界回退 |
| **`/search` 缺少 `series_key`** | 前端无法从检索结果跳转到所属套卷 | `service/library.py` 在命中项中补充 `series_key` |

## 6. 第二轮：面向人类操作的可用性升级

第一轮解决的是「能不能用」（路由、状态、主题、测试）；第二轮解决的是「好不好用」：
每次操作需要多少点击、等待期间有没有反馈、误操作能不能挽回。

### 6.1 异步编译（最大的体验缺口）

此前「编译导出」是同步阻塞请求：一次全版式编译要几十秒到几分钟，页面只能挂着一个
转圈，用户既不知道进度，也不敢离开，超时还会丢掉全部结果。

| 项 | 实现 |
| --- | --- |
| 前端状态机 | `application/composition/useCompileFlow.ts`：`idle → submitting → running → succeeded \| failed`，1.5 秒轮询 + 每秒更新已用时间 |
| 进度面板 | `features/composition/CompilePanel.tsx`：阶段、已用时间、任务 ID、错误原文、每个产物的下载按钮 |
| 产物下载 | 新增 HTTP 端点 `GET /compositions/jobs/{id}/artifact?index=N`（原异步任务只返回服务器路径，浏览器无法读取；现按真实文件名流式返回）。前端下载按钮**必须带上 `index`**——多版式编译有多个产物，不带索引只会取回第一个（此缺陷已在单元测试与 `build/ui-artifacts-check.py` 各锁定一次） |
| **跨页存活** | 编译状态提升到 `CompositionWorkspace`（应用级 Provider），离开或返回组卷页都不会中断轮询、不会丢结果；面板文案的「可以离开此页面」因此才成立 |

### 6.2 列表筛选与批量操作

| 项 | 变化 |
| --- | --- |
| 全库搜索 | 套卷页与组卷选卷区的搜索框改为**服务端检索**（`/papers?q=`），不再只过滤当前页；`total` 与分页随之描述筛选后的集合 |
| 输入节流 | 新增 `shared/ui/SearchField`：输入即时反馈、停顿 280ms 才提交，回车立即提交，`Esc`/× 清空 |
| 排序 | `/papers?order=` 支持 `series` / `year-desc` / `year-asc` / `questions-desc` / `questions-asc`，排序常量收敛到 `core/domain.py` |
| 控件复用 | 新增 `features/catalog/PaperFilters`，套卷页与组卷选卷区共用同一套筛选/排序控件；所有下拉框都带标签（原来三个「全部…」无从区分） |
| 批量选择 | 工作表头「选择本页全部」、标题栏「本页加入组卷」、「移除本页已选」；工作区新增 `addPapers` / `removePapers`（批量新增不会把已选中的又切换掉） |
| 检索到题目 | 检索命中改为跳转 `/papers?paper=<自然键>`，落地即打开该套卷抽屉，而不是丢到未筛选的列表 |
| 打印顺序 | 已选套卷支持**拖动排序**（`shared/hooks/useDragReorder`，原生 HTML5 DnD，无新依赖）；▲/▼ 按钮保留，兼顾键盘与触屏 |

### 6.3 可达性与防误操作

- 题目抽屉：`Esc` 关闭、背景禁止滚动、焦点进入抽屉、顶部可直接「加入组卷」。
- 清空日志与清空/删除组卷：统一走 `shared/ui/ConfirmDialog` 二次确认。
- 快捷键：`/`、`[`、`Ctrl/⌘+G`、`Ctrl/⌘+Shift+P`、`Ctrl/⌘+Shift+E`、`?`、`Esc`，
  由 `shared/hooks/useHotkeys` 统一处理并跳过输入中的按键。

### 6.4 渲染开销

编译面板每 1.5 秒轮询一次，因此编译状态放在**独立的 Context**（`useCompile`）而非
工作区 Context（`useWorkspace`）中：否则每次轮询都会重渲染所有读取草稿的页面，
包括数百行的套卷表格。

### 6.5 验收（本轮）

| 检查 | 结果 |
| --- | --- |
| `npx tsc -b --force` | 通过（strict，零错误） |
| `npx vitest run` | **74 项通过**（13 个文件；新增 SearchField / 目录页交互 / 抽屉 / 深链选择 / 拖动排序等用例） |
| `npx vite build` | 通过；入口约 311 KB，筛选控件独立分包（`PaperFilters`） |
| `python -m pytest tests` | **141 项通过**（新增服务层与 HTTP 层的搜索/排序用例） |
| 端到端（生产形态） | `build/ui5-check.py`：搜索命中全部来自目标系列（60 行）、排序顺序正确、`?paper=` 深链打开抽屉并渲染题目、组卷选卷区控件齐全 |
| 多产物下载 | `build/ui-artifacts-check.py`：A3+A4 两个产物按 `index` 分别取回（116,896 / 118,108 字节，文件名 `[A3] x.pdf` / `[A4] x.pdf`），越界索引返回 404 |

### 6.6 后续调整（2026-09-21）：套卷页去组卷，降低耦合

6.2 里的「批量选择」把**浏览**与**组卷**绑在了一起：套卷页要拿到
`CompositionWorkspace` 才能渲染复选框、批量按钮与「打开组卷」，于是只读的列表页
也依赖草稿状态，两个功能无法单独演化。本轮按「套卷页只负责看」拆开：

| 项 | 变化 |
| --- | --- |
| 数据流 | 套卷页不再调用 `useWorkspace`；选择、排序、编译全部留在 `/compose` |
| 选择器 | 删掉 `features/catalog/useCatalogSelection`（它同时管抽屉与草稿），改为只管抽屉的 `usePaperDrawer`（保留 `?paper=` 深链） |
| 列表 | 去掉复选框列、「选择本页全部」批量条、「加入组卷」行内按钮与「打开组卷」入口，行内只留「查看题目」 |
| 抽屉 | `PaperDetailDrawer` 去掉「加入组卷」，只渲染题面；`Esc` 关闭与滚动锁定的行为不变 |
| 选卷入口 | 组卷页自己的选卷区（同样复用 `PaperFilters`，保留「加入本页全部」）成为唯一入口 |
| 回归防线 | 新增用例：套卷页**不得**出现组卷控件（`加入组卷` / `打开组卷` / 复选框），抽屉不得出现组卷按钮 |
| 后端改造 | `core/domain.py` 新增排序契约；`service/library.py` 支持 `query`/`order`，过滤在分页前完成；`api/routes.py` 与 `mcp/server.py` 暴露同样参数（人类与 Agent 看到同一套语义） |

### 6.7 后续调整（2026-09-21）：删去检索页与套卷查看页，清死代码

用户决定前端只保留「仪表盘 / 套卷 / 组卷 / 版本清单 / 操作日志」五个页面：
检索与逐题阅读都能在套卷页的抽屉里完成，两个独立页面维护成本不划算。

| 项 | 变化 |
| --- | --- |
| 页面 | 删除 `features/search/`（含 `excerpt.ts`）与 `features/reader/`，路由表移除 `/search`、`/reader` |
| 端口 | `CatalogGateway` 去掉 `search` / `getQuestion`，`HttpCatalogGateway` 同步删除；`SearchResult`、`SearchMatch`、`QuestionContext`、`questionFigures`、`subjectLabel` 等只剩定义没有引用的类型与函数一并删除 |
| 查询层 | 删除未被调用的 `useSeries`、`useCompileJobs`、`useCompileJob`、`useSubmitCompile`、`useCompileNow`、`useLibraryFacets` 及 `queryKeys.jobs/job`（编译轮的轮询直接用 `exportGateway.jobs/job`） |
| 快捷键 | `/` 从「打开题目检索」改为「跳到套卷列表并聚焦搜索框」 |
| 样式 | 删除 `features.css` 的 search / reader 两段与 `responsive.css` 的 `.search-bar*`、`.table-bulk-bar` 残留 |
| 顺带修复 | 选择题的答题括号此前映射成 `\square`（浏览器里显示成方框），改为 `\text{（\hspace{1.5em}）}`；存储层换行标记 `\n` 现在渲染为断行而不是字面量 |
| 工具 | 新增 `build/frontend-dead-exports.py`（只在本文件出现的导出）与 `build/frontend-dead-css.py`（样式表里没有源码引用的类），两者都是只读候选清单 |

### 6.8 后续调整（2026-09-21）：组卷包可编辑，间距与留白拆开

两个问题一起改：

1. **正式组卷包只有脚本能碰**。`composition/<id>/composition.json` 是仓库里的真实
   文件，但前端只能另存一份 localStorage 草稿，两边长期不同步。
2. **间距和打印绑在一起**。`print` 既是"打印交付"又顺手把间距改成紧凑，于是
   "想给解答题留书写空间"和"想给卷子补空白页"变成同一个开关。

| 项 | 变化 |
| --- | --- |
| 服务端仓库 | `CompositionService.list_packages / load_package / save_package`：列出、读取、写回组卷包；写入前先校验，路径解析带目录穿越守卫 |
| 适配器 | HTTP 新增 `GET /compositions/packages`、`GET|PUT /compositions/packages/{id}`；MCP 新增 `npee_composition_packages / npee_composition_package / npee_composition_package_save`（工具总数 34 → 37） |
| 前端打开 | 组卷页新增「仓库组卷包」一栏：点一下读成一份**新草稿**（`draftFromCompositionDocument` 会按 `compile.subjects` 展开 `$subject` 三科模板），原包不动 |
| 前端写回 | 「保存回 <包名>」只在"这份草稿确实来自那个包"时可用——判据是草稿 id，所以复制出来的副本不会误覆盖 |
| 间距 | 词表回到 `compact`（自然连排）/ `spaced`（解答题独占页面），**只影响解答题**；`document.solution` 与 `structure/pairCount` 控件作为"写了不生效"的死设置一并删掉 |
| 留白 | 新字段 `print`（前后端同名字段）：每套卷补足整页、封面后加空白页、目录凑偶数页；类里由 `\NPEEApplyTargetPrintPolicy` 单独开关，`\NPEEEnsureCompactMinimumPages` 更名 `\NPEEEnsurePrintMinimumPages`（旧名保留为别名） |
| 历史兼容 | 旧组卷包里的 `spacing=print / a4-blank` 读成「compact + 留白」，行为与以前逐字一致；`openapi` 与前端草稿都按同一规则归一化 |

实测四组合（2024 张宇八套卷 第 1 套，A4）：

| 组合 | 页数 | 现象 |
| --- | --- | --- |
| 紧凑 + 不留白 | 5 | 解答题自然连排 |
| 紧凑 + 留白 | 6 | 多出封面后的空白页 |
| 宽松 + 不留白 | 9 | 17–18 共用一页，之后每题独占一页 |
| 宽松 + 留白 | 10 | 同上，另加空白页 |
