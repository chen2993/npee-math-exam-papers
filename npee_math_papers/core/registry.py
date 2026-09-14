"""Series registry.

The registry is a lightweight, human-editable list of registered series with their
display names. It is the only place that maps ``series_key`` to a human name; the
per-bundle ``bundle.json`` copies the name for portability but the registry is
authoritative when present.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from npee_math_papers.core.domain import ID_RE
from npee_math_papers.core.errors import RegistryError, ValidationError

REGISTRY_SCHEMA_VERSION = "3.0"


@dataclass(frozen=True)
class CatalogEntry:
    """One registered series."""

    id: str
    name: str
    enabled: bool = True

    def to_dict(self, *, data_root: str = ".npee-math-papers") -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "papers": f"{data_root}/papers/{self.id}-*",
        }


@dataclass
class CatalogRegistry:
    """The full registry document."""

    entries: list[CatalogEntry] = field(default_factory=list)
    schema_version: str = REGISTRY_SCHEMA_VERSION

    def names(self) -> dict[str, str]:
        return {entry.id: entry.name for entry in self.entries}

    def by_id(self) -> dict[str, CatalogEntry]:
        return {entry.id: entry for entry in self.entries}

    def get(self, series_key: str) -> CatalogEntry | None:
        return self.by_id().get(series_key)

    def display_name(self, series_key: str) -> str:
        entry = self.get(series_key)
        return entry.name if entry else series_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "catalogs": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CatalogRegistry":
        raw = value.get("catalogs")
        if not isinstance(raw, list):
            raise RegistryError("registry must contain a catalogs array")
        entries: list[CatalogEntry] = []
        seen: set[str] = set()
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise RegistryError(f"registry entry {index} must be an object")
            series_id = str(item.get("id") or "").strip()
            if not ID_RE.fullmatch(series_id):
                raise RegistryError(f"registry entry {index} has an invalid id")
            if series_id in seen:
                raise RegistryError(f"registry repeats id {series_id!r}")
            seen.add(series_id)
            name = str(item.get("name") or series_id).strip() or series_id
            entries.append(CatalogEntry(id=series_id, name=name, enabled=item.get("enabled", True) is not False))
        return cls(entries=entries, schema_version=str(value.get("schema_version", REGISTRY_SCHEMA_VERSION)))


def validate_registry(registry: CatalogRegistry) -> None:
    """Fail if a registry is internally inconsistent."""

    ids: set[str] = set()
    for entry in registry.entries:
        if not ID_RE.fullmatch(entry.id):
            raise ValidationError(f"registry id {entry.id!r} must be a lowercase ASCII id")
        if entry.id in ids:
            raise ValidationError(f"registry repeats id {entry.id!r}")
        if not entry.name.strip():
            raise ValidationError(f"registry id {entry.id!r} has an empty display name")
        ids.add(entry.id)


def load_registry(path: Path) -> CatalogRegistry:
    """Load and validate the registry JSON."""

    if not path.is_file():
        raise RegistryError(f"registry is missing: {path.as_posix()}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RegistryError(f"registry is not valid JSON: {error.msg}") from error
    if not isinstance(payload, Mapping):
        raise RegistryError("registry must be a JSON object")
    registry = CatalogRegistry.from_dict(payload)
    validate_registry(registry)
    return registry


def registry_to_payload(registry: CatalogRegistry) -> dict[str, Any]:
    """Serialize a registry for writing."""

    return registry.to_dict()


def upsert_names(registry: CatalogRegistry, names: Mapping[str, str]) -> CatalogRegistry:
    """Return a registry with ``names`` merged in, creating missing entries."""

    by_id = registry.by_id()
    for series_key, display_name in names.items():
        by_id[series_key] = CatalogEntry(id=series_key, name=display_name, enabled=True)
    return CatalogRegistry(entries=[by_id[key] for key in sorted(by_id)], schema_version=registry.schema_version)


def entries_from_pairs(pairs: Iterable[tuple[str, str]]) -> CatalogRegistry:
    """Build a registry from ``(series_key, display_name)`` pairs."""

    return CatalogRegistry(entries=[CatalogEntry(id=key, name=name) for key, name in sorted(set(pairs))])
