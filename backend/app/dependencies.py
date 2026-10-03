"""Application dependency wiring (I/O adapter composition root).

This module is the single place where the long-lived :class:`Repository` and
the service objects are constructed and handed to the FastAPI routers via
``Depends``. Keeping construction here (rather than in each router) preserves
the layered dependency direction — routers depend on services, services depend
on the kernel and the repository — and makes the whole graph trivial to swap in
tests (override :func:`get_repository`).

Lifecycle: :func:`init_state` is called once on startup (see ``app.main``). It
opens the SQLite connection, initializes the schema (Requirement 16.1), and
stashes the repository on ``app.state`` so a single connection is reused for the
process. :func:`shutdown_state` closes it. The per-request dependency functions
read the already-constructed repository back off ``app.state``; they never open
their own connection.

The database path comes from the ``DATABASE_PATH`` environment variable,
defaulting to a file under the backend directory. Reading the environment here
(an adapter concern) keeps the kernel free of environment reads.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, Request

from app.repository.repository import Repository
from app.services.analysis_service import AnalysisService
from app.services.profile_service import ProfileService
from app.services.resume_service import ResumeService

__all__ = [
    "init_state",
    "shutdown_state",
    "get_repository",
    "get_profile_service",
    "get_resume_service",
    "get_analysis_service",
    "resolve_database_path",
]

# Default database location: a file next to the backend app so data persists
# across restarts when the directory is a mounted volume (Requirement 16.2).
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "campushire.db")


def resolve_database_path() -> str:
    """Return the configured database path.

    Reads ``DATABASE_PATH`` from the environment (an adapter-layer concern),
    falling back to a file under the backend directory. Docker Compose points
    this at a named volume so data survives restarts (Requirements 16.2, 19.3).
    """
    return os.environ.get("DATABASE_PATH", _DEFAULT_DB_PATH)


def init_state(app) -> Repository:  # noqa: ANN001 - FastAPI app, avoid import cycle
    """Open the repository, initialize the schema, and stash it on app state.

    Called once on startup. Returns the repository so callers/tests can hold a
    reference. The schema initialization is idempotent (Requirement 16.1).
    """
    repository = Repository(resolve_database_path())
    repository.initialize_schema()
    app.state.repository = repository
    return repository


def shutdown_state(app) -> None:  # noqa: ANN001 - FastAPI app, avoid import cycle
    """Close the repository connection on shutdown, if one was opened."""
    repository: Repository | None = getattr(app.state, "repository", None)
    if repository is not None:
        repository.close()
        app.state.repository = None


# --------------------------------------------------------------------------- #
# Per-request dependency providers
# --------------------------------------------------------------------------- #
def get_repository(request: Request) -> Repository:
    """Return the process-wide repository stored on ``app.state``.

    The repository is constructed once in :func:`init_state`; this provider
    simply hands it to routers/services so a single SQLite connection is reused.
    """
    return request.app.state.repository


def get_profile_service(
    repository: Repository = Depends(get_repository),
) -> ProfileService:
    """Provide a :class:`ProfileService` bound to the shared repository."""
    return ProfileService(repository)


def get_resume_service(
    repository: Repository = Depends(get_repository),
) -> ResumeService:
    """Provide a :class:`ResumeService` bound to the shared repository."""
    return ResumeService(repository)


def get_analysis_service(
    repository: Repository = Depends(get_repository),
) -> AnalysisService:
    """Provide an :class:`AnalysisService` bound to the shared repository."""
    return AnalysisService(repository)
