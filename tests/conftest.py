"""Shared pytest fixtures.

Every test runs against a temporary data root so no test touches the real
``.npee-math-papers`` store. The fixtures are deliberately small but exercise the
same code paths the production store does.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from npee_math_papers.service import NpeeService  # noqa: E402

SUBJECTS = ("math1", "math2", "math3")


def make_choice_question(number: int = 1, *, stem_prefix: str = "") -> dict:
    """Return one valid schema-3.0 multiple-choice question."""

    return {
        "number": number,
        "section": "choice",
        "points": 5,
        "stem": {"text": f"{stem_prefix}设 $f(x)=x^{number}$，则 $f'(1)=$\\ExamSelection。", "figures": []},
        "choices": [
            {"label": label, "text": text, "figures": []}
            for label, text in (("A", "$0$"), ("B", f"${number}$"), ("C", "$2$"), ("D", "$3$"))
        ],
    }


def make_fill_question(number: int = 11) -> dict:
    """Return one valid schema-3.0 fill-in question."""

    return {
        "number": number,
        "section": "fill",
        "points": 5,
        "stem": {"text": "设 $a>0$，则 $\\int_0^1 x\\,dx=$ \\ExamBlank。", "figures": []},
    }


@pytest.fixture()
def data_root(tmp_path: Path) -> Path:
    """An empty, isolated data root."""

    root = tmp_path / ".npee-math-papers"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture()
def service(data_root: Path) -> NpeeService:
    """A service wired to the isolated data root."""

    return NpeeService.create(data_root, repository_root=REPO_ROOT)


@pytest.fixture()
def seeded(service: NpeeService) -> NpeeService:
    """A service with two bundles / three papers already ingested."""

    service.extraction.ingest("demo", 2024, "math1", 1, [make_choice_question(1), make_fill_question(11)])
    service.extraction.ingest("demo", 2024, "math1", 2, [make_choice_question(1)])
    service.extraction.ingest("other", 2025, "math2", 1, [make_choice_question(1)])
    return service


@pytest.fixture()
def repo_tmp(request, tmp_path: Path) -> Path:
    """A throwaway directory for assets that must be cleaned up."""

    target = tmp_path / "assets"
    target.mkdir()
    request.addfinalizer(lambda: shutil.rmtree(target, ignore_errors=True))
    return target
