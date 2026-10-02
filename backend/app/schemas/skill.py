"""Skill request/response schemas (Requirement 2).

Covers adding a technical or soft skill to a profile and the stored-record
shape returned to the client. Validation enforced at the boundary:

* ``name`` is trimmed and must be non-empty/non-whitespace (Requirement 2.1,
  2.2).
* ``skill_type`` is exactly ``"technical"`` or ``"soft"`` (Requirement 2.1,
  2.2).
* ``proficiency`` is an integer in the inclusive range 1..5 (Requirements 2.3,
  2.4); when omitted it defaults to 1 (Requirement 2.5).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import NonEmptyName, SkillType, StrictModel

__all__ = ["SkillCreate", "SkillResponse"]


class SkillCreate(StrictModel):
    """Request body for ``POST /profiles/{id}/skills`` (Requirement 2.1-2.5)."""

    name: NonEmptyName = Field(description="Skill name; trimmed, non-empty.")
    skill_type: SkillType = Field(
        description="Either 'technical' or 'soft'.",
    )
    # Default of 1 satisfies Requirement 2.5 (omitted proficiency -> 1); the
    # 1..5 bound satisfies Requirements 2.3 and 2.4.
    proficiency: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Proficiency level, integer 1..5. Defaults to 1 if omitted.",
    )


class SkillResponse(BaseModel):
    """Stored skill record returned to the client (Requirement 2.1, 2.2)."""

    id: str
    name: str
    skill_type: SkillType
    proficiency: int
