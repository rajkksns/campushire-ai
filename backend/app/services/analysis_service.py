"""AnalysisService: orchestrate the kernel pipeline and persist results.

This service drives the pure analysis kernel in its fixed order and persists
the fully materialized result so it can be read back without recomputation
(Requirements 6.1, 7.6, 8.1, 10.12, 11.1, 11.2, 13.1, 13.2, 13.4):

    extract_required_skills(jd) ─┐
    extract_resume_skills(resume)┴─> compare(student, required)
            ─> score(compared) ─> generate(compared) ─> persist Analysis

Layering: it depends only on the pure kernel and the :class:`Repository`. It
never imports FastAPI, sqlite3, or the Pydantic schemas; the router maps the
returned dataclasses to ``AnalysisResponse``. The single wall-clock read lives
here in the adapter layer, keeping the kernel deterministic.

The assembled result is kept in plain, framework-agnostic dataclasses
(mirroring the ``AnalysisResponse`` shape) so routers can convert it trivially
and so persistence can serialize the ordered lists to JSON verbatim.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.kernel.comparator import Category, StudentSkill, compare
from app.kernel.extractor import extract_required_skills, extract_resume_skills
from app.kernel.roadmap import generate
from app.kernel.scoring import score
from app.repository.repository import AnalysisRecord, Repository
from app.services.errors import NotFoundError

__all__ = [
    "AnalysisService",
    "BreakdownLine",
    "MatchedSkill",
    "WeakSkill",
    "MissingSkill",
    "RoadmapLine",
    "AnalysisResult",
]

# Default proficiency assigned to a resume-derived skill (design): the student
# merely evidences they have the skill. The comparator takes the max on name
# collisions, so a declared proficiency always wins over this default.
_RESUME_SKILL_PROFICIENCY = 1


# --------------------------------------------------------------------------- #
# Framework-agnostic result dataclasses (mirror AnalysisResponse)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BreakdownLine:
    """One itemized score contribution (Requirement 10.10)."""

    name: str
    weight: int
    category: str  # Category value: "matched"/"weak"/"missing"
    points: int


@dataclass(frozen=True)
class MatchedSkill:
    """A matched required skill with the student's proficiency (Req 11)."""

    name: str
    weight: int
    proficiency: int


@dataclass(frozen=True)
class WeakSkill:
    """A weak required skill with the student's proficiency (Req 11.2)."""

    name: str
    weight: int
    proficiency: int


@dataclass(frozen=True)
class MissingSkill:
    """A missing required skill (Requirement 11.1)."""

    name: str
    weight: int


@dataclass(frozen=True)
class RoadmapLine:
    """One ordered roadmap item for a gap skill (Requirement 12.7)."""

    name: str
    weight: int
    category: str  # "missing"/"weak"
    priority_rank: int


@dataclass(frozen=True)
class AnalysisResult:
    """The fully materialized analysis result the router maps to a response.

    ``no_required_skills`` flags the degenerate case where extraction found no
    required skills: the kernel yields score 0 and an empty breakdown, which is
    a valid, non-error outcome (Requirements 7.6, 10.12).
    """

    id: str
    readiness_score: int
    breakdown: list[BreakdownLine] = field(default_factory=list)
    matched: list[MatchedSkill] = field(default_factory=list)
    weak: list[WeakSkill] = field(default_factory=list)
    missing: list[MissingSkill] = field(default_factory=list)
    roadmap: list[RoadmapLine] = field(default_factory=list)
    no_required_skills: bool = False


class AnalysisService:
    """Run and persist deterministic placement-readiness analyses."""

    def __init__(self, repository: Repository) -> None:
        """Store the injected repository.

        Args:
            repository: The persistence adapter (dependency injection).
        """
        self._repo = repository

    # -- run -------------------------------------------------------------- #
    def run_analysis(self, profile_id: str, job_description: str) -> AnalysisResult:
        """Run the kernel pipeline for a profile + JD and persist the result.

        Steps (Requirements 6.1, 7.6, 8.1, 10.12, 11.1, 11.2, 13.1):

        1. Verify the profile exists (404 otherwise).
        2. Load declared skills and the resume.
        3. Build the student skill set as the UNION of declared skills and
           resume-derived skills (8.1): each declared skill maps to a
           ``StudentSkill(name, proficiency)``; each resume-derived skill is
           added at the default proficiency. The comparator collapses name
           collisions to the max proficiency, so declared proficiency wins.
        4. Extract required skills from the JD.
        5. Compare, score, and generate the roadmap.
        6. Assemble the result in the response shape.
        7. If no required skills were identified, flag the result (7.6, 10.12).
        8. Persist the materialized result as JSON and return it with its new id.

        Args:
            profile_id: The profile to analyze.
            job_description: Target job-description text (validated/trimmed at
                the boundary).

        Returns:
            The materialized :class:`AnalysisResult` including the new id.

        Raises:
            NotFoundError: If the profile does not exist.
        """
        if self._repo.get_profile(profile_id) is None:
            raise NotFoundError("Profile not found")

        # Step 2: load inputs.
        declared = self._repo.list_skills(profile_id)
        resume = self._repo.get_resume(profile_id)

        # Step 3: union of declared + resume-derived skills (8.1).
        student_skills = [
            StudentSkill(name=s.normalized, proficiency=s.proficiency)
            for s in declared
        ]
        if resume is not None:
            for name in extract_resume_skills(resume.content):
                student_skills.append(
                    StudentSkill(name=name, proficiency=_RESUME_SKILL_PROFICIENCY)
                )

        # Steps 4-5: run the kernel pipeline.
        required = extract_required_skills(job_description)
        compared = compare(student_skills, required)
        score_result = score(compared)
        roadmap = generate(compared)

        # Step 6: assemble the response-shaped result.
        breakdown = [
            BreakdownLine(
                name=item.name,
                weight=item.weight,
                category=item.category.value,
                points=item.points,
            )
            for item in score_result.breakdown
        ]

        matched: list[MatchedSkill] = []
        weak: list[WeakSkill] = []
        missing: list[MissingSkill] = []
        for cs in compared:
            if cs.category is Category.MATCHED:
                matched.append(
                    MatchedSkill(
                        name=cs.name,
                        weight=cs.weight,
                        proficiency=cs.proficiency if cs.proficiency is not None else 0,
                    )
                )
            elif cs.category is Category.WEAK:
                weak.append(
                    WeakSkill(
                        name=cs.name,
                        weight=cs.weight,
                        proficiency=cs.proficiency if cs.proficiency is not None else 0,
                    )
                )
            else:  # Category.MISSING
                missing.append(MissingSkill(name=cs.name, weight=cs.weight))

        roadmap_lines = [
            RoadmapLine(
                name=item.name,
                weight=item.weight,
                category=item.category.value,
                priority_rank=item.priority_rank,
            )
            for item in roadmap
        ]

        analysis_id = uuid4().hex
        result = AnalysisResult(
            id=analysis_id,
            readiness_score=score_result.readiness_score,
            breakdown=breakdown,
            matched=matched,
            weak=weak,
            missing=missing,
            roadmap=roadmap_lines,
            # Step 7: empty extraction is a valid, flagged outcome (7.6, 10.12).
            no_required_skills=len(required) == 0,
        )

        # Step 8: persist the fully materialized result (13.1).
        self._repo.create_analysis(
            AnalysisRecord(
                id=analysis_id,
                profile_id=profile_id,
                job_description=job_description,
                readiness_score=result.readiness_score,
                breakdown_json=_dump(result.breakdown),
                categorization_json=_dump_categorization(result),
                roadmap_json=_dump(result.roadmap),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        return result

    # -- retrieve --------------------------------------------------------- #
    def get_analysis(self, analysis_id: str) -> AnalysisResult:
        """Return a persisted analysis by id (Requirements 13.2, 13.3).

        Deserializes the stored JSON columns back into the result shape without
        recomputing the pipeline (the stored result is authoritative).

        Args:
            analysis_id: The analysis to fetch.

        Returns:
            The materialized :class:`AnalysisResult`.

        Raises:
            NotFoundError: If the analysis does not exist (404, 13.3).
        """
        record = self._repo.get_analysis(analysis_id)
        if record is None:
            raise NotFoundError("Analysis not found")
        return _record_to_result(record)

    # -- list ------------------------------------------------------------- #
    def list_analyses(self, profile_id: str) -> list[AnalysisResult]:
        """Return a profile's analyses, newest first (Requirement 13.4).

        Verifies the profile exists first (404 otherwise), then maps each
        persisted record back to a result.

        Args:
            profile_id: The profile whose analyses to list.

        Returns:
            A list of :class:`AnalysisResult`, newest first (repository order).

        Raises:
            NotFoundError: If the profile does not exist.
        """
        if self._repo.get_profile(profile_id) is None:
            raise NotFoundError("Profile not found")
        return [_record_to_result(r) for r in self._repo.list_analyses(profile_id)]


# --------------------------------------------------------------------------- #
# JSON (de)serialization helpers
#
# Lists are dumped in their already-deterministic kernel order; we never
# sort_keys so the ordered lists are preserved verbatim (the dataclass field
# order within each item is stable).
# --------------------------------------------------------------------------- #
def _dump(items: list) -> str:
    """Serialize a list of dataclass items to a JSON string, order-preserving."""
    return json.dumps([asdict(item) for item in items])


def _dump_categorization(result: AnalysisResult) -> str:
    """Serialize the matched/weak/missing groups to one JSON object."""
    return json.dumps(
        {
            "matched": [asdict(m) for m in result.matched],
            "weak": [asdict(w) for w in result.weak],
            "missing": [asdict(m) for m in result.missing],
        }
    )


def _record_to_result(record: AnalysisRecord) -> AnalysisResult:
    """Rebuild an :class:`AnalysisResult` from a persisted :class:`AnalysisRecord`."""
    breakdown = [
        BreakdownLine(**item) for item in json.loads(record.breakdown_json)
    ]
    categorization = json.loads(record.categorization_json)
    matched = [MatchedSkill(**m) for m in categorization.get("matched", [])]
    weak = [WeakSkill(**w) for w in categorization.get("weak", [])]
    missing = [MissingSkill(**m) for m in categorization.get("missing", [])]
    roadmap = [RoadmapLine(**item) for item in json.loads(record.roadmap_json)]

    return AnalysisResult(
        id=record.id,
        readiness_score=record.readiness_score,
        breakdown=breakdown,
        matched=matched,
        weak=weak,
        missing=missing,
        roadmap=roadmap,
        no_required_skills=len(breakdown) == 0,
    )
