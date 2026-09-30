"""Property-based tests for the Skill_Comparator.

Property 4: Categorization is a correct total partition.
    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6.
Property 5: Comparison is deterministic and order-invariant.
    Validates: Requirements 9.1, 9.2, 9.3.

Each property runs a minimum of 100 iterations and is tagged with its number.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.kernel.comparator import (
    PROFICIENCY_THRESHOLD,
    Category,
    ComparedSkill,
    StudentSkill,
    compare,
)
from app.kernel.extractor import RequiredSkill
from app.kernel.normalize import skill_normalize

# Skill names drawn from a small pool so student and required sets overlap
# often enough to exercise matched/weak paths (not just missing).
_NAME_POOL = [
    "python",
    "Python",
    "  java ",
    "JavaScript",
    "docker",
    "kubernetes",
    "sql",
    "AWS",
    "React",
    "go",
]

_student_skills = st.lists(
    st.builds(
        StudentSkill,
        name=st.sampled_from(_NAME_POOL),
        proficiency=st.integers(min_value=1, max_value=5),
    ),
    min_size=0,
    max_size=12,
)

_required_skills = st.lists(
    st.builds(
        RequiredSkill,
        name=st.sampled_from(_NAME_POOL),
        weight=st.integers(min_value=1, max_value=5),
    ),
    min_size=0,
    max_size=12,
)


def _distinct_required_count(required: list[RequiredSkill]) -> int:
    """Number of distinct required skills after normalized de-duplication."""
    return len({skill_normalize(r.name) for r in required if skill_normalize(r.name)})


# Property 4
@given(_student_skills, _required_skills)
def test_property_4_exactly_one_category_and_counts_sum(
    student: list[StudentSkill], required: list[RequiredSkill]
) -> None:
    """Each required skill gets exactly one category; counts sum (8.5, 8.6)."""
    result = compare(student, required)

    # One ComparedSkill per distinct required skill (8.5).
    assert len(result) == _distinct_required_count(required)

    matched = sum(1 for c in result if c.category is Category.MATCHED)
    weak = sum(1 for c in result if c.category is Category.WEAK)
    missing = sum(1 for c in result if c.category is Category.MISSING)
    # Counts partition the required set (8.6).
    assert matched + weak + missing == len(result)


# Property 4
@given(_student_skills, _required_skills)
def test_property_4_category_matches_proficiency_rule(
    student: list[StudentSkill], required: list[RequiredSkill]
) -> None:
    """Category follows the proficiency rule (8.1, 8.2, 8.3, 8.4)."""
    # Reference student proficiency map: normalized name -> max proficiency.
    prof: dict[str, int] = {}
    for s in student:
        n = skill_normalize(s.name)
        if n:
            prof[n] = max(prof.get(n, s.proficiency), s.proficiency)

    for c in compare(student, required):
        matched_prof = prof.get(c.name)
        if matched_prof is None:
            assert c.category is Category.MISSING
            assert c.proficiency is None
        elif matched_prof >= PROFICIENCY_THRESHOLD:
            assert c.category is Category.MATCHED
            assert c.proficiency == matched_prof
        else:
            assert c.category is Category.WEAK
            assert c.proficiency == matched_prof


# Property 5
@given(_student_skills, _required_skills, st.randoms())
def test_property_5_order_invariant_and_deterministic(
    student: list[StudentSkill],
    required: list[RequiredSkill],
    rng,
) -> None:
    """Permuting either input list does not change the result (9.1, 9.2, 9.3)."""
    baseline = compare(student, required)

    student_shuffled = list(student)
    required_shuffled = list(required)
    rng.shuffle(student_shuffled)
    rng.shuffle(required_shuffled)

    permuted = compare(student_shuffled, required_shuffled)
    assert permuted == baseline

    # Determinism: identical inputs -> identical output (9.1).
    assert compare(student, required) == baseline


# Property 5
@given(_student_skills, _required_skills)
def test_property_5_output_sorted_by_name(
    student: list[StudentSkill], required: list[RequiredSkill]
) -> None:
    """Output is sorted by normalized name, giving order-invariance (9.3)."""
    result = compare(student, required)
    names = [c.name for c in result]
    assert names == sorted(names)
