"""NPEE: 考研数学题库工程。

顶层包，按职责分层：

- ``npee_math_papers.core``         规则与存储：模型、校验、哈希、发布清单
- ``npee_math_papers.service``      用例层：题库、提取、组卷、TeX 渲染
- ``npee_math_papers.mcp``          面向 Agent 的 MCP 适配器
- ``npee_math_papers.api``          面向人类前端的 HTTP 适配器
- ``npee_math_papers.frontend``     人类前端（React 管理台）
- ``npee_math_papers.launcher``     本地启动器（一条命令拉起后端与前端）
- ``npee_math_papers.maintenance``  迁移、审计与环境检查

所有表面都调用同一 ``npee_math_papers.service``，因此行为不会分叉。
"""

from __future__ import annotations

__version__ = "3.0.0"

__all__ = ["__version__"]
