"""Canonical serialization, natural keys and hashing."""

from __future__ import annotations

import pytest

from npee_math_papers.core.canonical import (
    canonical_json,
    content_hash,
    natural_key,
    natural_key_parts,
    record_key,
    sha256_hex,
)


def test_canonical_json_is_key_order_independent() -> None:
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_canonical_json_keeps_unicode_unescaped() -> None:
    assert "设" in canonical_json({"text": "设"})


def test_content_hash_ignores_key_order() -> None:
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})


def test_content_hash_detects_value_change() -> None:
    assert content_hash({"a": 1}) != content_hash({"a": 2})


def test_sha256_hex_accepts_bytes_and_str() -> None:
    assert sha256_hex("abc") == sha256_hex(b"abc")


def test_natural_key_round_trip() -> None:
    assert natural_key(2024, "math1", "demo", 7) == "2024/math1/demo/7"
    assert natural_key_parts(2024, "math1", "demo", 7) == (2024, "math1", "demo", 7)


def test_natural_key_coerces_numeric_strings() -> None:
    assert natural_key("2024", "math1", "demo", "7") == "2024/math1/demo/7"


def test_natural_key_rejects_non_numeric() -> None:
    with pytest.raises(ValueError):
        natural_key("twenty", "math1", "demo", 7)


def test_record_key_adds_catalog_suffix_only_when_needed() -> None:
    assert record_key(2024, "math1", "demo", 7) == "2024/math1/demo/7"
    assert record_key(2024, "math1", "demo", 7, "catalog-x") == "2024/math1/demo/7#catalog-x"
