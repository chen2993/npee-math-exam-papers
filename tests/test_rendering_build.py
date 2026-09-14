"""End-to-end builder path: a composition document renders to TeX without LaTeX.

``build(dry_run=True)`` exercises the whole orchestration (catalog resolution,
target matrix, cover/hook assembly, main-document generation) without invoking
XeLaTeX, which makes it a fast but complete regression guard for the builder.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from npee_math_papers.service import NpeeService
from npee_math_papers.service.rendering.errors import CompositionError
from npee_math_papers.service.tex_builder import BuildOptions, build

from tests.conftest import make_choice_question, make_fill_question

REPO_ROOT = Path(__file__).resolve().parents[1]


def _composition(*, year: int | None = 2024) -> dict:
    metadata: dict = {"title": "示例组卷", "subject_scope": ["math1"]}
    if year is not None:
        metadata["year"] = year
    return {
        "schema_version": "3.0",
        "composition_id": "demo-comp",
        "metadata": metadata,
        "catalog": {"sources": [{"id": "demo"}]},
        "document": {
            "toc": {"enabled": False, "title": "目录", "include_groups": True, "include_papers": True},
            "layout": "a4",
            "theme": "print",
            "spacing": "compact",
            "opening": {"show": True, "candidate_info": False, "notices": False},
            "solution": {"structure": "pair-first", "pair_count": 2},
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
                {"layout": "a4", "theme": "print", "spacing": "compact", "enabled": True, "answers": False, "output_suffix": None}
            ],
            "output": {"directory": "build/demo-out", "filename_template": "x-{layout}-{spacing}.pdf", "overwrite": True},
        },
    }


@pytest.fixture()
def build_env(service: NpeeService, tmp_path):
    """Write a composition package and return (options, work dir).

    The builder only accepts repository-relative paths (that check is what keeps
    ``compile.output.directory`` from escaping the repo), so the package lives
    under the gitignored ``build/`` tree rather than the OS temp directory.
    """

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1), make_fill_question(11)])
    package = REPO_ROOT / "build" / "_builder-test" / tmp_path.name
    package.mkdir(parents=True, exist_ok=True)
    composition_path = package / "composition.json"
    composition_path.write_text(json.dumps(_composition(), ensure_ascii=False), encoding="utf-8")
    options = BuildOptions(
        composition=composition_path.relative_to(REPO_ROOT),
        work_dir=package / "gen",
        output_dir=package / "out",
        dry_run=True,
        clean=True,
        store=service.context.store,
    )
    return options, package


def test_dry_run_builds_tex_and_reports_targets(build_env) -> None:
    options, package = build_env
    report = build(options)
    assert report["composition_id"] == "demo-comp"
    assert len(report["targets"]) == 1
    main = package / "gen" / "a4-print-compact" / "main.tex"
    assert main.is_file()
    text = main.read_text(encoding="utf-8")
    assert "\\documentclass[a4,print,compact]{npee-math-exam}" in text
    assert "\\begin{document}" in text


def test_rendered_body_contains_the_questions(build_env) -> None:
    options, package = build_env
    build(options)
    body = (package / "gen" / "papers" / "fixed" / "paper-001.tex").read_text(encoding="utf-8")
    assert "ExamChoiceQuestion" in body
    assert "ExamFillQuestion" in body
    assert "\\ExamSection" in body


def test_missing_store_fails_loudly(tmp_path, service) -> None:
    """Without a store the builder must fail, not silently render nothing."""

    package = REPO_ROOT / "build" / "_builder-test" / (tmp_path.name + "-nostore")
    package.mkdir(parents=True, exist_ok=True)
    composition_path = package / "composition.json"
    composition_path.write_text(json.dumps(_composition(), ensure_ascii=False), encoding="utf-8")
    options = BuildOptions(
        composition=composition_path.relative_to(REPO_ROOT),
        work_dir=package / "gen",
        output_dir=package / "out",
        dry_run=True,
        clean=True,
        store=None,
    )
    with pytest.raises(CompositionError):
        build(options)


def test_unknown_paper_reference_fails(build_env) -> None:
    options, package = build_env
    document = _composition()
    document["groups"][0]["papers"][0]["paper_no"] = 9
    (package / "composition.json").write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CompositionError):
        build(options)
