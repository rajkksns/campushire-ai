"""Shared fixtures for API-level integration tests (Task 12.6-12.8).

These fixtures build the real FastAPI app from :func:`app.main.create_app` and
exercise it through Starlette's ``TestClient`` (backed by ``httpx``), so the
tests cover the full transport stack: routing, request-body validation, the
global exception handlers, the service layer, the pure kernel, and the
parameterized SQLite repository.

Isolation strategy: instead of relying on the app's env-driven lifespan DB
path, each test gets its own on-disk SQLite file under pytest's ``tmp_path`` and
the ``get_repository`` dependency is overridden to return a single
:class:`Repository` bound to that file. The dependency override replaces the
app's startup/shutdown repository wiring, giving every test a clean, private
database with zero cross-test leakage. An on-disk file (not ``:memory:``) is
used so the connection is safely shared across the TestClient's worker thread.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_repository
from app.main import create_app
from app.repository.repository import Repository


@pytest.fixture()
def repository(tmp_path) -> Iterator[Repository]:
    """Provide a fresh, schema-initialized repository on a temp-file database.

    Yielding the repository (rather than just a path) lets a test seed or
    inspect persistence directly when it needs to, while the API still talks to
    the very same connection through the dependency override.
    """
    repo = Repository(str(tmp_path / "campushire_api_test.db"))
    repo.initialize_schema()
    try:
        yield repo
    finally:
        repo.close()


@pytest.fixture()
def client(repository: Repository) -> Iterator[TestClient]:
    """A ``TestClient`` whose ``get_repository`` resolves to the test repo.

    The override is installed before the client is created and cleared on
    teardown so the app object (module-level in ``app.main`` is NOT used here;
    we build a fresh one) carries no state between tests.
    """
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
