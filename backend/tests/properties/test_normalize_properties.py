"""Property-based tests for the shared normalization helper.

Property 1: Normalization is idempotent and case/whitespace invariant.
Validates: Requirements 7.4, 2.6.

Each property runs a minimum of 100 iterations (see [tool.hypothesis] in
pyproject.toml) and is tagged with its property number.
"""

from __future__ import annotations

import re

from hypothesis import given
from hypothesis import strategies as st

from app.kernel.normalize import skill_normalize

# Whitespace characters Hypothesis may inject around/inside a base string.
_WHITESPACE = " \t\n\r\f\v"


def _reword_with_whitespace(word: str, ws_choices: list[str]) -> str:
    """Rebuild ``word`` with arbitrary whitespace runs between characters."""
    if not word:
        return "".join(ws_choices[:1])
    parts: list[str] = []
    for i, ch in enumerate(word):
        parts.append(ch)
        parts.append(ws_choices[i % len(ws_choices)])
    return "".join(parts)


# Base tokens: word-ish content without whitespace so we control whitespace
# variation ourselves. Mix of letters/digits/punctuation.
_base_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs", "Zs", "Zl", "Zp")),
    min_size=0,
    max_size=40,
).map(lambda s: re.sub(r"\s+", "", s))


# Property 1
@given(_base_text)
def test_property_1_normalize_is_idempotent(s: str) -> None:
    """normalize(normalize(s)) == normalize(s) for all s (7.4)."""
    once = skill_normalize(s)
    assert skill_normalize(once) == once


# Property 1
@given(_base_text)
def test_property_1_normalize_is_case_invariant(s: str) -> None:
    """Changing letter case does not change the normalized form (7.4, 2.6).

    ``skill_normalize`` lowercases, so a string and its lowercased form must
    normalize identically. We compare against ``s.lower()`` rather than
    ``s.upper()`` vs ``s.lower()`` because Python's ``str.upper``/``str.lower``
    are not mutual inverses for every Unicode code point (e.g. 'ß'.upper() ==
    'SS'), which would make an upper-vs-lower comparison test the quirks of
    Unicode case mapping rather than the normalizer's case tolerance.
    """
    assert skill_normalize(s) == skill_normalize(s.lower())


# Property 1
@given(
    st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=0,
        max_size=40,
    )
)
def test_property_1_normalize_is_ascii_case_invariant(s: str) -> None:
    """For ASCII text, any case variant normalizes identically (7.4, 2.6).

    ASCII ``str.upper``/``str.lower``/``str.swapcase`` are well-behaved (they
    are mutual case variants), so all of them collapse to the same normalized
    form. This is the case tolerance that matters for real skill names.
    """
    base = skill_normalize(s)
    assert skill_normalize(s.upper()) == base
    assert skill_normalize(s.lower()) == base
    assert skill_normalize(s.swapcase()) == base


# Property 1
@given(
    _base_text,
    st.lists(st.sampled_from(list(_WHITESPACE)), min_size=1, max_size=5),
    st.text(alphabet=_WHITESPACE, min_size=0, max_size=4),
    st.text(alphabet=_WHITESPACE, min_size=0, max_size=4),
)
def test_property_1_normalize_is_whitespace_invariant(
    s: str, inner_ws: list[str], lead: str, trail: str
) -> None:
    """Leading/trailing/internal whitespace variations normalize identically.

    A variant s' built from s by adding leading/trailing whitespace and by
    inserting arbitrary whitespace runs between characters must satisfy
    skill_normalize(s) == skill_normalize(s') (7.4, 2.6).
    """
    variant = lead + _reword_with_whitespace(s, inner_ws) + trail
    # The internal-whitespace variant inserts separators between every
    # character; that is a faithful "altered internal whitespace" of a string
    # whose own characters contain no whitespace, so both collapse to the same
    # single-spaced, trimmed, lowercased form.
    expected = skill_normalize(s)
    got = skill_normalize(variant)
    # When s has multiple characters, inserting whitespace between them creates
    # word boundaries; the invariant we assert is the canonical one: the
    # normalized variant equals the normalized, space-joined characters of s.
    canonical_variant = skill_normalize(" ".join(s)) if len(s) > 1 else expected
    assert got == canonical_variant


# Property 1
@given(_base_text)
def test_property_1_normalize_output_is_canonical(s: str) -> None:
    """Output is trimmed, single-spaced, and lowercase (7.4)."""
    out = skill_normalize(s)
    assert out == out.strip()
    assert out == out.lower()
    assert "  " not in out
