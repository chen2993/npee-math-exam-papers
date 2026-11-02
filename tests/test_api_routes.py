"""HTTP adapter: routes delegate to NpeeService and map errors to 4xx."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from npee_math_papers.api.factory import create_application

from tests.conftest import make_choice_question


@pytest.fixture()
def client(service) -> TestClient:
    app = create_application(service)
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_ok(client) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["provider"] == "npee-store"


def test_papers_list_starts_empty(client) -> None:
    body = client.get("/api/papers").json()
    assert body["total"] == 0


def test_papers_list_accepts_search_and_order(client, service) -> None:
    """The catalogue's search box and sort control are backed by these parameters."""

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    assert client.get("/api/papers", params={"q": "demo"}).json()["total"] == 1
    assert client.get("/api/papers", params={"q": "nothing-here"}).json()["total"] == 0
    ordered = client.get("/api/papers", params={"order": "questions-desc"}).json()
    counts = [paper["question_count"] for paper in ordered["papers"]]
    assert counts == sorted(counts, reverse=True)

def test_papers_list_ignores_an_unknown_order(client, service) -> None:
    """An old bookmark must still return data rather than a 422."""

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    assert client.get("/api/papers", params={"order": "made-up"}).status_code == 200

def test_bundles_list_accepts_the_paper_filter_vocabulary(client, service) -> None:
    """`/bundles` filters the same way `/papers` does.

    The MCP tool filtered `year`/`subject` in Python while this endpoint could
    not filter them at all, so the two surfaces offered different capabilities
    for the same query. Both now delegate to one service method.
    """

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    service.extraction.ingest("other", 2025, "math2", 1, [make_choice_question(1)])

    assert len(client.get("/api/bundles").json()["bundles"]) == 2

    by_year = client.get("/api/bundles", params={"year": 2024}).json()["bundles"]
    assert [bundle["bundle"] for bundle in by_year] == ["demo-2024-math1"]

    by_subject = client.get("/api/bundles", params={"subject": "math2"}).json()["bundles"]
    assert [bundle["bundle"] for bundle in by_subject] == ["other-2025-math2"]

    by_series = client.get("/api/bundles", params={"series_key": "demo"}).json()["bundles"]
    assert [bundle["bundle"] for bundle in by_series] == ["demo-2024-math1"]

def test_the_http_surface_cannot_touch_the_paper_store(client, service) -> None:
    """The frontend is a read-only view of the library.

    The POST routes that remain are not library writes: `/logs/clear` truncates
    the activity log, and the `/compositions/*` routes generate PDFs under
    `build/`. No route may reach an ingest or delete method, so a browser
    mistake cannot alter a paper.
    """

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    before = service.library.stats()

    # A path that exists but has no such method is 405; a path that does not
    # exist at all is 404. Both mean the browser cannot reach a library write.
    assert client.post("/api/papers", json={"questions": []}).status_code == 405
    assert client.put("/api/papers", json={}).status_code == 405
    assert client.delete("/api/papers/demo/2024/math1/1").status_code == 405
    assert client.post("/api/sources", json={}).status_code == 404

    assert service.library.stats() == before

def test_only_documented_non_get_routes_exist(client) -> None:
    """Any non-GET route must be one of the deliberate non-library writes."""

    from npee_math_papers.api.factory import create_application

    allowed = {
        "/api/logs/clear",
        "/api/compositions/validate",
        "/api/compositions/build",
        "/api/compositions/compile",
        "/api/compositions/submit",
        # 组卷包的写入口：前端把编辑结果存回 composition/<id>/composition.json。
        "/api/compositions/packages/{composition_id}",
    }
    schema = create_application().openapi()
    writes = {
        path
        for path, operations in schema["paths"].items()
        if {"post", "put", "patch", "delete"} & set(operations)
    }
    assert writes == allowed, writes

def test_missing_paper_maps_to_404(client) -> None:
    """A missing record is a 404, not a generic 400."""

    response = client.get("/api/papers/demo/2024/math1/1")
    assert response.status_code == 404


def test_invalid_request_maps_to_400(client) -> None:
    response = client.post("/api/compositions/validate", json={"composition_id": "Bad Id"})
    assert response.status_code == 400


def test_ingest_is_not_exposed_over_http(client) -> None:
    """Writes are agent-only (MCP); the HTTP surface stays read-mostly."""

    assert client.post("/api/papers", json={}).status_code == 405


def test_series_and_bundles_and_overview(client) -> None:
    assert "series" in client.get("/api/series").json()
    assert "bundles" in client.get("/api/bundles").json()
    assert {"stats", "series", "bundles"} <= set(client.get("/api/overview").json())


def test_compositions_validate_accepts_and_rejects(client) -> None:
    ok = client.post("/api/compositions/validate", json=_composition())
    assert ok.status_code == 200
    bad = client.post("/api/compositions/validate", json={"composition_id": "Bad Id"})
    assert bad.status_code == 400


def test_compositions_build_returns_document(client, service) -> None:
    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    response = client.post(
        "/api/compositions/build",
        json={
            "composition_id": "demo-comp",
            "title": "示例",
            "selections": [{"series_key": "demo", "year": 2024, "subject": "math1", "paper_no": 1}],
        },
    )
    assert response.status_code == 200
    document = response.json()
    assert document["composition_id"] == "demo-comp"
    assert document["groups"][0]["papers"][0]["paper_no"] == 1


def test_compositions_compile_dry_run_returns_report(client, service) -> None:
    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1)])
    response = client.post(
        "/api/compositions/compile",
        json={"composition": _composition(), "dry_run": True},
    )
    assert response.status_code == 200
    assert response.json()["composition_id"] == "demo-comp"


def test_unknown_compile_job_is_404(client) -> None:
    assert client.get("/api/compositions/jobs/does-not-exist").status_code == 404


def test_compile_job_artifact_requires_a_finished_job(client, service) -> None:
    """A queued/running job has no artifact to hand back yet (409, not 500)."""

    from npee_math_papers.service.jobs import CompileJob

    job = CompileJob(job_id="job-running", composition_id="demo-comp", status="running")
    service.composition.jobs._jobs[job.job_id] = job
    response = client.get(f"/api/compositions/jobs/{job.job_id}/artifact")
    assert response.status_code == 409


def test_compile_job_artifact_streams_the_file(client, service, tmp_path) -> None:
    """A finished job's artifact is downloadable under its real name."""

    import urllib.parse
    from npee_math_papers.service.jobs import CompileJob

    target = service.repository_root / "build" / "demo-artifact.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"%PDF-1.4 demo")
    job = CompileJob(
        job_id="job-done",
        composition_id="demo-comp",
        status="succeeded",
        artifacts=["build/demo-artifact.pdf"],
    )
    service.composition.jobs._jobs[job.job_id] = job
    response = client.get(f"/api/compositions/jobs/{job.job_id}/artifact")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 demo"
    disposition = response.headers["content-disposition"]
    assert urllib.parse.quote("demo-artifact.pdf") in disposition


def test_compile_job_artifact_rejects_a_bad_index(client, service) -> None:
    from npee_math_papers.service.jobs import CompileJob

    job = CompileJob(job_id="job-done2", composition_id="demo-comp", status="succeeded", artifacts=["build/x.pdf"])
    service.composition.jobs._jobs[job.job_id] = job
    assert client.get(f"/api/compositions/jobs/{job.job_id}/artifact?index=5").status_code == 404


def _composition() -> dict:
    return {
        "schema_version": "3.0",
        "composition_id": "demo-comp",
        "metadata": {"title": "示例", "year": 2024, "subject_scope": ["math1"]},
        "catalog": {"sources": [{"id": "demo"}]},
        "document": {
            "toc": {"enabled": False, "title": "目录", "include_groups": True, "include_papers": True},
            "layout": "a4",
            "theme": "print",
            "spacing": "compact",
            "print": True,
            "opening": {"show": True, "candidate_info": False, "notices": False},
        },
        "groups": [
            {
                "id": "g",
                "title": "组",
                "order_index": 1,
                "papers": [{"year": 2024, "subject": "math1", "series_key": "demo", "paper_no": 1}],
            }
        ],
        "compile": {
            "engine": "xelatex",
            "passes": 1,
            "targets": [
                {"layout": "a4", "theme": "print", "spacing": "compact", "print": True, "enabled": True, "answers": False, "output_suffix": None}
            ],
            "output": {"directory": "build/output", "filename_template": "{composition_id}.pdf", "overwrite": True},
        },
    }
