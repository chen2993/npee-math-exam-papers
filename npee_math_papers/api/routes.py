"""NPEE application API: a thin HTTP adapter over :mod:`npee_math_papers.service`.

Every route delegates to ``NpeeService``. There is no separate catalog data service
and no file access here, so the HTTP API and the MCP server are two translations of
the same use cases and cannot diverge.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from starlette.responses import Response

from npee_math_papers.api.dependencies import get_event_log, get_figure_renderer, get_service
from npee_math_papers.core.domain import DEFAULT_PAPER_ORDER
from npee_math_papers.core.errors import NpeeError, http_status_for
from npee_math_papers.core.figure_render import FigureRenderer
from npee_math_papers.service import NpeeService
from npee_math_papers.service.events import EventLog


router = APIRouter(tags=["NPEE"])


def _to_http_error(error: Exception) -> HTTPException:
    """Translate a shared-core error into the HTTP status it describes."""

    return HTTPException(status_code=http_status_for(error), detail=str(error))


@router.get("/health")
async def health(service: NpeeService = Depends(get_service)) -> dict[str, Any]:
    stats = await run_in_threadpool(service.library.stats)
    return {
        "status": "ok",
        "provider": "npee-store",
        "provider_state": "ready" if stats.get("papers") else "empty",
        "read_only": False,
        "data_boundary": "npee-store",
        "stats": stats,
    }


@router.get("/overview")
async def overview(service: NpeeService = Depends(get_service)) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.library.overview)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/series")
async def series(service: NpeeService = Depends(get_service)) -> dict[str, Any]:
    try:
        return {"series": await run_in_threadpool(service.library.list_series)}
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/bundles")
async def bundles(
    series_key: list[str] | None = Query(default=None),
    year: list[int] | None = Query(default=None),
    subject: list[str] | None = Query(default=None),
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return {
            "bundles": await run_in_threadpool(
                service.library.list_bundles,
                series_keys=series_key,
                years=year,
                subjects=subject,
            )
        }
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/papers")
async def papers(
    series_key: list[str] | None = Query(default=None),
    year: list[int] | None = Query(default=None),
    subject: list[str] | None = Query(default=None),
    paper_no: list[int] | None = Query(default=None),
    q: str = "",
    order: str = DEFAULT_PAPER_ORDER,
    offset: int = 0,
    limit: int | None = None,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            service.library.list_papers,
            series_keys=series_key,
            years=year,
            subjects=subject,
            paper_nos=paper_no,
            query=q,
            order=order,
            offset=offset,
            limit=limit,
        )
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/papers/{series_key}/{year}/{subject}/{paper_no}")
async def paper(
    series_key: str,
    year: int,
    subject: str,
    paper_no: int,
    with_questions: bool = True,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.library.get_paper, series_key, year, subject, paper_no, with_questions=with_questions)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/papers/{series_key}/{year}/{subject}/{paper_no}/questions/{question_no}")
async def question(
    series_key: str,
    year: int,
    subject: str,
    paper_no: int,
    question_no: int,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.library.get_question, series_key, year, subject, paper_no, question_no)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/search")
async def search(
    q: str,
    series_key: list[str] | None = Query(default=None),
    subject: list[str] | None = Query(default=None),
    limit: int = 50,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.library.search, q, series_keys=series_key, subjects=subject, limit=limit)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/release")
async def release(service: NpeeService = Depends(get_service)) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.context.store.build_release)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/logs")
async def logs(
    limit: int = 200,
    surface: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    q: str | None = None,
    event_log: EventLog = Depends(get_event_log),
) -> dict[str, Any]:
    """返回最近的操作日志（HTTP 请求与 MCP 工具调用合并的时间线）。"""

    events = await run_in_threadpool(
        event_log.read,
        limit=limit,
        surface=surface,
        kind=kind,
        status=status,
        query=q,
    )
    return {"stats": event_log.stats(), "count": len(events), "events": events}


@router.post("/logs/clear")
async def clear_logs(event_log: EventLog = Depends(get_event_log)) -> dict[str, Any]:
    """清空当前日志文件。"""

    await run_in_threadpool(event_log.clear)
    return {"ok": True}


@router.get("/figures/preview")
async def figure_preview(
    series_key: str,
    year: int,
    subject: str,
    paper_no: int,
    question_no: int,
    figure_index: int = 0,
    renderer: FigureRenderer = Depends(get_figure_renderer),
    service: NpeeService = Depends(get_service),
) -> Response:
    """Render one question figure to SVG on demand.

    KaTeX cannot render TikZ, so the viewer requests a compiled SVG here. The
    result is cached on disk by content hash, so repeated views do not recompile.
    """

    try:
        paper = await run_in_threadpool(service.library.get_paper, series_key, year, subject, paper_no)
    except NpeeError as error:
        raise _to_http_error(error) from error
    questions = paper.get("questions", [])
    question = next((item for item in questions if int(item["number"]) == question_no), None)
    if question is None:
        raise HTTPException(status_code=404, detail=f"question {question_no} not found")
    figures = _question_figures(question)
    if figure_index < 0 or figure_index >= len(figures):
        raise HTTPException(status_code=404, detail=f"figure {figure_index} not found on question {question_no}")
    figure = figures[figure_index]
    if figure.get("kind") != "tikz":
        raise HTTPException(status_code=400, detail="only TikZ figures can be previewed")
    try:
        result = await run_in_threadpool(renderer.render, figure.get("latex") or "")
    except NpeeError as error:
        raise _to_http_error(error) from error
    return Response(
        content=result.svg,
        media_type="image/svg+xml",
        headers={"X-NPEE-Figure-Cached": "1" if result.cached else "0", "Cache-Control": "public, max-age=86400"},
    )


def _question_figures(question: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every figure attached to a question in display order."""

    figures: list[dict[str, Any]] = list((question.get("stem") or {}).get("figures") or [])
    for choice in question.get("choices") or []:
        figures.extend(choice.get("figures") or [])
    for subpart in question.get("subparts") or []:
        figures.extend(subpart.get("figures") or [])
    return figures


@router.post("/compositions/validate")
async def validate_composition(
    composition: dict[str, Any],
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.composition.validate, composition)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/compositions/packages")
async def list_composition_packages(
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    """仓库里的组卷包（``composition/<id>/``），前端可直接打开与修改。"""

    packages = await run_in_threadpool(service.composition.list_packages)
    return {"packages": packages, "count": len(packages)}


@router.get("/compositions/packages/{composition_id}")
async def get_composition_package(
    composition_id: str,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(service.composition.load_package, composition_id)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.put("/compositions/packages/{composition_id}")
async def put_composition_package(
    composition_id: str,
    composition: dict[str, Any],
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    """把编辑后的组卷文档写回包内；校验失败返回 400，不会留下半个包。"""

    try:
        return await run_in_threadpool(
            service.composition.save_package, composition_id, composition
        )
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.post("/compositions/build")
async def build_composition(
    payload: dict[str, Any],
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(_build_from_payload, service, payload)
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.post("/compositions/compile")
async def compile_composition(
    payload: dict[str, Any],
    service: NpeeService = Depends(get_service),
) -> Response:
    """Compile a composition.

    Two accepted payloads:

    - ``{"composition": {...}}`` to compile an existing composition document;
    - ``{"selections": [...], "title": ..., ...}`` to build one first.

    The response is the PDF or ZIP. A ``dry_run`` request returns a JSON report
    instead so the caller can inspect the generated TeX without TeX installed.
    """

    try:
        if "composition" in payload:
            composition = payload["composition"]
            if not isinstance(composition, dict):
                raise NpeeError("composition must be an object")
        else:
            composition = _build_from_payload(service, payload)
        dry_run = bool(payload.get("dry_run"))
        result = await run_in_threadpool(
            service.composition.compile,
            composition,
            dry_run=dry_run,
            layouts=payload.get("layouts"),
            spacing=payload.get("spacing"),
        )
    except NpeeError as error:
        raise _to_http_error(error) from error
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    if dry_run:
        from fastapi.responses import JSONResponse

        return JSONResponse(result.to_dict())
    pdfs = [path for path in result.artifacts if path.lower().endswith(".pdf")]
    if not pdfs:
        from fastapi.responses import JSONResponse

        return JSONResponse(result.to_dict())
    primary = pdfs[0]
    from pathlib import Path

    data = Path(service.repository_root / primary).read_bytes() if not Path(primary).is_absolute() else Path(primary).read_bytes()
    filename = Path(primary).name
    from urllib.parse import quote

    headers = {
        "Content-Disposition": f'attachment; filename="npee-export.pdf"; filename*=UTF-8\'\'{quote(filename)}',
        "X-NPEE-Export-Format": "application/pdf",
    }
    return Response(content=data, media_type="application/pdf", headers=headers)


@router.post("/compositions/submit")
async def submit_composition(
    payload: dict[str, Any],
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    """把编译放到后台线程，立即返回可轮询的任务。"""

    try:
        if "composition" in payload:
            composition = payload["composition"]
            if not isinstance(composition, dict):
                raise NpeeError("composition must be an object")
        else:
            composition = _build_from_payload(service, payload)
        job = await run_in_threadpool(
            service.composition.submit_compile,
            composition,
            dry_run=bool(payload.get("dry_run")),
            layouts=payload.get("layouts"),
            spacing=payload.get("spacing"),
        )
        return job.to_dict()
    except NpeeError as error:
        raise _to_http_error(error) from error


@router.get("/compositions/jobs")
async def list_composition_jobs(
    limit: int = 20,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    """列出最近的编译任务。"""

    return {"jobs": await run_in_threadpool(service.composition.list_jobs, limit)}


@router.get("/compositions/jobs/{job_id}")
async def composition_job(
    job_id: str,
    service: NpeeService = Depends(get_service),
) -> dict[str, Any]:
    """查询编译任务状态。"""

    job = await run_in_threadpool(service.composition.get_job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"任务不存在：{job_id}")
    return job.to_dict()


@router.get("/compositions/jobs/{job_id}/artifact")
async def composition_job_artifact(
    job_id: str,
    index: int = 0,
    service: NpeeService = Depends(get_service),
) -> Response:
    """Download one artifact produced by a finished compile job.

    The asynchronous flow (submit → poll → download) needs a way to fetch the
    result: the job only reports artifact *paths*, and the browser cannot read the
    server filesystem. This endpoint streams the file back under its real name.
    """

    job = await run_in_threadpool(service.composition.get_job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"任务不存在：{job_id}")
    if job.status != "succeeded":
        raise HTTPException(status_code=409, detail=f"任务尚未完成：{job.status}")
    artifacts: list[str] = list(job.artifacts or [])
    if index < 0 or index >= len(artifacts):
        raise HTTPException(status_code=404, detail=f"产物不存在：index={index}")

    from pathlib import Path
    from urllib.parse import quote

    primary = artifacts[index]
    path = Path(primary)
    if not path.is_absolute():
        path = Path(service.repository_root) / primary
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"产物文件已不存在：{primary}")

    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    filename = path.name
    return Response(
        content=path.read_bytes(),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"export.bin\"; filename*=UTF-8''{quote(filename)}",
        },
    )


def _build_from_payload(service: NpeeService, payload: dict[str, Any]) -> dict[str, Any]:
    """Build a composition document from a lightweight request payload."""

    composition_id = str(payload.get("composition_id") or "composition")
    title = str(payload.get("title") or "组卷")
    document = payload.get("document")
    compile_config = payload.get("compile")
    if isinstance(payload.get("groups"), list):
        return service.composition.build_by_group(
            composition_id,
            payload["groups"],
            document=document,
            compile_config=compile_config,
        )
    selections = payload.get("selections")
    if not isinstance(selections, list) or not selections:
        raise NpeeError("payload requires either selections or groups")
    return service.composition.build(
        composition_id,
        title,
        selections,
        document=document,
        compile_config=compile_config,
    )
