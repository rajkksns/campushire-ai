"""Student-profile request/response schemas (Requirement 1).

Create and update both carry a non-empty, trimmed ``name`` (Requirements 1.1,
1.2, 1.5). The create response returns the generated identifier and timestamp
(1.1); the detail response additionally embeds the profile's skills,
certifications, and projects (1.3).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.certification import CertificationResponse
from app.schemas.common import NonEmptyName, StrictModel
from app.schemas.project import ProjectResponse
from app.schemas.skill import SkillResponse

__all__ = [
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "ProfileDetailResponse",
]


class ProfileCreate(StrictModel):
    """Request body for ``POST /profiles`` (Requirements 1.1, 1.2)."""

    name: NonEmptyName = Field(description="Profile name; trimmed, non-empty.")


class ProfileUpdate(StrictModel):
    """Request body for ``PUT /profiles/{id}`` (Requirement 1.5)."""

    name: NonEmptyName = Field(description="New profile name; trimmed, non-empty.")


class ProfileResponse(BaseModel):
    """Create/update response: identity and creation timestamp (1.1, 1.5)."""

    id: str
    name: str
    created_at: str


class ProfileDetailResponse(BaseModel):
    """Full profile detail with owned collections (Requirement 1.3)."""

    id: str
    name: str
    created_at: str
    skills: list[SkillResponse] = Field(default_factory=list)
    certifications: list[CertificationResponse] = Field(default_factory=list)
    projects: list[ProjectResponse] = Field(default_factory=list)
