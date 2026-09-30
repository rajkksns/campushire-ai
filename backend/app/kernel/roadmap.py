"""Roadmap_Generator: prioritized learning roadmap (Requirement 12).

This module is part of the *pure, deterministic* analysis kernel. It imports
only the standard library and the sibling ``comparator`` types; it must never
import FastAPI, sqlite3, or any I/O/adapter code (Requirement 20, design
"pure-kernel" principle).

It turns the categorized required skills into an ordered
:class:`~app.kernel.comparator.ComparedSkill`-derived learning roadmap that
tells the student which gaps to close first.

Rules (Requirement 12):
    - One item per ``MISSING`` and ``WEAK`` skill; ``MATCHED`` skills are
      excluded (12.1, 12.6).
    - Order by weight descending (12.2); on equal weight, ``MISSING`` before
      ``WEAK`` (12.3); on equal weight and category, normalized name ascending
      (12.4). This total order makes the roadmap deterministic (12.5).
    - ``priority_rank`` is assigned 1..N after sorting.

No randomness, clock, network, or I/O is involved, so identical inputs always
yield an identically ordered roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.kernel.comparator import Category, ComparedSkill

__all__ = ["RoadmapItem", "generate"]


# Category ordering key for the "MISSING before WEAK" tie-break (12.3). Lower
# sorts first; MATCHED is never emitted so its value is irrelevant but defined
# for completeness.
_CATEGORY_ORDER: dict[Category, int] = {
    Category.MISSING: 0,
    Category.WEAK: 1,
    Category.MATCHED: 2,
}


@dataclass(frozen=True)
class RoadmapItem:
    """One prioritized learning item for a gap skill.

    Attributes:
        name: Normalized skill name.
        weight: Importance weight carried from the required skill.
        category: Either ``MISSING`` or ``WEAK`` (``MATCHED`` is excluded).
        priority_rank: 1-based position in the ordered roadmap.
    """

    name: str
    weight: int
    category: Category
    priority_rank: int


def generate(compared: list[ComparedSkill]) -> list[RoadmapItem]:
    """Produce the prioritized learning roadmap from compared skills.

    Args:
        compared: The categorized required skills from the Skill_Comparator.

    Returns:
        An ordered list of :class:`RoadmapItem`, one per ``MISSING`` or ``WEAK``
        skill (matched excluded, 12.1/12.6), sorted by the deterministic total
        order (weight desc, then missing-before-weak, then name asc — 12.2–12.5)
        with ``priority_rank`` assigned 1..N.
    """
    gaps = [
        cs
        for cs in compared
        if cs.category in (Category.MISSING, Category.WEAK)
    ]

    # Total order: weight desc, then category (missing before weak), then
    # normalized name asc (12.2, 12.3, 12.4) — deterministic (12.5).
    gaps.sort(key=lambda cs: (-cs.weight, _CATEGORY_ORDER[cs.category], cs.name))

    return [
        RoadmapItem(
            name=cs.name,
            weight=cs.weight,
            category=cs.category,
            priority_rank=rank,
        )
        for rank, cs in enumerate(gaps, start=1)
    ]
