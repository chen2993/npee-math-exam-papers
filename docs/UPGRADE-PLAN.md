# 架构 / 数据结构 / 设计模式升级计划

> 记录一次系统性升级：在**不改变对外行为**（MCP/HTTP 契约、题库格式、发布哈希语义）
> 的前提下，消除重复、收紧边界、补齐工程设施。

## 0. 升级前诊断

### 优点（保留）

- **分层清晰**：`core` 从不 import `service`；`mcp`/`api` 只委托 `NpeeService`。
- **原子写**：每次落盘都是临时文件 + 改名。
- **派生索引**：`index/`、`release.json` 可重建，不是事实源。
- **内容哈希绑定**：组卷封印编写时的题目版本，编译前重算校验。
- **端口与适配器**：HTTP 与 MCP 可互换。

### 问题（本次修复）

| # | 问题 | 类别 |
| --- | --- | --- |
| P1 | **无任何测试**（pytest 已装，tests 目录不存在） | 工程设施 |
| P2 | **依赖注入缺失**：`tex_builder._store_for_build()` 从全局 `NPEE_DATA_ROOT`/默认根解析题库，而不是用调用它的 `NpeeService` 所绑定的 store。任何绑定到非默认数据根的用例（测试、多库、临时库）都会渲染**错误题库** | 架构 |
| P3 | `SUBJECTS` / `SUBJECT_LABELS` / `SECTIONS` / `ID_RE` 在 **7+ 模块**重复定义，容易漂移 | 数据结构 |
| P4 | TeX 正则（`BLOCK_MATH_RE`、`CJK_MATH_CHAR_RE`、`TIKZ_DOUBLE_COMMAND_RE`、`LITERAL_UNICODE_BACKSLASH_RE`、`TEXT_IN_MATH_COMMANDS`）在 `core/tex.py` 与 `service/tex_builder.py` **各存一份** | 数据结构 |
| P5 | `service/tex_builder.py` 是 **1420 行 God 模块**：CLI 解析、路径解析、校验、TeX 修复、渲染、水印、命名、编排混在一起 | 架构 |
| P6 | 错误只有字符串，适配器只能统一 400，无法区分"未找到 / 冲突 / 校验失败" | 设计 |
| P7 | 无 `pyproject.toml`，包不可安装、依赖未声明 | 打包 |

## 1. 升级顺序（每步都必须测试全绿）

1. **安全网**：建 `tests/`（core 模型、存储、用例、适配器、TeX 规则）+ `pyproject.toml`。
2. **P2 依赖注入**：`BuildOptions.store` + `load_catalogs(store=...)`，`CompositionService` 注入自己的 store。
3. **P3 术语常量单源**：新增 `core/domain.py` 作为 `SUBJECTS`/`SECTIONS`/`CHOICE_LABELS`/`ID_RE` 等的唯一定义，各模块改为 import。
4. **P4 TeX 常量单源**：`service/tex_builder.py` 改为复用 `core/tex.py` 的正则与命令集合。
5. **P5 拆分 God 模块**：把 `service/tex_builder.py` 按职责拆分，`tex_builder` 保留为兼容入口。
   计划中的命名是 `tex/repair.py`（历史写法修复）、`tex/layout.py`（版式/水印/命名）、
    `tex/package.py`（组卷包与片段解析）、`tex/builder.py`（编排）；实际落地为
    `service/rendering/` 下的多个模块（见下表 P5 行），两者职责一一对应，此处保留
    原计划命名仅作对照。
6. **P6 错误分类**：`core/errors.py` 增加 `NotFoundError` / `ConflictError`，适配器据此映射 404/409/400。

## 2. 兼容性约束

- MCP 工具名、返回 JSON 结构不变。
- HTTP 路径与响应结构不变（仅错误码更精确）。
- 题库 YAML 格式、`content_hash` 算法、`library_hash` 语义不变。
- `python -m npee_math_papers.service.tex_builder --composition ...` 仍可用。
- `test-architecture.ps1` 的文件清单必须继续满足（新增文件需同步）。

## 3. 完成情况

| 项 | 状态 | 证据 |
| --- | --- | --- |
| P1 测试与打包 | ✅ | `pytest` 121 项通过；新增 `pyproject.toml`、`tests/` |
| P2 依赖注入 | ✅ | `BuildOptions.store` + `CompositionService` 注入；临时数据根可正确编译 |
| P3 术语常量单源 | ✅ | 新增 `core/domain.py`；`store/sources/registry/questions/question/composition/tex_builder/composition(service)` 均改为导入 |
| P4 TeX 常量单源 | ✅ | `core/tex.py` 拥有正则与命令集合；`rendering/inline_tex.py` 复用 |
| P5 拆分 God 模块 | ✅ | `tex_builder.py` 1570 → 360 行；新增 `service/rendering/` 7 个模块 |
| P6 错误分类 | ✅ | `NotFoundError`/`ConflictError` + `http_status_for`；HTTP 映射 404/409/400 |
| P7 打包元数据 | ✅ | `pyproject.toml`（依赖、可选依赖、console script、pytest 配置） |

### 行为保持不变

- `tests/golden/rendering.json` 黄金快照在重构前后**逐字节一致**。
- `python build\full-build-scan.py` → `papers=321 build_ok=321 build_fail=0`。
- `python -m npee_math_papers.maintenance.audit_store` → `PASS`。
- `.\npee_math_papers\maintenance\test-architecture.ps1` → 通过（已登记新文件）。
- `python -m npee_math_papers.maintenance.verify_compile --matrix --collections` → 全部通过。
