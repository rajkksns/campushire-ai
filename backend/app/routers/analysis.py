"""Analysis router (Task 12.5, Requirements 6, 11, 13).

Thin HTTP transport over :class:`AnalysisService`, which orchestrates the pure
kernel pipeline (extractor -> comparator -> scoring -> roadmap) and persists the
fully materialized result. These handlers only validate the request, invoke the
service, and map the returned :class:`AnalysisResult` dataclass to
:class:`AnalysisResponse`.

Endpoints and status codes (design REST API Contract):

* ``POST /profiles/{id}/analyses`` -> **201**; **404** if the profile is
  missing; **422** if the job description is empty or exceeds 20000 chars
  (enforced in :class:`AnalysisRequest`).
* ``GET /analyses/{id}`` -> **200**; **404** if the analysis does not exist
  (13.2, 13.3).
* ``GET /profiles/{id}/analyses`` -> **200** (list, newest first); **404** if
  the profile is missing (13.4).

An empty extraction result is a valid, non-error outcome: the service returns a
score-0 analysis flagged ``no_required_skills`` (Requirements 7.6, 10.12), still
persisted and returned as 201.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import get_analysis_service
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    BreakdownItemResponse,
    MatchedSkillResponse,
    MissingSkillResponse,
    RoadmapItemResponse,
    WeakSkillResponse,
)
from app.services.analysis_service import AnalysisResult, AnalysisService

__all__ = ["router"]

router = APIRouter(tags=["analysis"])


def _to_response(result: AnalysisResult) -> AnalysisResponse:
    """Map a service :class:`AnalysisResult` to the API response schema.

    The ordered lists are copied verbatim so the kernel's deterministic
    ordering (breakdown, matched/weak/missing, roadmap) is preserved in the
    JSON response (Requirements 10.10, 11.1, 11.2, 12.7).
    """
    return AnalysisResponse(
        id=result.id,
        readiness_score=result.readiness_score,
        breakdown=[
            BreakdownItemResponse(
                name=b.name, weight=b.weight, category=b.category, points=b.points
            )
            for b in result.breakdown
        ],
        matched=[
            MatchedSkillResponse(
                name=m.name, weight=m.weight, proficiency=m.proficiency
            )
            for m in result.matched
        ],
        weak=[
            WeakSkillResponse(
                name=w.name, weight=w.weight, proficiency=w.proficiency
            )
            for w in result.weak
        ],
        missing=[
            MissingSkillResponse(name=m.name, weight=m.weight)
            for m in result.missing
        ],
        roadmap=[
            RoadmapItemResponse(
                name=r.name,
                weight=r.weight,
                category=r.category,
                priority_rank=r.priority_rank,
            )
            for r in result.roadmap
        ],
    )


@router.post(
    "/profiles/{profile_id}/analyses",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(
    profile_id: str,
    body: AnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Run and persist an analysis (Requirements 6.1-6.3, 8-13) -> 201/404/422."""
    result = service.run_analysis(profile_id, body.job_description)
    return _to_response(result)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Return a persisted analysis (Requirements 13.2, 13.3) -> 200/404."""
    result = service.get_analysis(analysis_id)
    return _to_response(result)


@router.get(
    "/profiles/{profile_id}/analyses",
    response_model=list[AnalysisResponse],
)
async def list_analyses(
    profile_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> list[AnalysisResponse]:
    """List a profile's analyses, newest first (Requirement 13.4) -> 200/404."""
    results = service.list_analyses(profile_id)
    return [_to_response(r) for r in results]
