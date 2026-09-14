# 文档索引

本项目是一套「MCP 服务 + 题库数据库」：Agent 通过 MCP 读写题库，人类通过网页管理台
查看与组卷，两者共用同一份题库与同一套用例代码。

## 按角色阅读

| 你是 | 先读 | 然后 |
| --- | --- | --- |
| Agent（要调 MCP） | [`AGENT-QUICKSTART.md`](AGENT-QUICKSTART.md) | [`MCP-SETUP.md`](MCP-SETUP.md) |
| 人类（要用网页） | [`HUMAN-GUIDE.md`](HUMAN-GUIDE.md) | — |
| 开发者（要改代码） | [`ARCHITECTURE.md`](ARCHITECTURE.md) | [`APPLICATION.md`](APPLICATION.md) |

## 三分钟了解

### 它是什么

考研数学题库工程：从 PDF 提取题面，存成可读的题库，再按套卷组卷输出 PDF。

### 数据在哪

`.npee-math-papers/`，一套试卷一个 YAML 文件。格式见
[`HUMAN-GUIDE.md`](HUMAN-GUIDE.md) 第三节。

### 谁用什么入口

```text
题库数据库 (.npee-math-papers/)
        │
        ├─ npee.service        用例层（唯一实现）
        │       ├─ npee.mcp        Agent 的 MCP 工具
        │       ├─ npee.api        人类前端用的 HTTP 接口
        │       └─ npee.launcher   本地启动器
        │
        └─ npee.frontend       人类网页管理台
```

### 一条命令开始

```powershell
.\start-npee.ps1        # 人类：启动网页管理台
```

Agent 装 MCP：见 [`MCP-SETUP.md`](MCP-SETUP.md)。

## 文档清单

| 文件 | 内容 |
| --- | --- |
| [`AGENT-QUICKSTART.md`](AGENT-QUICKSTART.md) | Agent 上手指南：术语、任务地图、工作流、题目结构、报错处理 |
| [`MCP-SETUP.md`](MCP-SETUP.md) | MCP 安装、OpenCode 配置、工具清单、排查 |
| [`HUMAN-GUIDE.md`](HUMAN-GUIDE.md) | 人类使用指南：启动、四种界面、存储格式、常见问题 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 分层架构、目录职责、数据流 |
| [`APPLICATION.md`](APPLICATION.md) | 应用 API 端点与前端结构 |
| [`UPGRADE-PLAN.md`](UPGRADE-PLAN.md) | 架构 / 数据结构 / 设计模式升级记录 |
| [`FRONTEND-RESEARCH.md`](FRONTEND-RESEARCH.md) | 前端升级：参考系统研究与设计决策 |
| [`GIT-DATA.md`](GIT-DATA.md) | 题库的 Git 版本管理：三层资源与 2 GB PDF/PNG 的处理 |

## 常用命令

```powershell
# 人类
.\start-npee.ps1                                    启动管理台

# Agent 与维护
python -m npee_math_papers.mcp.server                启动 MCP（stdio）
python -m npee_math_papers.maintenance.audit_store    题库审计
python -m npee_math_papers.maintenance.check_environment  环境检查
```

## 目录速览

```text
npee_math_papers/          Python 包
├─ core/                   规则与存储（模型、校验、哈希、发布清单）
├─ service/                用例层（题库、提取、捕获、组卷、TeX 编译）
├─ mcp/                    Agent 的 MCP 工具
├─ api/                    人类前端的 HTTP 接口
├─ launcher/               本地启动器
├─ frontend/               人类网页管理台（React）
├─ tex/                    LaTeX 排版类
└─ maintenance/            迁移、审计、环境检查
collections/               组卷配置
docs/                      文档（本目录）
.npee-math-papers/         题库数据库
start-npee.ps1 / .bat      启动脚本
```
