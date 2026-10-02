"""Pydantic v2 request/response schemas (boundary validation, Requirement 15).

This package defines the API's input validation and response shapes. Request
models sanitize and validate every value before it reaches a service, the
kernel, or the repository (Requirements 15.2, 18.2, 23.1); response models
define the JSON contract documented in the design's "REST API Contract".

Public models are re-exported here so callers can ``from app.schemas import
ProfileCreate`` without reaching into per-entity modules.
"""

from __future__ import annotations

from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    BreakdownItemResponse,
    MatchedSkillResponse,
    MissingSkillResponse,
    RoadmapItemResponse,
    WeakSkillResponse,
)
from app.schemas.certification import CertificationCreate, CertificationResponse
from app.schemas.common import (
    MAX_JOB_DESCRIPTION_LENGTH,
    BreakdownCategory,
    NonEmptyName,
    RoadmapCategory,
    SkillType,
    StrictModel,
)
from app.schemas.errors import (
    InternalErrorResponse,
    NotFoundErrorResponse,
    ValidationErrorResponse,
)
from app.schemas.profile import (
    ProfileCreate,
    ProfileDetailResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.resume import ResumePaste, ResumeResponse
from app.schemas.skill import SkillCreate, SkillResponse

__all__ = [
    # common
    "SkillType",
    "BreakdownCategory",
    "RoadmapCategory",
    "NonEmptyName",
    "StrictModel",
    "MAX_JOB_DESCRIPTION_LENGTH",
    # profile
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "ProfileDetailResponse",
    # skill
    "SkillCreate",
    "SkillResponse",
    # certification
    "CertificationCreate",
    "CertificationResponse",
    # project
    "ProjectCreate",
    "ProjectResponse",
    # resume
    "ResumePaste",
    "ResumeResponse",
    # analysis
    "AnalysisRequest",
    "AnalysisResponse",
    "BreakdownItemResponse",
    "MatchedSkillResponse",
    "WeakSkillResponse",
    "MissingSkillResponse",
    "RoadmapItemResponse",
    # errors
    "ValidationErrorResponse",
    "NotFoundErrorResponse",
    "InternalErrorResponse",
]
