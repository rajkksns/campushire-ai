"""Shared schema primitives and validators (boundary input sanitization).

These helpers are reused across the per-entity schema modules so that every
request model enforces the same canonical validation rules at the API boundary
before any value reaches a service, the kernel, or the repository
(Requirements 15.2, 18.2, 23.1).

The module is dependency-light and I/O-free: it imports only Pydantic and the
standard library. It deliberately does NOT import ``app.kernel`` — schemas
redefine the small set of literal category/type values locally so the
validation layer stays decoupled from the analysis kernel.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

__all__ = [
    "SkillType",
    "BreakdownCategory",
    "RoadmapCategory",
    "NonEmptyName",
    "StrictModel",
    "MAX_JOB_DESCRIPTION_LENGTH",
]

# ``skill_type`` must be exactly one of these two values (Requirement 2.1, 2.2).
SkillType = Literal["technical", "soft"]

# Category string values mirror the kernel's ``Category`` enum
# ("matched"/"weak"/"missing") but are redefined locally so schemas never
# import the kernel (keeps the boundary layer I/O-free and dependency-light).
BreakdownCategory = Literal["matched", "weak", "missing"]

# Roadmap items only ever cover gaps, so only "missing"/"weak" are valid
# (Requirement 12.1, 12.6).
RoadmapCategory = Literal["missing", "weak"]

# Maximum accepted job-description length after trimming (Requirement 6.3).
MAX_JOB_DESCRIPTION_LENGTH = 20000


def _require_non_empty_trimmed(value: str) -> str:
    """Trim surrounding whitespace, then reject empty/whitespace-only values.

    Trimming happens FIRST so that a value consisting solely of whitespace is
    rejected (it becomes the empty string after the strip). The trimmed value
    is what gets stored, matching the normalization the persistence layer
    expects (Requirements 1.2, 2.3, 3.2, 4.2).
    """
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("must not be empty or whitespace-only")
    return trimmed


# Reusable annotated type for required names/titles: strips whitespace and
# rejects empty/whitespace-only input, storing the trimmed value.
NonEmptyName = Annotated[str, AfterValidator(_require_non_empty_trimmed)]


class StrictModel(BaseModel):
    """Base model that forbids unexpected fields on request bodies.

    ``extra="forbid"`` strengthens input safety: a client cannot smuggle
    unexpected keys past validation (Requirement 23.1). Response models that
    must stay permissive do not inherit from this base.
    """

    model_config = ConfigDict(extra="forbid")
