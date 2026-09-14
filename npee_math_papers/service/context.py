"""Shared service context: the wired store, registry and managers.

Constructing the context once and passing it to every service keeps the wiring in
one place and lets tests build a service against a temporary data root.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from npee_math_papers.core.registry import CatalogRegistry, entries_from_pairs, load_registry
from npee_math_papers.core.sources import CaptureManager, SourceManager
from npee_math_papers.core.store import NpeePaths, PaperStore, atomic_write_json


@dataclass
class ServiceContext:
    """Everything a service needs, resolved against one data root."""

    paths: NpeePaths
    store: PaperStore
    sources: SourceManager
    captures: CaptureManager

    @classmethod
    def create(cls, root: str | Path | None = None, *, repository_root: Path | None = None) -> "ServiceContext":
        paths = NpeePaths.resolve(root, repository_root=repository_root)
        return cls(paths=paths, store=PaperStore(paths), sources=SourceManager(paths), captures=CaptureManager(paths))

    # --- registry ----------------------------------------------------------

    def registry(self) -> CatalogRegistry:
        """Load the registry, deriving one from bundles when the file is absent.

        A missing registry is not fatal: the store's own bundle metadata is enough
        to name every series, so the registry can always be rebuilt from the store.
        """

        if self.paths.registry.is_file():
            return load_registry(self.paths.registry)
        return self.derive_registry()

    def derive_registry(self) -> CatalogRegistry:
        """Build a registry from the bundles currently present in the store."""

        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()
        for bundle in self.store.list_bundles():
            if bundle.series_key in seen:
                continue
            seen.add(bundle.series_key)
            pairs.append((bundle.series_key, bundle.display_name or bundle.series_key))
        return entries_from_pairs(pairs)

    def write_registry(self, registry: CatalogRegistry) -> None:
        """Persist the registry."""

        atomic_write_json(
            self.paths.registry,
            {
                "schema_version": registry.schema_version,
                "catalogs": [
                    {"id": entry.id, "name": entry.name, "enabled": entry.enabled}
                    for entry in registry.entries
                ],
            },
        )

    def display_names(self) -> dict[str, str]:
        """Return ``series_key -> display_name`` from the registry."""

        return self.registry().names()

    def display_name(self, series_key: str) -> str:
        names = self.display_names()
        return names.get(series_key, series_key)

    def ensure(self) -> None:
        """Create the top-level data directories if they do not exist yet."""

        self.paths.ensure()
