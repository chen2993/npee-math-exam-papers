"""NPEE MCP 服务：``npee_math_papers.service`` 的薄适配器。

这里的每个 tool 都是对 ``NpeeService`` 的一到几行委托。所有规则、校验和文件访问都在
用例层，因此 MCP 表面只是翻译层，不会与 HTTP API 分叉。

工程约定
--------
- 所有写入工具在落盘前完成结构校验（``npee_math_papers.core`` 的模型校验）。
- 组卷编译可能耗时数十秒：:func:`npee_composition_compile` 支持 ``dry_run`` 先做
  快速契约检查，返回产物路径，由调用方决定是否真正编译或轮询。
- 题目图形由 :func:`npee_render_figure` 渲染为 SVG 并缓存。

启动::

    python -m npee_math_papers.mcp.server            # stdio 传输（默认）
    python -m npee_math_papers.mcp.server --http     # streamable HTTP 传输
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
import time
from typing import Any

from npee_math_papers.core.domain import DEFAULT_SPACING
from npee_math_papers.service import NpeeService
from npee_math_papers.service.events import build_payload, default_event_log

try:  # pragma: no cover - exercised through the CLI
    from mcp.server.fastmcp import FastMCP

    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    MCP_AVAILABLE = False


def _service() -> NpeeService:
    return NpeeService.create()


def _as_json(value: Any) -> str:
    """Serialize a service result for an MCP text content block."""

    return json.dumps(value, ensure_ascii=False, indent=2)


def _decode_tool_result(result: Any) -> tuple[Any, int]:
    """把工具返回值还原成可记录的结构。

    工具以 JSON 文本返回（MCP 的 content block），因此这里尝试解析回对象，
    让日志页可以折叠查看；解析失败则按纯文本记录。大小始终按原始文本计算，
    与 ``build_payload`` 的裁剪相互独立。
    """

    if isinstance(result, str):
        size = len(result.encode("utf-8"))
        try:
            return json.loads(result), size
        except json.JSONDecodeError:
            return result, size
    if result is None:
        return None, 0
    try:
        return result, len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        return str(result), 0


def _result_flags(value: Any) -> dict[str, Any]:
    """从解析后的返回值里推断「业务失败」，用于状态判定与筛选。"""

    flags: dict[str, Any] = {}
    if isinstance(value, dict):
        if value.get("ok") is False:
            flags["result_error"] = True
        if value.get("status") == "error":
            flags["result_error"] = True
        for key in ("error", "message"):
            if isinstance(value.get(key), str) and value.get("ok") is False:
                flags["error"] = value[key][:300]
    elif isinstance(value, list):
        # 批量工具常返回 [{ok: false, ...}]，整体不算失败但值得标出来。
        failures = sum(1 for item in value if isinstance(item, dict) and item.get("ok") is False)
        if failures:
            flags["failed_items"] = failures
    return flags


def _instrument_tools(server: "FastMCP") -> None:
    """让每个注册的工具自动写入共享事件日志。

    只在这里包一次 ``server.tool``，因此每个工具都获得调用记录，且工具函数本身
    保持干净。日志写入失败绝不影响工具执行。

    记录的是**完整入参与返回值**（经 ``build_payload`` 结构化裁剪），而不只是
    摘要：排查 Agent 行为时，「它到底传了什么、拿到了什么」是最常被问的问题，
    而原先只存 ``[3 项]`` 这样的占位符，答案并不在日志里。
    """

    event_log = default_event_log()
    original_tool = server.tool

    def tool(*args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        described_name = kwargs.get("name")
        decorator = original_tool(*args, **kwargs)

        def wrap(func):  # type: ignore[no-untyped-def]
            tool_name = described_name or func.__name__

            @functools.wraps(func)
            def logged(*call_args: Any, **call_kwargs: Any) -> Any:
                started = time.perf_counter()
                try:
                    result = func(*call_args, **call_kwargs)
                except Exception as error:
                    event_log.record(
                        surface="mcp",
                        kind="tool",
                        name=tool_name,
                        status="error",
                        duration_ms=(time.perf_counter() - started) * 1000,
                        detail={"error": str(error)[:300], "exception": type(error).__name__},
                        request=build_payload(call_kwargs),
                    )
                    raise
                elapsed = (time.perf_counter() - started) * 1000
                decoded, result_bytes = _decode_tool_result(result)
                detail: dict[str, Any] = _result_flags(decoded)
                event_log.record(
                    surface="mcp",
                    kind="tool",
                    name=tool_name,
                    status="error" if detail.get("result_error") else "ok",
                    duration_ms=elapsed,
                    detail=detail,
                    request=build_payload(call_kwargs),
                    response=build_payload(decoded, raw_bytes=result_bytes),
                )
                return result

            return decorator(logged)

        return wrap

    server.tool = tool  # type: ignore[assignment]


def build_server() -> "FastMCP":
    """Construct the MCP server with every NPEE tool registered."""

    if not MCP_AVAILABLE:
        raise RuntimeError('the "mcp" package is required to run the NPEE MCP server')

    server = FastMCP(
        "npee-math-papers",
        instructions=(
            "NPEE 题库服务。用于浏览与检索考研数学题库、管理来源与页面捕获、"
            "写入题目、以及按套卷组卷与编译。所有写入工具在落盘前完成结构校验。"
        ),
    )
    _instrument_tools(server)

    # --- library -----------------------------------------------------------

    @server.tool(description="题库总体统计：套卷数、题目数、图形数、系列与年份分布。")
    def npee_library_stats() -> str:
        return _as_json(_service().library.stats())

    @server.tool(description="列出全部系列，含每系列的套卷数与题目数。")
    def npee_list_series() -> str:
        return _as_json(_service().library.list_series())

    @server.tool(description="列出套卷分组。可按系列、年份、科目过滤（与 npee_list_papers 的参数一致）。")
    def npee_list_bundles(series_key: str = "", year: int = 0, subject: str = "") -> str:
        # Filtering is the service's job; the adapter only translates arguments.
        return _as_json(
            _service().library.list_bundles(
                series_keys=[series_key] if series_key else None,
                years=[year] if year else None,
                subjects=[subject] if subject else None,
            )
        )

    @server.tool(
        description=(
            "分页列出套卷摘要（不含题目正文）。可按系列、年份、科目、套号过滤，"
            "也可用 q 在系列名/系列键/年份/科目/套号中做子串搜索，"
            "并用 order 指定排序（series / year-desc / year-asc / questions-desc / questions-asc）。"
        )
    )
    def npee_list_papers(
        series_key: str = "",
        year: int = 0,
        subject: str = "",
        paper_no: int = 0,
        q: str = "",
        order: str = "series",
        offset: int = 0,
        limit: int = 50,
    ) -> str:
        service = _service()
        return _as_json(
            service.library.list_papers(
                series_keys=[series_key] if series_key else None,
                years=[year] if year else None,
                subjects=[subject] if subject else None,
                paper_nos=[paper_no] if paper_no else None,
                query=q,
                order=order,
                offset=offset,
                limit=limit if limit > 0 else None,
            )
        )

    @server.tool(description="读取单套试卷的完整题目。with_questions=false 时只返回摘要。")
    def npee_get_paper(
        series_key: str,
        year: int,
        subject: str,
        paper_no: int,
        with_questions: bool = True,
    ) -> str:
        return _as_json(_service().library.get_paper(series_key, year, subject, paper_no, with_questions=with_questions))

    @server.tool(description="读取单道题及其所属试卷上下文。")
    def npee_get_question(series_key: str, year: int, subject: str, paper_no: int, question_no: int) -> str:
        return _as_json(_service().library.get_question(series_key, year, subject, paper_no, question_no))

    @server.tool(description="把指定题目中的 TikZ 图形渲染为 SVG，返回缓存键（供人类前端或可视化工具取用）。")
    def npee_render_figure(
        series_key: str,
        year: int,
        subject: str,
        paper_no: int,
        question_no: int,
        figure_index: int = 0,
    ) -> str:
        import hashlib

        from npee_math_papers.core.figure_render import FigureRenderer

        service = _service()
        paper = service.library.get_paper(series_key, year, subject, paper_no)
        question = next((item for item in paper["questions"] if int(item["number"]) == question_no), None)
        if question is None:
            return _as_json({"ok": False, "error": f"question {question_no} not found"})
        figures: list[dict[str, Any]] = list((question.get("stem") or {}).get("figures") or [])
        for choice in question.get("choices") or []:
            figures.extend(choice.get("figures") or [])
        for subpart in question.get("subparts") or []:
            figures.extend(subpart.get("figures") or [])
        if figure_index < 0 or figure_index >= len(figures):
            return _as_json({"ok": False, "error": f"figure {figure_index} not found"})
        figure = figures[figure_index]
        if figure.get("kind") != "tikz":
            return _as_json({"ok": False, "error": "only TikZ figures can be rendered"})
        renderer = FigureRenderer(service.repository_root, service.repository_root / "build" / "figure-cache")
        available, reason = renderer.available()
        if not available:
            return _as_json({"ok": False, "error": reason})
        latex = figure.get("latex") or ""
        digest = hashlib.sha256(latex.encode("utf-8")).hexdigest()
        result = renderer.render(latex)
        return _as_json({
            "ok": True,
            "digest": result.digest,
            "cached": result.cached,
            "svg_bytes": len(result.svg),
            "cache_path": f"build/figure-cache/{digest}.svg",
        })

    @server.tool(description="在题干、选项与子问中检索子串，返回命中题目摘要。")
    def npee_search_questions(query: str, series_key: str = "", subject: str = "", limit: int = 50) -> str:
        service = _service()
        return _as_json(
            service.library.search(
                query,
                series_keys=[series_key] if series_key else None,
                subjects=[subject] if subject else None,
                limit=limit if limit > 0 else 50,
            )
        )

    # --- sources and captures ---------------------------------------------

    @server.tool(description="登记某个系列的来源 PDF。pdf_path 必须是服务器可访问的仓库内路径。")
    def npee_register_source(
        series_key: str,
        year: int,
        subject: str,
        pdf_path: str,
        source_id: str = "",
        notes: str = "",
        move: bool = False,
    ) -> str:
        return _as_json(
            _service().extraction.register_source(
                series_key,
                year,
                subject,
                pdf_path,
                source_id=source_id or None,
                notes=notes or None,
                move=move,
            )
        )

    @server.tool(description="读取某系列的来源 PDF 记录（含 SHA-256 与页数）。")
    def npee_get_source(series_key: str, year: int, subject: str) -> str:
        return _as_json(_service().extraction.get_source(series_key, year, subject))

    @server.tool(description="列出全部已登记的来源 PDF。")
    def npee_list_sources() -> str:
        return _as_json(_service().extraction.list_sources())

    @server.tool(description="按 PDF 页码范围自动渲染页面捕获：从来源 PDF 生成题面页 PNG，登记来源与捕获，答案/排除页永不渲染。")
    def npee_capture_pdf(
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        pdf_path: str,
        page_from: int = 1,
        page_to: int = 0,
        answer_pages: list[int] | None = None,
        exclude_pages: list[int] | None = None,
        dpi: int = 220,
        source_id: str = "",
        notes: str = "",
    ) -> str:
        return _as_json(
            _service().capture.capture_pdf(
                series_key,
                year,
                subject,
                capture_id,
                pdf_path,
                page_from=page_from,
                page_to=page_to or None,
                answer_pages=answer_pages or [],
                exclude_pages=exclude_pages or [],
                dpi=dpi,
                source_id=source_id or None,
                register_source=True,
                notes=notes or None,
            ).to_dict()
        )

    @server.tool(description="检查 PDF 渲染环境（pdfinfo / pdftoppm）是否可用。")
    def npee_capture_available() -> str:
        available, reason = _service().capture.available()
        return _as_json({"available": available, "reason": reason})

    @server.tool(description="为某系列创建一次页面捕获，必须显式给出 question_pages，各页集合不得重叠。")
    def npee_prepare_capture(
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        question_pages: list[int],
        answer_pages: list[int] | None = None,
        exclude_pages: list[int] | None = None,
        source_id: str = "",
        notes: str = "",
    ) -> str:
        return _as_json(
            _service().extraction.prepare_capture(
                series_key,
                year,
                subject,
                capture_id,
                question_pages=question_pages,
                answer_pages=answer_pages or [],
                exclude_pages=exclude_pages or [],
                source_id=source_id or None,
                notes=notes or None,
            )
        )

    @server.tool(description="把一张渲染好的页面 PNG 加入捕获。页码必须属于该捕获声明的 question_pages。")
    def npee_add_capture_page(
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        page_number: int,
        png_path: str,
    ) -> str:
        return _as_json(
            _service().extraction.add_page(series_key, year, subject, capture_id, page_number, png_path)
        )

    @server.tool(description="列出页面捕获。可按 series / year / subject 过滤。")
    def npee_list_captures(series_key: str = "", year: int = 0, subject: str = "") -> str:
        return _as_json(
            _service().extraction.list_captures(
                series_key=series_key or None,
                year=year or None,
                subject=subject or None,
            )
        )

    @server.tool(description="更新捕获的生命周期状态，例如 prepared / returned / reviewed。")
    def npee_set_capture_status(
        series_key: str,
        year: int,
        subject: str,
        capture_id: str,
        status: str,
    ) -> str:
        return _as_json(_service().extraction.set_capture_status(series_key, year, subject, capture_id, status))

    # --- ingestion ---------------------------------------------------------

    @server.tool(description="写入一套试卷的题目。questions 为题目数组（支持 schema 3.0 或旧 2.0，自动转换）。落盘前完成结构校验。replace=true 才允许覆盖既有套卷。")
    def npee_ingest_paper(
        series_key: str,
        year: int,
        subject: str,
        paper_no: int,
        questions: list[dict[str, Any]],
        replace: bool = False,
        series_name: str = "",
        capture_id: str = "",
    ) -> str:
        return _as_json(
            _service().extraction.ingest(
                series_key,
                year,
                subject,
                paper_no,
                questions,
                replace=replace,
                series_name=series_name or None,
                capture_id=capture_id or None,
            )
        )

    @server.tool(
        description=(
            "写入一份完整 paper 文档。document 的形状与 npee_get_paper 的返回一致："
            "去掉 meta 块即可直接回写，即 {schema_version?, paper:{series_key,year,subject,paper_no}, "
            "questions:[...]}。未知字段与只读派生字段（natural_key/question_count 等）会被拒绝；"
            "兼容旧 schema 2.0 题目。"
        )
    )
    def npee_ingest_document(document: dict[str, Any], replace: bool = False, series_name: str = "") -> str:
        # `document` is exactly what `npee_get_paper` returns with its `meta`
        # block removed, so a read result can be edited and written straight back.
        return _as_json(
            _service().extraction.ingest_document(
                document,
                replace=replace,
                series_name=series_name or None,
            )
        )

    @server.tool(description="校验一套题面数据是否可以写入，但不落盘。用于提取后自检。")
    def npee_validate_questions(questions: list[dict[str, Any]]) -> str:
        from npee_math_papers.core.question import convert_v2_question, has_schema_v3, validate_questions

        converted = []
        for question in questions:
            raw = dict(question)
            converted.append(raw if has_schema_v3(raw) else convert_v2_question(raw))
        try:
            validated = validate_questions(converted, "questions")
        except Exception as error:  # surfaced as a structured failure
            return _as_json({"ok": False, "error": str(error)})
        return _as_json({"ok": True, "question_count": len(validated)})

    # --- composition -------------------------------------------------------

    @server.tool(description="按套卷列表生成组卷文档。selections 每项为 {series_key, year, subject, paper_no}，默认封印每套的 content_hash。")
    def npee_build_composition(
        composition_id: str,
        title: str,
        selections: list[dict[str, Any]],
        layout: str = "a4",
        spacing: str = DEFAULT_SPACING,
        theme: str = "print",
        pin_hashes: bool = True,
    ) -> str:
        document = {
            "toc": {"enabled": True, "title": "目录", "include_groups": True, "include_papers": True},
            "layout": layout,
            "theme": theme,
            "spacing": spacing,
            "opening": {"show": True, "candidate_info": True, "notices": True},
            "solution": {"structure": "pair-first", "pair_count": 2},
        }
        return _as_json(
            _service().composition.build(
                composition_id,
                title,
                selections,
                document=document,
                pin_hashes=pin_hashes,
            )
        )

    @server.tool(description="校验组卷文档：结构是否合法，以及每个引用是否与当前题库内容一致。")
    def npee_validate_composition(composition: dict[str, Any]) -> str:
        return _as_json(_service().composition.validate(composition))

    @server.tool(description="编译组卷（同步）。编译耗时较长时改用 npee_composition_submit + npee_composition_job 轮询。dry_run=true 只生成 TeX 与报告。")
    def npee_composition_compile(
        composition: dict[str, Any],
        dry_run: bool = False,
        layouts: str = "",
        spacing: str = "",
    ) -> str:
        return _as_json(
            _service().composition.compile(
                composition,
                dry_run=dry_run,
                layouts=layouts or None,
                spacing=spacing or None,
            ).to_dict()
        )

    @server.tool(description="提交后台编译任务，立即返回 job_id。随后用 npee_composition_job 轮询状态，避免长编译阻塞。")
    def npee_composition_submit(
        composition: dict[str, Any],
        dry_run: bool = False,
        layouts: str = "",
        spacing: str = "",
    ) -> str:
        job = _service().composition.submit_compile(
            composition,
            dry_run=dry_run,
            layouts=layouts or None,
            spacing=spacing or None,
        )
        return _as_json(job.to_dict())

    @server.tool(description="查询编译任务状态：queued / running / succeeded / failed，含产物路径与错误。")
    def npee_composition_job(job_id: str) -> str:
        job = _service().composition.get_job(job_id)
        if job is None:
            return _as_json({"ok": False, "error": f"任务不存在：{job_id}"})
        return _as_json(job.to_dict())

    @server.tool(description="列出最近的编译任务。")
    def npee_composition_jobs(limit: int = 20) -> str:
        return _as_json(_service().composition.list_jobs(limit))

    # --- maintenance -------------------------------------------------------

    @server.tool(description="重建派生索引（papers.json / bundles.json）与发布清单，并返回最新发布哈希。")
    def npee_rebuild_index() -> str:
        service = _service()
        index = service.context.store.rebuild_index()
        release = service.context.store.write_release()
        return _as_json({"index": index, "release": {"paper_count": release["paper_count"], "library_hash": release["library_hash"]}})

    @server.tool(description="返回发布清单：每套卷的 content_hash 与库级哈希，用于版本绑定。")
    def npee_release_manifest() -> str:
        return _as_json(_service().context.store.build_release())

    # --- TeX 调试 ----------------------------------------------------------

    @server.tool(description="静态检查一段 TeX 文本（丢反斜杠、块级数学、\\frac、未闭合数学模式等），返回问题列表。")
    def npee_check_tex(text: str) -> str:
        return _as_json(_service().tex.check_text(text))

    @server.tool(description="扫描一段文本的对齐环境（矩阵/分段/数组）内的反斜杠串异常，返回结构化问题。")
    def npee_scan_alignments(text: str) -> str:
        return _as_json(_service().tex.scan_alignments(text))

    @server.tool(description="全库静态扫描对齐环境内的反斜杠串异常（纯文本、秒级），返回受影响套卷与逐字段问题。")
    def npee_audit_tex(series_key: str = "", limit: int = 100) -> str:
        return _as_json(
            _service().tex.audit_library(
                series_keys=[series_key] if series_key else None,
                limit=limit,
            )
        )

    @server.tool(description="用真实排版类渲染一段 TeX 片段，返回 PDF/PNG 路径与提取的文本层，供肉眼或程序核对。")
    def npee_render_tex(text: str, label: str = "field") -> str:
        return _as_json(_service().tex.render_text(text, label=label or "field"))

    @server.tool(description="渲染并诊断一段题面字段：检测命令名泄漏成字面字母、数学模式泄漏、残留待核标记等。")
    def npee_diagnose_field(text: str, label: str = "field") -> str:
        return _as_json(_service().tex.diagnose_field(text, label=label or "field"))

    @server.tool(description="逐字段渲染诊断一套试卷，返回有问题的字段及其证据。")
    def npee_diagnose_paper(series_key: str, year: int, subject: str, paper_no: int) -> str:
        return _as_json(_service().tex.diagnose_paper(series_key, year, subject, paper_no))

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NPEE MCP server")
    parser.add_argument("--http", action="store_true", help="use the streamable HTTP transport instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args(argv)
    server = build_server()
    if args.http:
        import os

        os.environ.setdefault("FASTMCP_HOST", args.host)
        os.environ.setdefault("FASTMCP_PORT", str(args.port))
        server.run("streamable-http")
    else:
        server.run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
