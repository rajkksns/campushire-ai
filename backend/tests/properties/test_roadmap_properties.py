"""Property-based test for the Roadmap_Generator.

Property 12: Roadmap membership and deterministic ordering.
    Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6.

Runs a minimum of 100 iterations and is tagged with its property number.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.kernel.comparator import Category, ComparedSkill
from app.kernel.roadmap import generate

_CATEGORIES = list(Category)

# Category rank for the "missing before weak" tie-break assertion (12.3).
_CATEGORY_RANK = {Category.MISSING: 0, Category.WEAK: 1}


@st.composite
def _compared_lists(draw: st.DrawFn):
    """Generate a list of ComparedSkill with unique normalized names."""
    names = draw(
        st.lists(
            st.text(
                alphabet=st.characters(min_codepoint=97, max_codepoint=122),
                min_size=1,
                max_size=6,
            ),
            min_size=0,
            max_size=12,
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
        items.append(ComparedSkill(name, weight, category, prof))
    return items


# Property 12
@given(_compared_lists())
def test_property_12_membership(compared) -> None:
    """One item per missing/weak skill; matched excluded (12.1, 12.6)."""
    roadmap = generate(compared)

    expected_names = {
        c.name for c in compared if c.category in (Category.MISSING, Category.WEAK)
    }
    assert {item.name for item in roadmap} == expected_names
    assert all(item.category in (Category.MISSING, Category.WEAK) for item in roadmap)
    assert len(roadmap) == len(expected_names)


# Property 12
@given(_compared_lists())
def test_property_12_ordering_and_ranks(compared) -> None:
    """Ordering is weight desc, missing-before-weak, name asc (12.2-12.4)."""
    roadmap = generate(compared)

    keys = [
        (-item.weight, _CATEGORY_RANK[item.category], item.name) for item in roadmap
    ]
    assert keys == sorted(keys)

    # priority_rank assigned 1..N in order.
    assert [item.priority_rank for item in roadmap] == list(
        range(1, len(roadmap) + 1)
    )


# Property 12
@given(_compared_lists(), st.randoms())
def test_property_12_permutation_invariant(compared, rng) -> None:
    """Permuting the input yields an identical roadmap (12.5)."""
    baseline = generate(compared)
    shuffled = list(compared)
    rng.shuffle(shuffled)
    assert generate(shuffled) == baseline
