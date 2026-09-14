"""Event log: payload capture, trimming and the read-back contract."""

from __future__ import annotations

import json

from npee_math_papers.service.events import (
    MAX_PAYLOAD_ITEMS,
    Event,
    EventLog,
    build_payload,
    decode_body,
)


def test_build_payload_is_empty_when_there_is_nothing_to_record() -> None:
    """A bare GET must not grow the log."""

    assert build_payload(None) == {}


def test_build_payload_keeps_json_and_byte_size() -> None:
    payload = build_payload({"ok": True}, content_type="application/json; charset=utf-8", raw_bytes=11)
    assert payload["json"] == {"ok": True}
    assert payload["bytes"] == 11
    assert payload["content_type"] == "application/json"


def test_build_payload_summarises_binary_bodies_by_size_only() -> None:
    """The log must never become a second copy of the artifact store."""

    payload = build_payload(None, content_type="application/pdf", raw_bytes=119_331)
    assert payload["binary"] is True
    assert payload["bytes"] == 119_331
    assert "text" not in payload and "json" not in payload


def test_build_payload_trims_structurally_not_by_truncating_json() -> None:
    """One huge field must not swallow the rest of the object."""

    payload = build_payload(
        {"stem": {"text": "x" * 5000}, "paper_no": 7},
        content_type="application/json",
    )
    # The sibling field survives, which a mid-string cut of the serialised JSON
    # would have destroyed.
    assert payload["json"]["paper_no"] == 7
    assert len(payload["json"]["stem"]["text"]) < 5000


def test_build_payload_marks_long_collections() -> None:
    payload = build_payload(list(range(MAX_PAYLOAD_ITEMS + 10)), content_type="application/json")
    items = payload["json"]
    assert items[-1] == f"…（另 10 项）"
    assert len(items) == MAX_PAYLOAD_ITEMS + 1


def test_decode_body_parses_json_and_sizes_binary() -> None:
    value, size = decode_body(b'{"q": "x"}', "application/json")
    assert value == {"q": "x"} and size == 10
    value, size = decode_body(b"%PDF-1.4", "application/pdf")
    assert value is None and size == 8


def test_event_line_round_trips_with_payloads(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    log.record(
        surface="http",
        kind="request",
        name="POST /api/x",
        status="ok",
        status_code=201,
        duration_ms=12.5,
        detail={"method": "POST"},
        request=build_payload({"a": 1}),
        response=build_payload({"b": 2}, raw_bytes=9),
    )
    (event,) = log.read()
    assert event["status_code"] == 201
    assert event["request"]["json"] == {"a": 1}
    assert event["response"]["json"] == {"b": 2}
    assert event["response"]["bytes"] == 9


def test_read_still_accepts_the_previous_schema(tmp_path) -> None:
    """Logs written before payload capture must keep loading."""

    path = tmp_path / "events.jsonl"
    legacy = {
        "ts": "2026-01-01T00:00:00.000Z",
        "surface": "mcp",
        "kind": "tool",
        "name": "npee_list_papers",
        "status": "ok",
        "duration_ms": 4.0,
        "detail": {"arguments": {}},
    }
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    (event,) = EventLog(path).read()
    assert event["name"] == "npee_list_papers"
    assert event["request"] == {} and event["response"] == {}
    assert event["status_code"] is None


def test_search_matches_inside_recorded_bodies(tmp_path) -> None:
    """"Which request carried subject=math3?" must be answerable."""

    log = EventLog(tmp_path / "events.jsonl")
    log.record(
        surface="http",
        kind="request",
        name="POST /api/compositions/validate",
        request=build_payload({"subject": "math3"}),
    )
    log.record(surface="http", kind="request", name="GET /api/overview")

    hits = log.read(query="math3")
    assert len(hits) == 1
    assert hits[0]["name"] == "POST /api/compositions/validate"


def test_event_from_line_rejects_garbage() -> None:
    assert Event.from_line("not json") is None
    assert Event.from_line("[1, 2]") is None


def test_read_returns_the_newest_events_not_the_oldest(tmp_path) -> None:
    """Regression: the page must show recent traffic, not day-old entries.

    The old implementation stopped as soon as it had `limit` matches, which on a
    log longer than the limit returned the *first* events in the file — the log
    page then displayed the oldest requests and never any new ones.
    """

    log = EventLog(tmp_path / "events.jsonl")
    for index in range(50):
        log.record(surface="http", kind="request", name=f"GET /api/item/{index}")

    newest = log.read(limit=5)
    assert [event["name"] for event in newest] == [
        "GET /api/item/49",
        "GET /api/item/48",
        "GET /api/item/47",
        "GET /api/item/46",
        "GET /api/item/45",
    ]


def test_read_window_also_considers_the_rotated_archive(tmp_path) -> None:
    """The window spans the archive and the live file, newest first."""

    log = EventLog(tmp_path / "events.jsonl")
    for index in range(10):
        log.record(surface="http", kind="request", name=f"GET /old/{index}")

    # Simulate a rotation: move the live file aside and start a fresh one.
    log.path.replace(log.path.with_suffix(".1.jsonl"))
    for index in range(3):
        log.record(surface="http", kind="request", name=f"GET /new/{index}")

    newest = log.read(limit=4)
    assert [event["name"] for event in newest] == [
        "GET /new/2",
        "GET /new/1",
        "GET /new/0",
        "GET /old/9",
    ]


def test_read_applies_filters_to_the_newest_window(tmp_path) -> None:
    """A filter must not resurrect the oldest entries."""

    log = EventLog(tmp_path / "events.jsonl")
    for index in range(20):
        log.record(surface="http", kind="request", name=f"GET /api/a/{index}", status="ok")
    log.record(surface="http", kind="request", name="GET /api/b/boom", status="error")

    errors = log.read(limit=5, status="error")
    assert [event["name"] for event in errors] == ["GET /api/b/boom"]
