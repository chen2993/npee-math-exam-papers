"""Error hierarchy and HTTP status mapping."""

from __future__ import annotations

from npee_math_papers.core.errors import (
    ConflictError,
    NotFoundError,
    NpeeError,
    PackageError,
    RegistryError,
    ReleaseError,
    ValidationError,
    http_status_for,
)


def test_validation_is_400_and_valueerror() -> None:
    assert ValidationError.http_status == 400
    assert issubclass(ValidationError, ValueError)
    assert issubclass(ValidationError, NpeeError)


def test_not_found_is_a_400_subclass_with_404_status() -> None:
    assert issubclass(NotFoundError, ValidationError)
    assert NotFoundError.http_status == 404


def test_conflict_is_409() -> None:
    assert ConflictError.http_status == 409
    assert issubclass(ConflictError, NpeeError)


def test_internal_errors_are_500() -> None:
    for error_type in (PackageError, RegistryError, ReleaseError, NpeeError):
        assert error_type.http_status == 500


def test_http_status_for_maps_instances() -> None:
    assert http_status_for(NotFoundError("x")) == 404
    assert http_status_for(ConflictError("x")) == 409
    assert http_status_for(ValidationError("x")) == 400


def test_http_status_for_treats_unknown_as_500() -> None:
    assert http_status_for(RuntimeError("boom")) == 500
