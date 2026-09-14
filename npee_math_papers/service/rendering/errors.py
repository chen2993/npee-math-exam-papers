"""The builder's error type and its fail helper."""

from __future__ import annotations


class CompositionError(ValueError):
    """A composition could not be rendered.

    Subclasses :class:`ValueError` so existing ``except ValueError`` callers keep
    working, while remaining distinct from core validation errors.
    """


def fail(message: str) -> None:
    """Raise :class:`CompositionError` with ``message``."""

    raise CompositionError(message)
