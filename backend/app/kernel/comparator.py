"""Skill_Comparator: compare student skills against required skills.

This module is part of the *pure, deterministic* analysis kernel. It imports
only the standard library and the sibling ``normalize`` / ``extractor``
helpers; it must never import FastAPI, sqlite3, or any I/O/adapter code
(Requirement 20, design "pure-kernel" principle).

Responsibility (Requirements 8, 9):
    Given the student's declared and resume-derived skills and the set of
    required skills extracted from a job description, categorize each required
    skill as ``MATCHED``, ``WEAK``, or ``MISSING`` and return a deterministic,
    order-invariant result.

Categorization rule (Requirement 8):
    Build a single normalized-name -> max-proficiency map over the *union* of
    declared and resume-derived skills (8.1). For each required skill:

    - ``MATCHED``  when a matching student skill has proficiency >= 3 (8.2)
    - ``WEAK``     when a matching student skill has proficiency  < 3 (8.3)
    - ``MISSING``  when there is no matching student skill (8.4)

    Every required skill is assigned to exactly one category (8.5) and the
    category counts sum to the required count (8.6).

Determinism and invariance (Requirement 9):
    Because the student skills are collapsed to a name->max-proficiency map
    before categorization, the order of the student list is irrelevant (9.2),
    and the output is sorted by normalized name so the order of the required
    list is likewise irrelevant (9.1, 9.3). No randomness, clock, network, or
    I/O is involved, so identical inputs always yield identical output.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.kernel.extractor import RequiredSkill
from app.kernel.normalize import skill_normalize

__all__ = [
    "Category",
    "PROFICIENCY_THRESHOLD",
    "StudentSkill",
    "ComparedSkill",
    "compare",
]


class Category(str, Enum):
    """The category a required skill falls into after comparison.

    Inherits from ``str`` so instances serialize directly to their string
    value in JSON responses (matched/weak/missing).
    """

    MATCHED = "matched"
    WEAK = "weak"
    MISSING = "missing"


# A matching student skill at or above this proficiency counts as MATCHED;
# below it counts as WEAK (Requirements 8.2, 8.3).
PROFICIENCY_THRESHOLD = 3


@dataclass(frozen=True)
class StudentSkill:
    """A skill the student has, normalized for comparison.

    Attributes:
        name: Skill name. Callers may pass a raw or normalized name; ``compare``
            normalizes it via :func:`skill_normalize` before matching (8.1).
        proficiency: Ordinal competency on the inclusive 1..5 scale. Resume-
            derived skills that are not otherwise declared are conventionally
            supplied at the default proficiency of 1 (see design).
    """

    name: str
    proficiency: int


@dataclass(frozen=True)
class ComparedSkill:
    """The categorization of a single required skill.

    Attributes:
        name: Normalized required-skill name (7.4).
        weight: Importance weight carried over from the required skill (1..5).
        category: Exactly one of :class:`Category` (8.5).
        proficiency: The student's matched proficiency for ``MATCHED``/``WEAK``;
            ``None`` for ``MISSING`` (no matching student skill).
    """

    name: str
    weight: int
    category: Category
    proficiency: int | None


def _build_student_proficiency_map(
    student_skills: list[StudentSkill],
) -> dict[str, int]:
    """Collapse student skills to a normalized-name -> max-proficiency map.

    Taking the maximum proficiency on a name collision implements the "union of
    declared + resume-derived skills" rule (8.1): if the same skill appears more
    than once (e.g. declared at 4 and resume-derived at 1), the strongest signal
    wins. Reducing to a map before categorization is what makes the result
    invariant to the order of the student list (9.2).
    """
    proficiency_by_name: dict[str, int] = {}
    for skill in student_skills:
        name = skill_normalize(skill.name)
        if not name:
            continue
        current = proficiency_by_name.get(name)
        if current is None or skill.proficiency > current:
            proficiency_by_name[name] = skill.proficiency
    return proficiency_by_name


def compare(
    student_skills: list[StudentSkill],
    required_skills: list[RequiredSkill],
) -> list[ComparedSkill]:
    """Categorize each required skill against the student's skill set.

    Args:
        student_skills: The union of the student's declared and resume-derived
            skills. Order is irrelevant; duplicate names collapse to their
            maximum proficiency (8.1, 9.2).
        required_skills: The required skills extracted from the job description.
            Order is irrelevant; the output is sorted by normalized name
            (9.1, 9.3).

    Returns:
        A list of :class:`ComparedSkill`, one per required skill, sorted
        ascending by normalized ``name``. Each required skill is assigned to
        exactly one category (8.5); therefore
        ``len(result) == len(required_skills)`` (after de-duplicating required
        names) and the matched/weak/missing counts sum to that length (8.6).
    """
    student_proficiency = _build_student_proficiency_map(student_skills)

    # De-duplicate required skills by normalized name, keeping the highest
    # weight on collision. This mirrors the extractor's own de-duplication rule
    # and guarantees exactly one ComparedSkill per distinct required skill (8.5).
    required_weight: dict[str, int] = {}
    for req in required_skills:
        name = skill_normalize(req.name)
        if not name:
            continue
        if req.weight > required_weight.get(name, -1):
            required_weight[name] = req.weight

    compared: list[ComparedSkill] = []
    # Sort by normalized name for an order-invariant, deterministic output
    # (9.1, 9.3).
    for name in sorted(required_weight):
        weight = required_weight[name]
        proficiency = student_proficiency.get(name)

        if proficiency is None:
            category = Category.MISSING  # no matching student skill (8.4)
        elif proficiency >= PROFICIENCY_THRESHOLD:
            category = Category.MATCHED  # proficiency >= 3 (8.2)
        else:
            category = Category.WEAK  # proficiency < 3 (8.3)

        compared.append(
            ComparedSkill(
                name=name,
                weight=weight,
                category=category,
                proficiency=proficiency,
            )
        )

    return compared
