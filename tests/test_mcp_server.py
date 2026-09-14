"""MCP adapter: tools are thin wrappers returning JSON strings."""

from __future__ import annotations

import asyncio
import json

import pytest

from tests.conftest import make_choice_question


@pytest.fixture()
def server(monkeypatch, service):
    """Build the FastMCP server, pointing ``_service()`` at the isolated store."""

    import npee_math_papers.mcp.server as server_module

    monkeypatch.setattr(server_module, "_service", lambda: service)
    return server_module.build_server()


def _call(server, name: str, arguments: dict | None = None):
    result = asyncio.run(server.call_tool(name, arguments or {}))
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def test_library_stats_tool(seeded, server) -> None:
    body = _call(server, "npee_library_stats")
    assert body["papers"] == 3


def test_list_series_tool(seeded, server) -> None:
    series = [item["series_key"] for item in _call(server, "npee_list_series")]
    assert series == ["demo", "other"]


def test_list_bundles_tool_filters_like_the_http_endpoint(seeded, server) -> None:
    """`npee_list_bundles` and `/api/bundles` accept the same filter vocabulary.

    The tool used to filter `year`/`subject` in Python while the endpoint could
    not filter them, so an agent and a browser asking the same question got
    different answer sets. Both now go through one service method.
    """

    everything = _call(server, "npee_list_bundles")
    assert len(everything) == 2

    by_year = _call(server, "npee_list_bundles", {"year": 2024})
    assert [item["bundle"] for item in by_year] == ["demo-2024-math1"]

    by_subject = _call(server, "npee_list_bundles", {"subject": "math2"})
    assert [item["bundle"] for item in by_subject] == ["other-2025-math2"]

    by_series = _call(server, "npee_list_bundles", {"series_key": "other"})
    assert [item["bundle"] for item in by_series] == ["other-2025-math2"]


def test_get_paper_tool_returns_questions(seeded, server) -> None:
    body = _call(server, "npee_get_paper", {"series_key": "demo", "year": 2024, "subject": "math1", "paper_no": 1})
    # The document keys sit at the top level; derived fields ride along in `meta`.
    assert body["paper"]["series_key"] == "demo"
    assert body["meta"]["natural_key"] == "2024/math1/demo/1"
    assert body["questions"]


def test_search_questions_tool(seeded, server) -> None:
    body = _call(server, "npee_search_questions", {"query": "设"})
    assert body["total"] >= 1


def test_ingest_paper_tool_writes(service, server) -> None:
    body = _call(
        server,
        "npee_ingest_paper",
        {"series_key": "demo", "year": 2024, "subject": "math1", "paper_no": 1, "questions": [make_choice_question(1)]},
    )
    assert body["natural_key"] == "2024/math1/demo/1"
    assert service.library.stats()["papers"] == 1


def test_validate_questions_tool_reports_failure(server) -> None:
    ok = _call(server, "npee_validate_questions", {"questions": [make_choice_question(1)]})
    assert ok["ok"] is True
    bad = _call(server, "npee_validate_questions", {"questions": [{"number": 1}]})
    assert bad["ok"] is False


def test_check_tex_tool_flags_missing_backslash(server) -> None:
    body = _call(server, "npee_check_tex", {"text": r"$\begin{array}{c|ccc}X&2\\hline P\end{array}$"})
    assert body["issue_count"] >= 1


def test_scan_alignments_tool_flags_blank_row(server) -> None:
    body = _call(server, "npee_scan_alignments", {"text": r"$\begin{pmatrix}a\\\\b\end{pmatrix}$"})
    kinds = {issue["kind"] for issue in body["issues"]}
    assert "alignment_blank_row" in kinds


def test_audit_tex_tool_scans_library(seeded, server) -> None:
    body = _call(server, "npee_audit_tex", {"limit": 5})
    assert body["papers_scanned"] == 3
    assert body["finding_count"] == 0


def test_unknown_tool_raises(server) -> None:
    with pytest.raises(Exception):
        asyncio.run(server.call_tool("npee_not_a_tool", {}))
