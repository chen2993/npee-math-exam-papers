"""Release manifest: content hashes that pin an exact library version.

A composition stores natural keys plus the ``content_hash`` it was authored
against. Before compiling, the builder recomputes each hash from the store and
fails if it changed, so a reader never silently renders a different revision than
the one they selected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from npee_math_papers.core.canonical import canonical_json, content_hash, sha256_hex
from npee_math_papers.core.errors import ReleaseError, ValidationError

RELEASE_SCHEMA_VERSION = "3.0"


@dataclass
class ReleaseManifest:
    """A frozen snapshot of every paper's content hash."""

    schema_version: str
    library_hash: str
    papers: dict[str, str] = field(default_factory=dict)

    def hash_for(self, natural_key: str) -> str | None:
        return self.papers.get(natural_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "library_hash": self.library_hash,
            "paper_count": len(self.papers),
            "papers": dict(sorted(self.papers.items())),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReleaseManifest":
        papers = value.get("papers")
        if not isinstance(papers, Mapping):
            raise ReleaseError("release manifest must contain a papers object")
        return cls(
            schema_version=str(value.get("schema_version", RELEASE_SCHEMA_VERSION)),
            library_hash=str(value.get("library_hash", "")),
            papers={str(key): str(item) for key, item in papers.items()},
        )


def build_release_manifest(entries: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a release manifest from paper summaries.

    Each entry must carry ``natural_key`` and ``content_hash``. ``library_hash`` is
    the hash of the sorted ``natural_key -> content_hash`` map, so any change to any
    paper changes the library hash.
    """

    papers: dict[str, str] = {}
    for entry in entries:
        key = str(entry.get("natural_key") or "")
        digest = str(entry.get("content_hash") or "")
        if not key or not digest:
            raise ValidationError("release entries require natural_key and content_hash")
        if key in papers and papers[key] != digest:
            raise ReleaseError(f"conflicting content hashes for {key}")
        papers[key] = digest
    ordered = dict(sorted(papers.items()))
    return {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "library_hash": content_hash(ordered),
        "paper_count": len(ordered),
        "papers": ordered,
    }


def load_release_manifest(path: Path) -> ReleaseManifest:
    """Read a release manifest from disk."""

    if not path.is_file():
        raise ReleaseError(f"release manifest is missing: {path.as_posix()}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ReleaseError(f"release manifest is not valid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise ReleaseError("release manifest must be a JSON object")
    return ReleaseManifest.from_dict(payload)


def write_release_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    """Write a release manifest atomically via the store's atomic writer."""

    from npee_math_papers.core.store import atomic_write_json

    atomic_write_json(Path(path), manifest)


def verify_release_manifest(
    manifest: ReleaseManifest,
    entries: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare a manifest against current paper summaries.

    Returns a structured report listing matching, changed, missing and extra
    papers instead of raising, so callers can decide whether drift is fatal.
    """

    current = {str(entry.get("natural_key")): str(entry.get("content_hash")) for entry in entries}
    changed = sorted(
        key for key, digest in current.items() if key in manifest.papers and manifest.papers[key] != digest
    )
    missing = sorted(key for key in manifest.papers if key not in current)
    extra = sorted(key for key in current if key not in manifest.papers)
    unchanged = sorted(key for key in current if manifest.papers.get(key) == current[key])
    return {
        "ok": not changed and not extra,
        "matched": len(unchanged),
        "changed": changed,
        "missing": missing,
        "extra": extra,
        "manifest_hash": manifest.library_hash,
        "current_hash": content_hash(dict(sorted(current.items()))),
    }


def manifest_hash(papers: Mapping[str, str]) -> str:
    """Return the library hash for a ``natural_key -> content_hash`` mapping."""

    return content_hash(dict(sorted(papers.items())))


def source_sha256(path: Path) -> str:
    """Return the SHA-256 of a file's bytes, used for PDF provenance."""

    digest = sha256_hex(path.read_bytes())
    return digest


def hash_text(text: str) -> str:
    """Return the canonical hash of a text blob (prompt snapshots, TeX assets)."""

    return sha256_hex(canonical_json(text))
