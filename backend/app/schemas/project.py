"""Academic-project request/response schemas (Requirement 4).

Adding a project requires a non-empty, trimmed ``title`` (Requirements 4.1,
4.2); the ``description`` is optional and stored as given when present
(Requirement 4.3).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import NonEmptyName, StrictModel

__all__ = ["ProjectCreate", "ProjectResponse"]


class ProjectCreate(StrictModel):
    """Request body for ``POST /profiles/{id}/projects`` (4.1-4.3)."""

    title: NonEmptyName = Field(description="Project title; trimmed, non-empty.")
    description: str | None = Field(
        default=None,
        description="Optional project description, stored as provided (4.3).",
    )


class ProjectResponse(BaseModel):
    """Stored project record returned to the client (Requirement 4.1)."""

    id: str
    title: str
    description: str | None = None
