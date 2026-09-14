r"""On-disk serialization tuned for LaTeX-heavy content.

Why not JSON
------------
Exam questions are full of LaTeX, and JSON forces every backslash to be escaped:
``\\dfrac``, ``\\begin{cases}`` and every ``\\draw`` in a TikZ block. On real
published content this roughly doubles the backslash count and turns a multi-line
TikZ drawing into one enormous single-line string. It is hard for a human to read,
awkward for an agent to edit, and a single missing backslash corrupts the file.

Chosen format: YAML with literal block scalars
-----------------------------------------------
Any string that contains a backslash, a newline or significant leading/trailing
whitespace is written with a literal block scalar (``|-`` / ``|2-``). Inside such
a block the text is stored verbatim, so::

    text: |-
      \dfrac{a}{b}, \begin{cases}x\\y\end{cases}

round-trips byte-exactly with zero escaping. Measured on real questions this cut
the backslash count roughly in half and reduced backslash escaping to a single
occurrence (the genuine LaTeX row separator ``\\\\`` inside ``cases``).

Transport is still JSON
-----------------------
HTTP responses and the MCP protocol use JSON, produced from these documents. Only
the files on disk use YAML, and only this module reads or writes them.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from npee_math_papers.core.errors import ValidationError

try:  # pragma: no cover - import guard, exercised by the environment check
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import LiteralScalarString

    YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    YAML_AVAILABLE = False


def _new_yaml() -> "YAML":
    if not YAML_AVAILABLE:
        raise ValidationError(
            "ruamel.yaml is required to read or write .npee-math-papers paper files; install it with "
            '"python -m pip install ruamel.yaml"'
        )
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.width = 8192
    yaml.allow_unicode = True
    yaml.preserve_quotes = False
    return yaml


def _needs_literal_block(value: str) -> bool:
    """Return whether ``value`` should be stored as a literal block scalar.

    Literal blocks are used for LaTeX, code and anything multiline. Plain prose
    without backslashes stays a normal scalar so short fields stay on one line.
    """

    if "\\" in value or "\n" in value:
        return True
    return value != value.strip()


def _wrap(value: Any) -> Any:
    """Recursively convert strings that need verbatim storage into literal blocks."""

    if isinstance(value, dict):
        return {key: _wrap(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_wrap(item) for item in value]
    if isinstance(value, str) and _needs_literal_block(value):
        return LiteralScalarString(value)
    return value


def _unwrap(value: Any) -> Any:
    """Recursively convert loaded YAML back into plain Python types."""

    if isinstance(value, dict):
        return {str(key): _unwrap(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_unwrap(item) for item in value]
    if isinstance(value, str):
        return str(value)
    return value


def dumps(value: Any) -> str:
    """Serialize ``value`` to a YAML document string."""

    yaml = _new_yaml()
    buffer = io.StringIO()
    yaml.dump(_wrap(value), buffer)
    return buffer.getvalue()


def loads(text: str) -> Any:
    """Parse a YAML document string into plain Python types."""

    yaml = _new_yaml()
    try:
        parsed = yaml.load(text)
    except Exception as error:  # ruamel raises several subclasses
        raise ValidationError(f"invalid YAML: {error}") from error
    return _unwrap(parsed)


def dump_json_compatible(value: Any) -> Any:
    """Return a plain JSON-compatible copy of ``value`` (no YAML node types).

    Used when a document read from disk must be returned over HTTP or MCP.
    """

    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def write_document(path: Path, value: Any) -> None:
    """Write a YAML document atomically, with a stable trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = dumps(value)
    if not text.endswith("\n"):
        text += "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def read_document(path: Path) -> Any:
    """Read and parse a YAML document."""

    if not path.is_file():
        raise ValidationError(f"document is missing: {path.as_posix()}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValidationError(f"cannot read {path.as_posix()}: {error}") from error
    return loads(text)


def document_extension() -> str:
    """Return the canonical paper document extension."""

    return ".yaml"
