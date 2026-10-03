"""Profile / skills / certifications / projects router (Task 12.3).

Thin HTTP transport over :class:`ProfileService`. Each endpoint validates its
request body with the Pydantic schemas (field-named 422 on failure, handled
globally in :mod:`app.main`), delegates the business rule to the service, and
maps the returned record dataclass to a response schema.

Status codes follow the design's REST API Contract (Requirement 15.4):

* ``POST`` create endpoints return **201**.
* ``GET`` / ``PUT`` / ``DELETE`` success return **200**.
* A missing parent/child resource surfaces as **404** (service
  :class:`NotFoundError`), a case-insensitive duplicate skill as **409**
  (service :class:`ConflictError`), and schema violations as **422**.

The **404-over-409 precedence** (Requirement 15.5) is guaranteed by the service
(it checks parent existence before any conflict), so these handlers never need
to order the checks themselves — they just let the service raise.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import get_profile_service
from app.schemas.certification import CertificationCreate, CertificationResponse
from app.schemas.profile import (
    ProfileCreate,
    ProfileDetailResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.skill import SkillCreate, SkillResponse
from app.services.profile_service import ProfileService

__all__ = ["router"]

router = APIRouter(tags=["profile"])


# --------------------------------------------------------------------------- #
# Profiles
# --------------------------------------------------------------------------- #
@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    body: ProfileCreate,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Create a profile (Requirements 1.1, 1.2) -> 201."""
    record = service.create_profile(body.name)
    return ProfileResponse(
        id=record.id, name=record.name, created_at=record.created_at
    )


@router.get("/profiles/{profile_id}", response_model=ProfileDetailResponse)
async def get_profile(
    profile_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileDetailResponse:
    """Return a profile with its skills, certs, and projects (1.3) -> 200/404."""
    profile, skills, certs, projects = service.get_profile_detail(profile_id)
    return ProfileDetailResponse(
        id=profile.id,
        name=profile.name,
        created_at=profile.created_at,
        skills=[
            SkillResponse(
                id=s.id,
                name=s.name,
                skill_type=s.skill_type,
                proficiency=s.proficiency,
            )
            for s in skills
        ],
        certifications=[
            CertificationResponse(id=c.id, name=c.name) for c in certs
        ],
        projects=[
            ProjectResponse(id=p.id, title=p.title, description=p.description)
            for p in projects
        ],
    )


@router.put("/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: str,
    body: ProfileUpdate,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Rename a profile (Requirement 1.5) -> 200/404/422."""
    record = service.update_profile_name(profile_id, body.name)
    return ProfileResponse(
        id=record.id, name=record.name, created_at=record.created_at
    )


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> dict[str, str]:
    """Delete a profile; owned rows cascade (Requirement 16.3) -> 200/404."""
    service.delete_profile(profile_id)
    return {"status": "deleted"}


# --------------------------------------------------------------------------- #
# Skills
# --------------------------------------------------------------------------- #
@router.post(
    "/profiles/{profile_id}/skills",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_skill(
    profile_id: str,
    body: SkillCreate,
    service: ProfileService = Depends(get_profile_service),
) -> SkillResponse:
    """Add a technical/soft skill (2.1-2.6) -> 201/404/409/422."""
    record = service.add_skill(
        profile_id=profile_id,
        name=body.name,
        skill_type=body.skill_type,
        proficiency=body.proficiency,
    )
    return SkillResponse(
        id=record.id,
        name=record.name,
        skill_type=record.skill_type,
        proficiency=record.proficiency,
    )


@router.delete("/profiles/{profile_id}/skills/{skill_id}")
async def remove_skill(
    profile_id: str,
    skill_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> dict[str, str]:
    """Remove a skill (Requirement 2.7) -> 200/404."""
    service.remove_skill(profile_id, skill_id)
    return {"status": "deleted"}


# --------------------------------------------------------------------------- #
# Certifications
# --------------------------------------------------------------------------- #
@router.post(
    "/profiles/{profile_id}/certifications",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_certification(
    profile_id: str,
    body: CertificationCreate,
    service: ProfileService = Depends(get_profile_service),
) -> CertificationResponse:
    """Add a certification (3.1, 3.2) -> 201/404/422."""
    record = service.add_certification(profile_id, body.name)
    return CertificationResponse(id=record.id, name=record.name)


@router.delete("/profiles/{profile_id}/certifications/{cert_id}")
async def remove_certification(
    profile_id: str,
    cert_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> dict[str, str]:
    """Remove a certification (Requirement 3.3) -> 200/404."""
    service.remove_certification(profile_id, cert_id)
    return {"status": "deleted"}


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #
@router.post(
    "/profiles/{profile_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project(
    profile_id: str,
    body: ProjectCreate,
    service: ProfileService = Depends(get_profile_service),
) -> ProjectResponse:
    """Add an academic project (4.1-4.3) -> 201/404/422."""
    record = service.add_project(profile_id, body.title, body.description)
    return ProjectResponse(
        id=record.id, title=record.title, description=record.description
    )


@router.delete("/profiles/{profile_id}/projects/{project_id}")
async def remove_project(
    profile_id: str,
    project_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> dict[str, str]:
    """Remove an academic project (Requirement 4.4) -> 200/404."""
    service.remove_project(profile_id, project_id)
    return {"status": "deleted"}
