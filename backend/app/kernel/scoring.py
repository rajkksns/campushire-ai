"""Scoring_Engine: transparent, deterministic readiness score (Requirement 10).

This module is part of the *pure, deterministic* analysis kernel. It imports
only the standard library and the sibling ``comparator`` types; it must never
import FastAPI, sqlite3, or any I/O/adapter code (Requirement 20, design
"pure-kernel" principle).

It turns a list of :class:`~app.kernel.comparator.ComparedSkill` into an
integer ``Readiness_Score`` in [0, 100] whose per-skill point contributions sum
**exactly** to the score. The procedure is the Hamilton / largest-remainder
method specified in design.md ("Scoring Algorithm"), which guarantees:

- **Bounds** (10.1): the score is an integer in [0, 100].
- **Determinism** (10.2): identical inputs yield an identical score; the
  remainder-distribution sort key is a total order.
- **Conservation / transparency** (10.3, 10.13, 10.10): the breakdown's integer
  points sum exactly to the score, and every point is traceable to a skill.
- **Weighted proportionality** (10.11): each skill contributes in proportion to
  its weight relative to the total weight.
- **Degenerate cases** (10.5, 10.6, 10.12): all-matched -> 100, all-missing ->
  0, empty required set -> 0 with an empty breakdown.

No randomness, clock, network, or I/O is involved.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.kernel.comparator import Category, ComparedSkill

__all__ = [
    "BreakdownItem",
    "ScoreResult",
    "CATEGORY_FACTOR",
    "score",
]


@dataclass(frozen=True)
class BreakdownItem:
    """One traceable line of the Score_Breakdown (Requirement 10.10).

    Attributes:
        name: Normalized skill name.
        weight: Importance weight carried from the required skill.
        category: The skill's category (matched/weak/missing).
        points: Integer point contribution; the sum of all items' points equals
            the readiness score (10.3).
    """

    name: str
    weight: int
    category: Category
    points: int


@dataclass(frozen=True)
class ScoreResult:
    """The computed readiness score and its itemized breakdown.

    Attributes:
        readiness_score: Integer in [0, 100] (10.1).
        breakdown: Per-skill :class:`BreakdownItem` list, ordered by the same
            total order used for remainder distribution so it is deterministic
            and traceable (10.10).
    """

    readiness_score: int
    breakdown: list[BreakdownItem]


# Fraction of a skill's weighted capacity earned by category (design Step 3).
# Monotonic in category (matched >= weak >= missing), the basis for the
# monotonicity properties (10.7, 10.8, 10.9).
CATEGORY_FACTOR: dict[Category, float] = {
    Category.MATCHED: 1.0,
    Category.WEAK: 0.5,
    Category.MISSING: 0.0,
}

# Inclusive bounds for the readiness score (Requirement 10.1).
_MIN_SCORE = 0
_MAX_SCORE = 100


def _round_half_up(value: float) -> int:
    """Round ``value`` to the nearest integer using round-half-up.

    ``round`` in Python uses banker's rounding, which would make the score
    depend on parity; the design mandates round-half-up for a deterministic,
    intuitive target. ``Decimal`` gives exact half-up behavior.
    """
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def score(compared: list[ComparedSkill]) -> ScoreResult:
    """Compute the readiness score and breakdown via largest-remainder rounding.

    Implements the design's "Scoring Algorithm" exactly:

    1. **Degenerate case** — empty required set returns score 0 and an empty
       breakdown (10.12).
    2. **Per-skill weights** — use each skill's weight; if the total weight is
       0, treat every skill as equally weighted with ``w = 1`` (10.13), reusing
       the same rounding rule.
    3. **Raw earned score** — ``capacity_i = 100 * w_i / sum(w)``;
       ``earned_i = capacity_i * factor(category_i)``;
       ``raw_score = sum(earned_i)`` in [0, 100].
    4. **Integer allocation (Hamilton)** — ``target = round_half_up(raw_score)``
       clamped to [0, 100]; give each skill ``floor(earned_i)`` points, then
       distribute the ``target - sum(floor)`` remainder one point at a time to
       skills ordered by fractional part desc, then weight desc, then
       normalized name asc (10.4). This conserves the total (10.3) and is
       deterministic (10.2).
    5. **Breakdown** — emit one :class:`BreakdownItem` per skill in that same
       total order (10.10).

    Args:
        compared: The categorized required skills from the Skill_Comparator.

    Returns:
        A :class:`ScoreResult` whose breakdown points sum exactly to
        ``readiness_score`` (10.3), with the score in [0, 100] (10.1).
    """
    if not compared:
        return ScoreResult(readiness_score=0, breakdown=[])

    # Step 2 — effective per-skill weights. If every weight is 0, weight all
    # skills equally at 1 so the "equal allocation" case reuses this same path
    # (10.13). Weights are treated as non-negative per the contract.
    total_weight = sum(max(0, cs.weight) for cs in compared)
    if total_weight == 0:
        effective_weights = [1] * len(compared)
        total_weight = len(compared)
    else:
        effective_weights = [max(0, cs.weight) for cs in compared]

    # Step 3 — fractional earned points per skill.
    earned: list[float] = []
    for cs, w in zip(compared, effective_weights):
        capacity = 100.0 * w / total_weight
        earned.append(capacity * CATEGORY_FACTOR[cs.category])

    raw_score = sum(earned)

    # Step 4.1 — integer target, round-half-up then clamped to [0, 100].
    target = max(_MIN_SCORE, min(_MAX_SCORE, _round_half_up(raw_score)))

    # Step 4.2 — floors and the remainder to distribute.
    floors = [math.floor(e) for e in earned]
    fracs = [e - f for e, f in zip(earned, floors)]
    remainder = target - sum(floors)

    # Step 4.4 — total order for distributing the remainder and for the
    # breakdown: fractional part desc, weight desc, normalized name asc (10.4).
    order = sorted(
        range(len(compared)),
        key=lambda i: (-fracs[i], -effective_weights[i], compared[i].name),
    )

    # Step 4.5 — hand out the remaining points one at a time in that order.
    # ``remainder`` is bounded by the number of skills, but guard the range so
    # a clamped target can never over- or under-allocate.
    points = list(floors)
    give = max(0, min(remainder, len(order)))
    for idx in order[:give]:
        points[idx] += 1

    # Step 5 — breakdown ordered by the same total order (10.10). Points are
    # guaranteed non-negative and sum exactly to ``target`` (10.3).
    breakdown = [
        BreakdownItem(
            name=compared[i].name,
            weight=compared[i].weight,
            category=compared[i].category,
            points=points[i],
        )
        for i in order
    ]

    return ScoreResult(readiness_score=sum(points), breakdown=breakdown)
