"""Canonical serialization, natural keys and content hashing.

Every layer must agree byte-for-byte on what "the same paper" means, otherwise
the published CSV, the data service cache and the composition release binding can
disagree while all looking locally valid. This module is that single definition.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

NATURAL_KEY_FIELDS = ("year", "subject", "series_key", "paper_no")


def canonical_json(value: Any) -> str:
    """Return a deterministic, compact JSON string.

    Keys are sorted, separators are tight and non-ASCII is preserved so a Chinese
    question stem round-trips without escaping. This is the exact form used for
    hashing and for the published ``questions_json`` column.
    """

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: bytes | str) -> str:
    """Return a lowercase SHA-256 hex digest for ``data``."""

    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def content_hash(value: Any) -> str:
    """Return the canonical content hash of any JSON-serializable value."""

    return sha256_hex(canonical_json(value))


def natural_key_parts(year: int | str, subject: str, series_key: str, paper_no: int | str) -> tuple[int, str, str, int]:
    """Coerce raw natural-key fields into their canonical typed tuple.

    Raises ``ValueError`` when a numeric field cannot be parsed, so callers can
    convert it into a domain-specific :class:`~npee_math_papers.core.errors.ValidationError`.
    """

    return (int(year), str(subject), str(series_key), int(paper_no))


def natural_key(year: int | str, subject: str, series_key: str, paper_no: int | str) -> str:
    """Return the slash-joined natural key ``year/subject/series_key/paper_no``."""

    return "/".join(str(part) for part in natural_key_parts(year, subject, series_key, paper_no))


def record_key_parts(year: int | str, subject: str, series_key: str, paper_no: int | str, catalog_id: str | None = None) -> tuple[int, str, str, int, str | None]:
    """Return the canonical record key parts.

    ``record_key`` extends the natural key with an optional ``catalog_id`` so two
    sources that publish the same natural key with different content stay
    addressable. The catalog suffix is only present for genuine conflicts.
    """

    base = natural_key_parts(year, subject, series_key, paper_no)
    return (*base, catalog_id or None)


def record_key(
    year: int | str,
    subject: str,
    series_key: str,
    paper_no: int | str,
    catalog_id: str | None = None,
) -> str:
    """Return the canonical record key, with ``#<catalog_id>`` only when needed."""

    base = natural_key(year, subject, series_key, paper_no)
    return f"{base}#{catalog_id}" if catalog_id else base


def sorted_natural_keys(keys: Sequence[tuple[int, str, str, int]]) -> list[tuple[int, str, str, int]]:
    """Return natural keys in the stable publish order used across the project."""

    return sorted(keys, key=lambda item: (item[0], item[1], item[2], item[3]))


def stable_payload_map(items: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``items`` sorted by key for readable, diff-friendly output."""

    return {key: items[key] for key in sorted(items)}
