# NPEE 数学试卷工程

一套「MCP 服务 + 题库数据库」：Agent 通过 MCP 读写题库，人类通过网页管理台查看与组卷，
两者共用同一份题库与同一套用例代码。

## 快速开始

**人类**：

```powershell
.\start-npee.ps1
```

浏览器打开提示的地址，即可浏览题库、查看题目与图形、组织试卷并导出 PDF。

**Agent**：把 `npee-math-papers` 接入 MCP 客户端，配置见
[`docs/MCP-SETUP.md`](docs/MCP-SETUP.md)。

## 文档

完整索引见 [`docs/README.md`](docs/README.md)。

| 你是 | 先读 |
| --- | --- |
| Agent | [`docs/AGENT-QUICKSTART.md`](docs/AGENT-QUICKSTART.md) |
| 人类 | [`docs/HUMAN-GUIDE.md`](docs/HUMAN-GUIDE.md) |
| 开发者 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |

## 数据链路

```text
来源 PDF ─► .npee-math-papers/sources    来源登记
页面 PNG ─► .npee-math-papers/captures   页面捕获
题面     ─► .npee-math-papers/papers     题库正文（一套一 YAML）
                    │
                    ├─ npee.service      用例层（唯一实现）
                    │      ├─ npee.mcp       Agent 的 MCP 工具
                    │      ├─ npee.api       人类前端的 HTTP 接口
                    │      └─ npee.launcher  本地启动器
                    │
                    └─ npee.frontend     人类网页管理台
```

## 题库存储

一套试卷一个可读的 YAML 文件：

```text
.npee-math-papers/papers/zhangyu8-2024-math1/7.yaml
```

选用 YAML 字面量块是因为题面充满 LaTeX，反斜杠可原样保存，无需转义：

```yaml
stem:
  text: |-
    设 $\dfrac{a}{b}$，则 $\begin{cases}x\\y\end{cases}$
```

## 目录

```text
npee_math_papers/          Python 包
├─ core/                   规则与存储：模型、校验、哈希、发布清单
├─ service/                用例层：题库、提取、捕获、组卷、TeX 编译
├─ mcp/                    Agent 的 MCP 工具（28 个）
├─ api/                    人类前端的 HTTP 接口
├─ launcher/               本地启动器
├─ frontend/               人类网页管理台（React + Vite）
├─ tex/                    LaTeX 排版类
└─ maintenance/            迁移、审计、环境检查
composition/               组卷配置（只引用自然键）
dist/                      编译产物（PDF，不入库）
docs/                      文档
.npee-math-papers/         题库数据库
```

## 常用命令

```powershell
# 人类
.\start-npee.ps1

# Agent
python -m npee_math_papers.mcp.server                     启动 MCP（stdio）
python -m npee_math_papers.mcp.server --http --port 8780  启动 MCP（HTTP）

# 维护
python -m npee_math_papers.maintenance.audit_store          题库一致性审计
python -m npee_math_papers.maintenance.audit_store --rebuild 重建索引与发布清单
python -m npee_math_papers.maintenance.check_math_cjk       扫描数学模式中的中文
python -m npee_math_papers.maintenance.check_environment    环境检查
```

LaTeX 类接口见 [`npee_math_papers/tex/CLASS-API.md`](npee_math_papers/tex/CLASS-API.md)，
类代码许可证见 [`npee_math_papers/tex/LICENSE-CLASS.md`](npee_math_papers/tex/LICENSE-CLASS.md)。
