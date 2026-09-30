"""Property-based tests for the Scoring_Engine.

Property 6:  Score is an integer within bounds. Validates: Requirement 10.1.
Property 7:  Breakdown conserves the score. Validates: 10.3, 10.4, 10.13.
Property 8:  Scoring is deterministic. Validates: 10.2.
Property 9:  Extreme categorizations map to score bounds. Validates:
             10.5, 10.6, 10.12, 7.6.
Property 10: Score is monotonic in categorization. Validates: 10.7, 10.8, 10.9.
Property 11: Breakdown is complete and traceable. Validates: 10.10.

Each property runs a minimum of 100 iterations and is tagged with its number.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.kernel.comparator import Category, ComparedSkill
from app.kernel.scoring import CATEGORY_FACTOR, score

_CATEGORIES = list(Category)


@st.composite
def _compared_lists(draw: st.DrawFn, min_size: int = 0, max_size: int = 12):
    """Generate a list of ComparedSkill with unique normalized names.

    Names are unique so the list is a valid comparator output (one entry per
    distinct required skill). Weights are non-negative; categories are free.
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    names = draw(
        st.lists(
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122),
                min_size=1,
                max_size=6,
            ),
            min_size=size,
            max_size=size,
            unique=True,
        )
    )
    items: list[ComparedSkill] = []
    for name in names:
        weight = draw(st.integers(min_value=0, max_value=5))
        category = draw(st.sampled_from(_CATEGORIES))
        prof = None if category is Category.MISSING else draw(
            st.integers(min_value=1, max_value=5)
        )
        items.append(
            ComparedSkill(name=name, weight=weight, category=category, proficiency=prof)
        )
    return items


# Property 6
@given(_compared_lists())
def test_property_6_score_integer_within_bounds(compared) -> None:
    """readiness_score is an int in the inclusive 0..100 range (10.1)."""
    result = score(compared)
    assert isinstance(result.readiness_score, int)
    assert 0 <= result.readiness_score <= 100


# Property 7
@given(_compared_lists())
def test_property_7_breakdown_conserves_score(compared) -> None:
    """Sum of breakdown points equals the score (10.3, 10.4, 10.13)."""
    result = score(compared)
    assert sum(item.points for item in result.breakdown) == result.readiness_score
    # Points are non-negative integers.
    for item in result.breakdown:
        assert isinstance(item.points, int)
        assert item.points >= 0


# Property 8
@given(_compared_lists())
def test_property_8_scoring_is_deterministic(compared) -> None:
    """Two calls on identical input yield identical score and breakdown (10.2)."""
    first = score(compared)
    second = score(compared)
    assert first.readiness_score == second.readiness_score
    assert first.breakdown == second.breakdown


# Property 9
@given(_compared_lists(min_size=1))
def test_property_9_all_matched_is_100(compared) -> None:
    """A non-empty all-matched set scores exactly 100 (10.5)."""
    all_matched = [
        ComparedSkill(c.name, c.weight, Category.MATCHED, 5) for c in compared
    ]
    assert score(all_matched).readiness_score == 100


# Property 9
@given(_compared_lists(min_size=1))
def test_property_9_all_missing_is_0(compared) -> None:
    """A non-empty all-missing set scores exactly 0 (10.6)."""
    all_missing = [
        ComparedSkill(c.name, c.weight, Category.MISSING, None) for c in compared
    ]
    assert score(all_missing).readiness_score == 0


# Property 9
def test_property_9_empty_is_0_with_empty_breakdown() -> None:
    """Empty required set scores 0 with an empty breakdown (10.12, 7.6)."""
    result = score([])
    assert result.readiness_score == 0
    assert result.breakdown == []


# Property 10
@given(_compared_lists(min_size=1), st.integers(min_value=0, max_value=11))
def test_property_10_downgrade_does_not_increase_score(compared, idx: int) -> None:
    """Downgrading one skill's category never increases the score (10.7)."""
    i = idx % len(compared)
    original = score(compared).readiness_score

    # Downgrade skill i one step: matched->weak->missing.
    target = compared[i]
    if target.category is Category.MATCHED:
        downgraded_cat, prof = Category.WEAK, 1
    elif target.category is Category.WEAK:
        downgraded_cat, prof = Category.MISSING, None
    else:
        return  # already missing; nothing to downgrade

    mutated = list(compared)
    mutated[i] = ComparedSkill(target.name, target.weight, downgraded_cat, prof)
    assert score(mutated).readiness_score <= original


# Property 10
@given(_compared_lists(min_size=1), st.integers(min_value=0, max_value=11))
def test_property_10_upgrade_does_not_decrease_score(compared, idx: int) -> None:
    """Upgrading one skill's category never decreases the score (10.8)."""
    i = idx % len(compared)
    original = score(compared).readiness_score

    target = compared[i]
    if target.category is Category.MISSING:
        upgraded_cat, prof = Category.WEAK, 1
    elif target.category is Category.WEAK:
        upgraded_cat, prof = Category.MATCHED, 5
    else:
        return  # already matched; nothing to upgrade

    mutated = list(compared)
    mutated[i] = ComparedSkill(target.name, target.weight, upgraded_cat, prof)
    assert score(mutated).readiness_score >= original


# Property 10
def test_property_10_category_factor_ordering() -> None:
    """At equal weight, matched >= weak >= missing in earned factor (10.9)."""
    assert (
        CATEGORY_FACTOR[Category.MATCHED]
        >= CATEGORY_FACTOR[Category.WEAK]
        >= CATEGORY_FACTOR[Category.MISSING]
    )


# Property 11
@given(_compared_lists())
def test_property_11_breakdown_complete_and_traceable(compared) -> None:
    """One breakdown item per required skill, each fully attributed (10.10)."""
    result = score(compared)
    assert len(result.breakdown) == len(compared)

    by_name = {c.name: c for c in compared}
    assert {item.name for item in result.breakdown} == set(by_name)
    for item in result.breakdown:
        source = by_name[item.name]
        assert item.weight == source.weight
        assert item.category == source.category
        assert isinstance(item.points, int)
