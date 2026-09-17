# NPEE Agent 协作契约

本规则适用于整个仓库。子目录中的 `AGENTS.md` 可以补充更细的权限，但不能放宽
这里的安全边界，也不能覆盖用户尚未完成的改动。

## 活动事实源

- `.npee-math-papers/papers/<series>-<year>-<subject>/<paper_no>.yaml`：题库权威存储，一套一文件。
- `.npee-math-papers/registry.json`：系列注册表。
- `.npee-math-papers/release.json`：发布清单，记录每套卷的 `content_hash` 与库级哈希。
- `.npee-math-papers/index/`：派生索引，可由 `papers/` 重建，不作为事实源。
- `.npee-math-papers/sources/`、`captures/`、`logs/`：来源 PDF、页面证据与操作日志，已被 git 忽略。
- `npee_math_papers/core/`：无三方依赖的核心库，是校验、存储与组卷契约的唯一实现。
- `npee_math_papers/service/`：用例层，MCP 与 HTTP 均为其薄适配器。
- `npee_math_papers/tex/npee-math-exam.cls`：不含出版物内容的通用排版类。

## 术语

| 术语 | 含义 | 示例 |
| --- | --- | --- |
| series | 出版社系列 | `zhangyu8` |
| paper | 一套试卷 | `paper_no=7` |
| bundle | 系列 + 年份 + 科目 | `zhangyu8-2024-math1` |
| capture | 一次页面切分批次 | `unit-007` |

自然键为 `year/subject/series_key/paper_no`。

## 工作入口

Agent 通过 MCP 工具工作，工具清单与用法见
[`docs/AGENT-QUICKSTART.md`](docs/AGENT-QUICKSTART.md) 与
[`docs/MCP-SETUP.md`](docs/MCP-SETUP.md)。写入工具在落盘前完成结构校验，
覆盖既有套卷需显式 `replace=true`。写入后索引与发布清单自动重建。

## 提取边界

题面只来自 capture 中 `pages/p####.png` 的原生多模态观察。OCR、PDF 文本层、复制粘贴、
公式识别器和自动文本提取均禁止。答案、解析、勘误、答题卡、封面和广告不进入题库。

## 工程约束

- 所有路径使用仓库相对 `/`，禁止盘符、绝对路径和 `..`。
- `.npee-math-papers/sources`、`captures`、`logs` 与 `build/` 不提交；`papers`、`registry.json`、
  `release.json`、`index/` 提交。**来源 PDF 与页面图不上传 GitHub**（约 2 GB）：PDF 由
  `source.json` 的 `sha256` 锁定，页面图的可复现性缺口见 `docs/GIT-DATA.md`。
- 题库经 Git 版本管理后，**任何测试与探针脚本默认以沙盒副本运行**——写入真实题库前必须显式
  指定，避免验证脚本改动权威数据。
- 公式默认行内；分式按位置选大小——正文用 `\dfrac`，上下标、积分上下限与
  分式的分子/分母用 `\frac`（这些位置样式已降一级，`\dfrac` 会撑出行高）。
  通用类不放题面、出版物名称或第三方素材。
- 手工编辑使用 `apply_patch`；保留用户改动，不使用破坏性 Git 命令。
- 交付前运行：

```powershell
git diff --check
python -m npee_math_papers.maintenance.audit_store
.\npee_math_papers\maintenance\test-architecture.ps1
```

## 各层职责

| 层 | 目录 | 职责 | 约束 |
| --- | --- | --- | --- |
| 核心库 | `npee_math_papers/core/` | 存储、模型、校验、哈希、发布清单、组卷契约 | 除 `serialize`/`store` 外不依赖三方库 |
| 用例层 | `npee_math_papers/service/` | 题库、提取、捕获、组卷、TeX 编译 | 只读写 `.npee-math-papers`，不解析外部表格格式 |
| MCP 适配器 | `npee_math_papers/mcp/` | Agent 工具 | 只调用 `NpeeService` |
| HTTP 适配器 | `npee_math_papers/api/` | 人类前端的 JSON 接口 | 只调用 `NpeeService` |
| 前端 | `npee_math_papers/frontend/` | 人类网页管理台 | 只调用 HTTP 接口 |
| 排版类 | `npee_math_papers/tex/` | 通用 LaTeX 排版 | 不含来源相关内容 |
| 维护 | `npee_math_papers/maintenance/` | 迁移、审计、环境检查 | 不改题库正文以外的文件 |
