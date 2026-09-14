"""Launcher static server: API-URL injection and SPA fallback.

These cover the pre-existing production bug where the served bundle called a
relative ``/api`` on a static server that has no proxy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from npee_math_papers.launcher.static_server import inject_api_url  # noqa: E402

INDEX = (
    "<!doctype html>\n<html><head><meta charset='UTF-8' />"
    "<script type=\"module\" src=\"/assets/index.js\"></script></head>"
    "<body><div id='root'></div></body></html>"
)


def test_inject_api_url_adds_a_global_before_head_close() -> None:
    result = inject_api_url(INDEX, "http://127.0.0.1:8766/api")
    assert 'window.NPEE_API_URL = "http://127.0.0.1:8766/api"' in result
    # Injecting must not disturb the module script tag.
    assert "/assets/index.js" in result
    assert result.index("NPEE_API_URL") < result.index("</head>")


def test_inject_api_url_is_idempotent() -> None:
    once = inject_api_url(INDEX, "http://127.0.0.1:8766/api")
    twice = inject_api_url(once, "http://127.0.0.1:9999/api")
    assert twice == once
    assert twice.count("NPEE_API_URL") == 1


def test_inject_api_url_without_a_url_is_a_noop() -> None:
    assert inject_api_url(INDEX, "") == INDEX


def test_inject_api_url_quotes_the_value() -> None:
    """A value with a quote must not break the emitted script."""

    result = inject_api_url(INDEX, 'http://x/";alert(1);//')
    assert 'window.NPEE_API_URL = "http://x/\\";alert(1);//"' in result


def test_inject_api_url_handles_documents_without_a_head() -> None:
    result = inject_api_url("<div>app</div>", "http://x/api")
    assert result.lstrip().startswith("<script>")
    assert "http://x/api" in result
