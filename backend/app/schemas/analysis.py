"""Analysis request/response schemas (Requirements 6, 10-13).

The request carries the target job description, validated non-empty (6.2) and
at most 20000 characters after trimming (6.3). The response mirrors the fully
materialized analysis result shape from the design "REST API Contract":
readiness score, itemized breakdown, matched/weak/missing groups, and the
ordered roadmap (Requirements 10.10, 11.1, 11.2, 12.7).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import (
    MAX_JOB_DESCRIPTION_LENGTH,
    BreakdownCategory,
    RoadmapCategory,
    StrictModel,
)

__all__ = [
    "AnalysisRequest",
    "BreakdownItemResponse",
    "MatchedSkillResponse",
    "WeakSkillResponse",
    "MissingSkillResponse",
    "RoadmapItemResponse",
    "AnalysisResponse",
]


class AnalysisRequest(StrictModel):
    """Request body for ``POST /profiles/{id}/analyses`` (6.1-6.3)."""

    job_description: str = Field(
        description="Target job-description text; non-empty, <= 20000 chars after trim.",
    )

    @field_validator("job_description")
    @classmethod
    def _validate_job_description(cls, value: str) -> str:
        """Reject blank text (6.2); enforce the 20000-char cap after trim (6.3).

        Trimming happens first so a whitespace-only description is rejected and
        the length bound is measured against the meaningful content. The
        trimmed text is returned for downstream extraction.
        """
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("job_description must not be empty or whitespace-only")
        if len(trimmed) > MAX_JOB_DESCRIPTION_LENGTH:
            raise ValueError(
                f"job_description must be at most {MAX_JOB_DESCRIPTION_LENGTH} characters"
            )
        return trimmed


class BreakdownItemResponse(BaseModel):
    """One itemized score contribution (Requirement 10.10)."""

    name: str
    weight: int
    category: BreakdownCategory
    points: int


class MatchedSkillResponse(BaseModel):
    """A matched required skill with the student's proficiency (Requirement 11)."""

    name: str
    weight: int
    proficiency: int


class WeakSkillResponse(BaseModel):
    """A weak required skill with the student's proficiency (Requirement 11.2)."""

    name: str
    weight: int
    proficiency: int


class MissingSkillResponse(BaseModel):
    """A missing required skill (Requirement 11.1)."""

    name: str
    weight: int


class RoadmapItemResponse(BaseModel):
    """One ordered roadmap item for a gap skill (Requirement 12.7)."""

    name: str
    weight: int
    category: RoadmapCategory
    priority_rank: int


class AnalysisResponse(BaseModel):
    """Fully materialized analysis result (Requirements 10.10, 11.1, 11.2, 12.7)."""

    id: str
    readiness_score: int = Field(ge=0, le=100)
    breakdown: list[BreakdownItemResponse] = Field(default_factory=list)
    matched: list[MatchedSkillResponse] = Field(default_factory=list)
    weak: list[WeakSkillResponse] = Field(default_factory=list)
    missing: list[MissingSkillResponse] = Field(default_factory=list)
    roadmap: list[RoadmapItemResponse] = Field(default_factory=list)
