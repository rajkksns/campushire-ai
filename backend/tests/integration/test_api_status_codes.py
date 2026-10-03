"""API status-code and error-contract integration tests (Task 12.6).

These exercise the full transport stack through ``TestClient`` and assert the
exact status codes and JSON error shapes from the design's REST API Contract:

* **404-over-409 precedence** (Requirements 15.4, 15.5): adding a duplicate
  skill under a *nonexistent* profile returns 404, never 409, because the
  service checks parent existence before any conflict.
* **422 field naming** (Requirements 15.2, 18.2): a validation failure names
  the single offending field in the body.
* **Generic 500 body** (Requirement 18.1): an unexpected internal error is
  reduced to a generic message with no stack trace or field detail.
* **Not-found non-disclosure** (Requirement 23.3): a 404 body carries only a
  generic message and leaks no storage internals.

The 500 case is driven by making the injected repository raise an unexpected
error, proving the catch-all handler (not FastAPI's default 500 page) owns the
response shape.
"""

from __future__ import annotations

import pytest

from app.dependencies import get_repository
from app.main import create_app


def _create_profile(client, name: str = "Asha Verma") -> str:
    """Create a profile via the API and return its id."""
    response = client.post("/profiles", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --------------------------------------------------------------------------- #
# 404-over-409 precedence (Requirements 15.4, 15.5)
# --------------------------------------------------------------------------- #
def test_duplicate_skill_under_missing_profile_is_404_not_409(client):
    """A conflict condition under a missing parent must resolve to 404 (15.5).

    Even though the request *looks* like it could be a duplicate skill (409),
    the profile does not exist, so the service raises NotFoundError first and
    the API returns 404 with the generic not-found body.
    """
    response = client.post(
        "/profiles/does-not-exist/skills",
        json={"name": "Python", "skill_type": "technical", "proficiency": 4},
    )
    assert response.status_code == 404, response.text
    body = response.json()
    assert body["error"] == "not_found"
    # Non-disclosure: generic message, nothing about tables/SQL/ids (23.3).
    assert body["message"] == "Profile not found"


def test_real_duplicate_skill_is_409(client):
    """With the profile present, a genuine case-insensitive duplicate is 409."""
    profile_id = _create_profile(client)
    first = client.post(
        f"/profiles/{profile_id}/skills",
        json={"name": "Python", "skill_type": "technical", "proficiency": 4},
    )
    assert first.status_code == 201, first.text

    # Same normalized name + type, different case/whitespace -> conflict.
    duplicate = client.post(
        f"/profiles/{profile_id}/skills",
        json={"name": "  python ", "skill_type": "technical"},
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"] == "conflict"


# --------------------------------------------------------------------------- #
# 422 field naming (Requirements 15.2, 18.2)
# --------------------------------------------------------------------------- #
def test_empty_profile_name_is_422_naming_name(client):
    """A whitespace-only profile name yields a field-named 422 for ``name``."""
    response = client.post("/profiles", json={"name": "   "})
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["field"] == "name"
    assert body["message"]  # human-readable, non-empty


def test_out_of_range_proficiency_is_422_naming_proficiency(client):
    """Proficiency above the 1..5 bound names the ``proficiency`` field (2.4)."""
    profile_id = _create_profile(client)
    response = client.post(
        f"/profiles/{profile_id}/skills",
        json={"name": "Go", "skill_type": "technical", "proficiency": 9},
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["field"] == "proficiency"


def test_empty_job_description_is_422_naming_job_description(client):
    """A blank job description names the ``job_description`` field (6.2)."""
    profile_id = _create_profile(client)
    response = client.post(
        f"/profiles/{profile_id}/analyses", json={"job_description": "   "}
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["field"] == "job_description"


# --------------------------------------------------------------------------- #
# Not-found non-disclosure (Requirements 15.4, 23.3)
# --------------------------------------------------------------------------- #
def test_missing_profile_get_is_generic_404(client):
    """Fetching an unknown profile returns a generic, non-disclosing 404."""
    response = client.get("/profiles/nope")
    assert response.status_code == 404, response.text
    body = response.json()
    assert body == {"error": "not_found", "message": "Profile not found"}


def test_missing_analysis_get_is_generic_404(client):
    """Fetching an unknown analysis returns a generic 404 (13.3)."""
    response = client.get("/analyses/nope")
    assert response.status_code == 404, response.text
    body = response.json()
    assert body["error"] == "not_found"
    # No storage internals disclosed.
    assert "Analysis" in body["message"] or body["message"] == "Resource not found"


# --------------------------------------------------------------------------- #
# Generic 500 body (Requirement 18.1)
# --------------------------------------------------------------------------- #
def test_unexpected_internal_error_is_generic_500(tmp_path):
    """An unexpected error anywhere below the router is reduced to a generic 500.

    A broken repository stub (whose ``create_profile`` raises) is injected via
    the dependency override. The catch-all handler must convert the raised
    error into the generic 500 body with NO stack trace or field detail (18.1),
    proving internals never leak to the client.
    """
    from fastapi.testclient import TestClient

    class _BrokenRepository:
        """Minimal repository stub that fails on the first write path used."""

        def create_profile(self, _record):  # noqa: ANN001 - test stub
            raise RuntimeError("boom: internal detail that must not leak")

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: _BrokenRepository()
    # Avoid the real lifespan opening a DB; the override supplies the repo.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/profiles", json={"name": "Asha"})
    app.dependency_overrides.clear()

    assert response.status_code == 500, response.text
    body = response.json()
    assert body == {
        "error": "internal_error",
        "message": "An unexpected error occurred",
    }
    # The internal RuntimeError text must not appear anywhere in the response.
    assert "boom" not in response.text
    assert "RuntimeError" not in response.text
