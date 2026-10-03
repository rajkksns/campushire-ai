"""FastAPI application bootstrap and global error handling (Task 12.1).

This is the composition root for the HTTP transport layer. It:

* creates the :class:`fastapi.FastAPI` app and wires the routers,
* opens the SQLite repository and initializes the schema on startup, closing
  it on shutdown (Requirement 16.1, via :mod:`app.dependencies`),
* installs global exception handlers that translate the framework-agnostic
  service exceptions and Pydantic validation failures into the exact JSON
  error shapes and status codes defined in the design's REST API Contract.

Error-handling contract (design "Sample payloads"; Requirements 15.1-15.5,
18.1, 18.2, 23.3):

* **422 validation** — body names the single failing field
  (``{"error":"validation_error","field":...,"message":...}``). Produced both
  by Pydantic request-body validation (``RequestValidationError``) and by a
  service-raised :class:`ValidationError`.
* **404 not found** — generic message disclosing no storage internals.
* **409 conflict** — e.g. a case-insensitive duplicate skill.
* **415 / 413** — resume media-type / size guards.
* **500 internal** — a generic message with no stack trace or field detail; any
  unhandled exception is caught and reduced to this shape so internals never
  leak (18.1).

The **404-over-409 precedence** (Requirement 15.5) is enforced inside the
services (parent-existence is checked before any conflict), not here; these
handlers simply map whichever exception the service raised.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.dependencies import init_state, shutdown_state
from app.routers import analysis, health, profile, resume
from app.services.errors import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaError,
    ValidationError,
)

__all__ = ["app", "create_app"]


# --------------------------------------------------------------------------- #
# Error-body builders (single source of each JSON shape)
# --------------------------------------------------------------------------- #
def _validation_body(field: str, message: str) -> dict[str, str]:
    """422 body naming the failing field (Requirements 15.2, 18.2)."""
    return {"error": "validation_error", "field": field, "message": message}


def _not_found_body(message: str = "Resource not found") -> dict[str, str]:
    """404 body with a generic, non-disclosing message (Requirement 23.3)."""
    return {"error": "not_found", "message": message}


def _conflict_body(message: str) -> dict[str, str]:
    """409 body for a uniqueness/business conflict (Requirement 2.6)."""
    return {"error": "conflict", "message": message}


def _unsupported_media_body(message: str) -> dict[str, str]:
    """415 body for an unsupported resume media type (Requirement 5.4)."""
    return {"error": "unsupported_media_type", "message": message}


def _payload_too_large_body(message: str) -> dict[str, str]:
    """413 body for an oversized resume upload (Requirement 5.5)."""
    return {"error": "payload_too_large", "message": message}


def _internal_body() -> dict[str, str]:
    """500 body: generic, no stack trace or field detail (Requirement 18.1)."""
    return {"error": "internal_error", "message": "An unexpected error occurred"}


# --------------------------------------------------------------------------- #
# Field extraction for Pydantic request-validation errors
# --------------------------------------------------------------------------- #
def _field_from_validation_error(exc: RequestValidationError) -> tuple[str, str]:
    """Reduce a Pydantic ``RequestValidationError`` to (field, message).

    FastAPI reports a list of errors, each with a ``loc`` tuple like
    ``("body", "proficiency")``. The design's 422 shape names a single failing
    field, so we take the first error, use the last meaningful path segment as
    the field name (skipping the ``"body"``/``"query"`` prefix), and surface its
    message. This keeps the 422 body stable and field-named (18.2) without
    leaking Pydantic's internal error structure.
    """
    errors = exc.errors()
    if not errors:
        return "request", "Invalid request"

    first = errors[0]
    loc = [str(part) for part in first.get("loc", ()) if part not in ("body", "query", "path")]
    field = loc[-1] if loc else "request"
    message = first.get("msg", "Invalid value")
    # Pydantic prefixes value errors with "Value error, "; strip it so the
    # message reads cleanly to a client.
    message = message.removeprefix("Value error, ")
    return field, message


# --------------------------------------------------------------------------- #
# Exception handler registration
# --------------------------------------------------------------------------- #
def _register_exception_handlers(app: FastAPI) -> None:
    """Install all global exception handlers on ``app``."""

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Map Pydantic request-body validation to a field-named 422 (18.2)."""
        field, message = _field_from_validation_error(exc)
        return JSONResponse(status_code=422, content=_validation_body(field, message))

    @app.exception_handler(ValidationError)
    async def _handle_service_validation(
        _request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Map a service-raised validation failure to a field-named 422."""
        return JSONResponse(
            status_code=422, content=_validation_body(exc.field, exc.message)
        )

    @app.exception_handler(NotFoundError)
    async def _handle_not_found(
        _request: Request, exc: NotFoundError
    ) -> JSONResponse:
        """Map a missing resource to a generic 404 (Requirements 15.4, 23.3)."""
        return JSONResponse(status_code=404, content=_not_found_body(exc.message))

    @app.exception_handler(ConflictError)
    async def _handle_conflict(
        _request: Request, exc: ConflictError
    ) -> JSONResponse:
        """Map a uniqueness/business conflict to 409 (Requirement 2.6)."""
        return JSONResponse(status_code=409, content=_conflict_body(exc.message))

    @app.exception_handler(UnsupportedMediaError)
    async def _handle_unsupported_media(
        _request: Request, exc: UnsupportedMediaError
    ) -> JSONResponse:
        """Map an unsupported resume media type to 415 (Requirement 5.4)."""
        return JSONResponse(
            status_code=415, content=_unsupported_media_body(exc.message)
        )

    @app.exception_handler(PayloadTooLargeError)
    async def _handle_payload_too_large(
        _request: Request, exc: PayloadTooLargeError
    ) -> JSONResponse:
        """Map an oversized resume upload to 413 (Requirement 5.5)."""
        return JSONResponse(
            status_code=413, content=_payload_too_large_body(exc.message)
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        """Catch-all: reduce any unhandled error to a generic 500 (18.1).

        No stack trace, exception type, or field detail is echoed to the
        client, so persistence/internal details never leak (Requirement 23.3).
        """
        return JSONResponse(status_code=500, content=_internal_body())


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Open the repository + schema on startup, close it on shutdown (16.1)."""
    init_state(app)
    try:
        yield
    finally:
        shutdown_state(app)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Factory form so tests can construct an isolated app (optionally with an
    overridden repository dependency) without import-time side effects.
    """
    app = FastAPI(
        title="CampusHire AI",
        version="0.1.0",
        description=(
            "Placement-readiness and skill-gap analyzer. Deterministic analysis "
            "kernel behind a thin FastAPI transport layer."
        ),
        lifespan=_lifespan,
    )

    _register_exception_handlers(app)

    # Router wiring. Health has no prefix; the resource routers carry their own
    # paths so the design's REST contract is expressed in one place each.
    app.include_router(health.router)
    app.include_router(profile.router)
    app.include_router(resume.router)
    app.include_router(analysis.router)

    return app


# Module-level app for ``uvicorn app.main:app``.
app = create_app()
