"""Shared error types.

A single error hierarchy keeps every tool's exit behavior predictable: repository
scripts catch :class:`ValidationError` and print a message with exit code 2, while
services translate the same error into an HTTP status.

The status mapping lives here so both adapters (HTTP and MCP) agree:

======================  ======  ===============================================
Error                   Status  Meaning
======================  ======  ===============================================
ValidationError         400     malformed request or invalid content
NotFoundError           404     the requested record does not exist
ConflictError           409     the request conflicts with current state
RegistryError           500     the registry file is missing, malformed or stale
ReleaseError            500     the release manifest is missing or stale
PackageError            500     a package file could not be read or written
NpeeError               500     any other shared-core failure
======================  ======  ===============================================
"""

from __future__ import annotations


class NpeeError(Exception):
    """Base class for all shared-core failures."""

    #: HTTP status adapters should use when this error reaches a request boundary.
    http_status = 500


class ValidationError(NpeeError, ValueError):
    """A user-facing, actionable validation failure.

    Messages must always name the offending field and the required shape so the
    caller never has to read the implementation to fix the input.
    """

    http_status = 400


class NotFoundError(ValidationError):
    """A requested record (paper, question, capture…) does not exist."""

    http_status = 404


class ConflictError(NpeeError):
    """The request conflicts with current state, e.g. overwriting without ``replace``."""

    http_status = 409


class PackageError(NpeeError):
    """A series package file could not be read or written safely."""


class RegistryError(NpeeError):
    """The catalog registry is missing, malformed or internally inconsistent."""


class ReleaseError(NpeeError):
    """A release manifest is missing, stale or does not match the working tree."""


def http_status_for(error: BaseException) -> int:
    """Return the HTTP status that best describes ``error``.

    One helper keeps the HTTP adapter from re-deriving the mapping; any error
    outside the hierarchy is treated as an internal failure.
    """

    if isinstance(error, NpeeError):
        return error.http_status
    return 500
