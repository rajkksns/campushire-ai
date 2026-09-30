"""Property-based tests for the Skill_Extractor.

Property 2: Extraction output invariants (weights in 1..5, no case-insensitive
    duplicate names). Validates: Requirements 7.2, 7.3.
Property 3: Extraction is deterministic. Validates: Requirements 7.5.

Each property runs a minimum of 100 iterations and is tagged with its number.
The generators bias toward text that actually contains vocabulary terms so the
properties exercise real extraction hits, while still admitting arbitrary text.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.kernel.extractor import (
    MAX_WEIGHT,
    MIN_WEIGHT,
    SKILL_VOCABULARY,
    extract_required_skills,
)
from app.kernel.normalize import skill_normalize

# A pool of real vocabulary terms (canonical names + a few aliases) to seed
# job-description text so extraction has something to find.
_CANONICAL_TERMS = sorted(SKILL_VOCABULARY.keys())
_ALIAS_TERMS = sorted(
    alias for aliases in SKILL_VOCABULARY.values() for alias in aliases
)
_TERM_POOL = _CANONICAL_TERMS + _ALIAS_TERMS

# Filler words and phrasing cues to interleave with skill terms.
_FILLER = st.sampled_from(
    [
        "required",
        "must have",
        "preferred",
        "nice to have",
        "experience with",
        "the",
        "and",
        "strong",
        "responsibilities include",
        "we are looking for a candidate with",
        ".",
        ",",
        "\n",
    ]
)

_terms = st.lists(st.sampled_from(_TERM_POOL), min_size=0, max_size=12)
_fillers = st.lists(_FILLER, min_size=0, max_size=12)


@st.composite
def _job_descriptions(draw: st.DrawFn) -> str:
    """Compose a plausible JD by interleaving skill terms and filler text."""
    terms = draw(_terms)
    fillers = draw(_fillers)
    tokens = terms + fillers
    draw(st.randoms()).shuffle(tokens)
    return " ".join(tokens)


# Also mix in fully arbitrary text to ensure robustness on junk input.
_arbitrary_text = st.text(max_size=200)
_jd_strategy = st.one_of(_job_descriptions(), _arbitrary_text)


# Property 2
@given(_jd_strategy)
def test_property_2_weights_within_bounds(jd: str) -> None:
    """Every extracted RequiredSkill has weight in the inclusive 1..5 (7.2)."""
    for skill in extract_required_skills(jd):
        assert isinstance(skill.weight, int)
        assert MIN_WEIGHT <= skill.weight <= MAX_WEIGHT


# Property 2
@given(_jd_strategy)
def test_property_2_no_case_insensitive_duplicate_names(jd: str) -> None:
    """The normalized names contain no case-insensitive duplicates (7.3)."""
    skills = extract_required_skills(jd)
    normalized = [skill_normalize(s.name) for s in skills]
    assert len(normalized) == len(set(normalized))


# Property 2
@given(_jd_strategy)
def test_property_2_names_are_normalized_and_sorted(jd: str) -> None:
    """Names are already normalized and the list is sorted by name (7.3, 7.5)."""
    skills = extract_required_skills(jd)
    names = [s.name for s in skills]
    assert names == sorted(names)
    for s in skills:
        assert s.name == skill_normalize(s.name)


# Property 3
@given(_jd_strategy)
def test_property_3_extraction_is_deterministic(jd: str) -> None:
    """Two calls on identical text produce identical results (7.5)."""
    first = extract_required_skills(jd)
    second = extract_required_skills(jd)
    assert first == second
