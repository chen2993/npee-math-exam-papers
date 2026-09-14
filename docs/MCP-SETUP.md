# MCP 安装与部署

把 `npee-math-papers` 接入支持 MCP 的 Agent（OpenCode、Claude Desktop 等）。

## 一、前置条件

```powershell
cd <仓库根目录>
python -m pip install -r npee_math_papers/api/requirements.txt
```

这会安装 `mcp`（MCP SDK）、`ruamel.yaml`（题库 YAML）、`fastapi`、`uvicorn`。

验证：

```powershell
python -c "from npee_math_papers.mcp.server import build_server; print(len(build_server()._tool_manager._tools))"
```

应输出 `28`。

## 二、传输方式

| 方式 | 用途 | 启动 |
| --- | --- | --- |
| stdio | 本地 Agent，按需拉起 | `python -m npee_math_papers.mcp.server` |
| HTTP | 常驻服务，多个客户端 | `python -m npee_math_papers.mcp.server --http --port 8780` |

本地 Agent 推荐 **stdio**：随会话启动、无端口占用、退出即释放。

## 三、OpenCode 配置

编辑 `~/.config/opencode/opencode.json`（Windows 为
`C:\Users\<你>\.config\opencode\opencode.json`），在 `mcp` 下加入：

```json
{
  "mcp": {
    "npee-math-papers": {
      "enabled": true,
      "type": "local",
      "command": ["python", "-m", "npee_math_papers.mcp.server"],
      "environment": {
        "NPEE_DATA_ROOT": "C:/Users/<你>/Desktop/jjb/.npee-math-papers"
      }
    }
  }
}
```

要点：

- `type` 用 `local`（stdio 子进程）。
- `command` 必须能在**仓库根目录**下执行，因为数据根默认按包位置解析。
  若 OpenCode 不在仓库根启动，用绝对路径：
  `["python", "-m", "npee_math_papers.mcp.server"]` 并把工作目录设为仓库根，
  或用 `NPEE_DATA_ROOT` 显式指定数据根（上例已指定）。
- `NPEE_DATA_ROOT` 指向仓库里的 `.npee-math-papers/`。省略时按包位置推导。

改完重启 OpenCode，在工具列表里应看到 28 个 `npee_*` 工具。

## 四、HTTP 方式配置

先常驻启动：

```powershell
python -m npee_math_papers.mcp.server --http --port 8780
```

再在 `opencode.json` 里：

```json
{
  "mcp": {
    "npee-math-papers": {
      "enabled": true,
      "type": "remote",
      "url": "http://127.0.0.1:8780/mcp"
    }
  }
}
```

## 五、Windows 上找不到 python

`python` 不在 PATH 时，用解释器绝对路径：

```json
"command": ["C:/Python312/python.exe", "-m", "npee_math_papers.mcp.server"]
```

## 六、验证接入成功

让 Agent 调用一次 `npee_library_stats`。应返回：

```json
{ "papers": 321, "bundles": 60, "questions": 7062 }
```

若失败，按顺序排查：

1. `python -m npee_math_papers.mcp.server` 能手动启动吗；
2. `NPEE_DATA_ROOT` 是否指向正确的 `.npee-math-papers/`；
3. 依赖是否装全（`mcp`、`ruamel.yaml`）。

## 七、工具清单

```text
题库浏览
  npee_library_stats          统计
  npee_list_series            系列列表
  npee_list_bundles           套卷分组
  npee_list_papers            分页套卷摘要
  npee_get_paper              单套题面
  npee_get_question           单题
  npee_search_questions       检索

图形
  npee_render_figure          TikZ 渲染为 SVG

来源与捕获
  npee_capture_available      渲染环境自检
  npee_capture_pdf            PDF 渲染为 capture
  npee_register_source        登记来源 PDF
  npee_get_source             读取来源记录
  npee_list_sources           来源列表
  npee_prepare_capture        手工创建 capture
  npee_add_capture_page       逐页添加
  npee_list_captures          捕获列表
  npee_set_capture_status     更新捕获状态

写入
  npee_ingest_paper           写入一套卷
  npee_ingest_document        写入完整文档
  npee_validate_questions     落盘前校验

组卷
  npee_build_composition      生成组卷（封印版本）
  npee_validate_composition   校验组卷与版本绑定
  npee_composition_compile    编译 PDF（同步）
  npee_composition_submit     提交后台编译任务
  npee_composition_job        查询编译任务状态
  npee_composition_jobs       列出最近编译任务

维护
  npee_rebuild_index          重建索引与发布清单
  npee_release_manifest       发布清单与内容哈希
```

## 八、注意

- 长编译用 `npee_composition_submit` + `npee_composition_job` 轮询，避免单次调用超时；
  短编译或试编译用同步的 `npee_composition_compile` 即可。
- `dry_run=true` 只生成 TeX 与报告，不调用 XeLaTeX，适合先验证契约。
- 写入工具的 `replace` 默认 `false`，覆盖既有套卷需显式开启。
- 所有工具调用（含失败）都会写入共享事件日志，可在前端「操作日志」页查看。
