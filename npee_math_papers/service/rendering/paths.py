"""Path resolution for the builder.

Two different roots are in play, and confusing them is a security bug:

* the **repository root** — ``composition.output.directory`` and every other
  repository-relative setting must stay inside it;
* the **composition package root** — a self-contained directory holding
  ``composition.json`` plus its cover, hooks and assets, which must stay inside it.

Both are resolved here so the checks exist once.
"""

from __future__ import annotations

from pathlib import Path

from npee_math_papers.service.rendering.errors import fail

#: Repository root: this file lives at ``…/service/rendering/paths.py``.
ROOT = Path(__file__).resolve().parents[3]


def repository_path(value: str | Path, field: str) -> Path:
    """Resolve a repository-relative path, refusing escapes and absolute paths."""

    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        if any(part in {"", ".", ".."} for part in path.parts):
            fail(f"{field} must be a repository-relative path without '.', '..' or repeated separators")
        resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        fail(f"{field} resolves outside the repository: {value!s}")
    return resolved


def package_path(value: str | Path, package_root: Path, field: str) -> Path:
    """Resolve an asset path within one self-contained composition package."""

    raw = Path(value)
    if (
        not str(value)
        or raw.is_absolute()
        or "\\" in str(value)
        or any(part in {"", ".", ".."} for part in raw.parts)
    ):
        fail(f"{field} must be a safe package-relative path")
    resolved = (package_root / raw).resolve()
    try:
        resolved.relative_to(package_root)
    except ValueError:
        fail(f"{field} resolves outside the composition package: {value!s}")
    return resolved


def package_tex_path(value: str | Path, package_root: Path, field: str) -> Path:
    """Resolve a hook or body fragment stored next to ``composition.json``."""

    resolved = package_path(value, package_root, field)
    if resolved.parent != package_root or resolved.suffix.lower() != ".tex":
        fail(f"{field} must name a .tex file next to composition.json")
    return resolved


def relative_tex_path(path: Path) -> str:
    """Return ``path`` relative to the repository root, POSIX separated."""

    return path.relative_to(ROOT).as_posix()
