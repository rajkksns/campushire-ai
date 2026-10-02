"""Certification request/response schemas (Requirement 3).

Adding a certification requires a non-empty, trimmed name (Requirements 3.1,
3.2). The response echoes the stored record.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import NonEmptyName, StrictModel

__all__ = ["CertificationCreate", "CertificationResponse"]


class CertificationCreate(StrictModel):
    """Request body for ``POST /profiles/{id}/certifications`` (3.1, 3.2)."""

    name: NonEmptyName = Field(
        description="Certification name; trimmed, non-empty.",
    )


class CertificationResponse(BaseModel):
    """Stored certification record returned to the client (Requirement 3.1)."""

    id: str
    name: str
