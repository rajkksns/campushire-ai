"""Unit tests for the Scoring_Engine's exact allocation behavior (task 5.8).

These assert the exact largest-remainder (Hamilton) outcome on hand-computed
examples and a weighted-proportionality example.
Validates: Requirements 10.4 (deterministic remainder distribution + tie-break)
and 10.11 (weighted proportionality).
"""

from __future__ import annotations

from app.kernel.comparator import Category, ComparedSkill
from app.kernel.scoring import score


def _points_by_name(result) -> dict[str, int]:
    return {item.name: item.points for item in result.breakdown}


def test_largest_remainder_distributes_to_highest_fraction_then_weight() -> None:
    """Hand-computed largest-remainder example (10.4).

    Three matched skills with weights 5, 3, 4 (total 12). All matched, so
    earned == capacity:
        python     (w5): 100*5/12 = 41.6667  -> floor 41, frac .6667
        docker     (w3): 100*3/12 = 25.0000  -> floor 25, frac .0
        kubernetes (w4): 100*4/12 = 33.3333  -> floor 33, frac .3333
    raw_score = 100 -> target 100; floors sum 99; remainder 1.
    Highest fractional part is python (.6667), so python gets the extra point.
    Expected: python 42, kubernetes 33, docker 25 (sum 100).
    """
    compared = [
        ComparedSkill("python", 5, Category.MATCHED, 5),
        ComparedSkill("docker", 3, Category.MATCHED, 5),
        ComparedSkill("kubernetes", 4, Category.MATCHED, 5),
    ]
    result = score(compared)
    pts = _points_by_name(result)

    assert result.readiness_score == 100
    assert pts == {"python": 42, "kubernetes": 33, "docker": 25}


def test_largest_remainder_alphabetical_tie_break() -> None:
    """Equal fraction and equal weight break ties alphabetically (10.4).

    Three equally weighted matched skills (w1 each, total 3):
        each: 100/3 = 33.3333 -> floor 33, frac .3333 (identical).
    raw_score = 100 -> target 100; floors sum 99; remainder 1.
    Fraction and weight tie, so the alphabetically-first name ("alpha") wins.
    Expected: alpha 34, bravo 33, charlie 33.
    """
    compared = [
        ComparedSkill("charlie", 1, Category.MATCHED, 5),
        ComparedSkill("alpha", 1, Category.MATCHED, 5),
        ComparedSkill("bravo", 1, Category.MATCHED, 5),
    ]
    result = score(compared)
    pts = _points_by_name(result)

    assert result.readiness_score == 100
    assert pts == {"alpha": 34, "bravo": 33, "charlie": 33}


def test_weighted_proportionality() -> None:
    """Contributions scale with weight relative to total weight (10.11).

    Two matched skills, weights 3 and 1 (total 4):
        heavy (w3): 100*3/4 = 75  -> 75 points
        light (w1): 100*1/4 = 25  -> 25 points
    Both whole numbers, so no remainder distribution is needed.
    """
    compared = [
        ComparedSkill("heavy", 3, Category.MATCHED, 5),
        ComparedSkill("light", 1, Category.MATCHED, 5),
    ]
    result = score(compared)
    pts = _points_by_name(result)

    assert result.readiness_score == 100
    assert pts == {"heavy": 75, "light": 25}
    # Heavy skill contributes exactly 3x the light skill (proportional to weight).
    assert pts["heavy"] == 3 * pts["light"]


def test_weak_half_capacity_and_conservation() -> None:
    """Weak earns half its capacity; total conserves (10.13, 10.3, weak=0.5).

    weights 5 (matched), 3 (weak), 4 (missing), total 12:
        python     matched: 41.6667
        docker     weak:    25.0 * 0.5 = 12.5
        kubernetes missing: 0
    raw_score = 54.1667 -> target 54; floors 41+12+0=53; remainder 1 -> highest
    fraction is python (.6667) -> python 42. docker 12, kubernetes 0.
    """
    compared = [
        ComparedSkill("python", 5, Category.MATCHED, 4),
        ComparedSkill("docker", 3, Category.WEAK, 2),
        ComparedSkill("kubernetes", 4, Category.MISSING, None),
    ]
    result = score(compared)
    pts = _points_by_name(result)

    assert result.readiness_score == 54
    assert sum(pts.values()) == 54
    assert pts == {"python": 42, "docker": 12, "kubernetes": 0}


def test_zero_total_weight_equal_allocation() -> None:
    """When all weights are 0, allocate equally via the same rule (10.13).

    Two skills both weight 0 -> treated as w=1 each (total 2):
        matched: 100/2 = 50
        missing: 0
    Score = 50.
    """
    compared = [
        ComparedSkill("a", 0, Category.MATCHED, 5),
        ComparedSkill("b", 0, Category.MISSING, None),
    ]
    result = score(compared)
    pts = _points_by_name(result)

    assert result.readiness_score == 50
    assert pts == {"a": 50, "b": 0}
