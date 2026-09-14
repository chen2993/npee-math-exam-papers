from __future__ import annotations

from fastapi import Request

from npee_math_papers.core.figure_render import FigureRenderer
from npee_math_papers.service import NpeeService
from npee_math_papers.service.events import EventLog


def get_service(request: Request) -> NpeeService:
    """Return the shared :class:`NpeeService` from application state."""

    return request.app.state.service


def get_figure_renderer(request: Request) -> FigureRenderer:
    """Return the shared on-demand figure renderer from application state."""

    return request.app.state.figure_renderer


def get_event_log(request: Request) -> EventLog:
    """Return the shared event log from application state."""

    return request.app.state.event_log
