"""The request-log middleware captures what was actually sent and returned."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import Response

from npee_math_papers.api.logging import RequestLogMiddleware
from npee_math_papers.service.events import EventLog


@pytest.fixture()
def logged_app(tmp_path, monkeypatch):
    """A tiny app wired to a throwaway event log."""

    app = FastAPI()

    @app.get("/things")
    async def things() -> dict:
        return {"items": [1, 2, 3]}

    @app.post("/things")
    async def create(payload: dict) -> dict:
        return {"created": payload}

    @app.get("/blob")
    async def blob() -> Response:
        return Response(content=b"%PDF-1.4 fake", media_type="application/pdf")

    log = EventLog(tmp_path / "events.jsonl")
    app.add_middleware(RequestLogMiddleware, event_log=log)
    return app, log


def read_events(log: EventLog) -> dict[str, dict]:
    return {event["name"]: event for event in log.read(limit=50)}


def test_records_query_and_response_body(logged_app) -> None:
    app, log = logged_app
    with TestClient(app) as client:
        client.get("/things?a=1")

    (event,) = log.read()
    assert event["name"] == "GET /things"
    assert event["status"] == "ok"
    assert event["status_code"] == 200
    assert event["detail"]["query"] == "a=1"
    # A GET has no body, and the log says so rather than inventing one.
    assert event["request"] == {}
    assert event["response"]["json"] == {"items": [1, 2, 3]}


def test_captures_a_request_body(logged_app) -> None:
    app, log = logged_app
    with TestClient(app) as client:
        client.post("/things", json={"name": "demo"})

    (event,) = log.read()
    assert event["request"]["json"] == {"name": "demo"}
    assert event["response"]["json"] == {"created": {"name": "demo"}}
    assert event["request"]["bytes"] == len(b'{"name":"demo"}')


def test_binary_response_is_size_only(logged_app) -> None:
    app, log = logged_app
    with TestClient(app) as client:
        response = client.get("/blob")

    # The body still reaches the caller intact — capture must not consume it.
    assert response.content == b"%PDF-1.4 fake"
    (event,) = log.read()
    assert event["response"]["binary"] is True
    assert event["response"]["bytes"] == len(b"%PDF-1.4 fake")
    assert "text" not in event["response"]


def test_error_responses_are_recorded_with_their_status(tmp_path) -> None:
    app = FastAPI()

    @app.post("/boom")
    async def boom() -> dict:
        raise ValueError("nope")

    log = EventLog(tmp_path / "events.jsonl")
    app.add_middleware(RequestLogMiddleware, event_log=log)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/boom", json={"x": 1})

    assert response.status_code == 500
    (event,) = log.read()
    assert event["status"] == "error"
    # The body of the failed request is still on record: that is what makes a
    # failure reproducible.
    assert event["request"]["json"] == {"x": 1}
