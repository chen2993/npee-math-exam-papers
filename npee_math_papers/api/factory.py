"""NPEE 应用 API 工厂。

构建一个只依赖共享 :class:`NpeeService` 的 FastAPI 应用。没有独立的数据服务：
题库只创建一次并注入，因此 HTTP API 与 MCP 服务共用同一份实现。每次请求都会写入
共享事件日志，供前端的「日志管理」页查看。
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from npee_math_papers.api.logging import RequestLogMiddleware
from npee_math_papers.api.routes import router
from npee_math_papers.core.figure_render import FigureRenderer
from npee_math_papers.service import NpeeService
from npee_math_papers.service.events import default_event_log


def create_application(service: NpeeService | None = None) -> FastAPI:
    repository_root = Path(__file__).resolve().parents[2]
    app = FastAPI(
        title="NPEE Application API",
        version="3.0.0",
        description="Thin HTTP adapter over the NPEE paper store.",
    )
    origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    extra = os.environ.get("NPEE_CORS_ORIGINS", "")
    origins.extend(item.strip() for item in extra.split(",") if item.strip())

    service_instance = service or NpeeService.create(repository_root=repository_root)
    event_log = default_event_log(repository_root)

    app.add_middleware(RequestLogMiddleware, event_log=event_log)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.service = service_instance
    app.state.event_log = event_log
    app.state.figure_renderer = FigureRenderer(repository_root, repository_root / "build" / "figure-cache")
    app.include_router(router, prefix="/api")
    return app
