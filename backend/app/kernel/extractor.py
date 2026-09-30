"""Skill_Extractor: curated skill vocabulary and alias table (subtask 3.1).

This module belongs to the *pure, deterministic* analysis kernel. It imports
only the standard library and the sibling ``normalize`` helper; it must never
import FastAPI, sqlite3, or any I/O/adapter code (Requirement 20, design
"pure-kernel" principle).

Purpose of this file (subtask 3.1 scope):
    Define the static, source-controlled skill vocabulary the extractor matches
    against. The vocabulary maps a *canonical* skill name to a set of *aliases*
    that should resolve to that canonical name. Both canonical names and aliases
    are stored in normalized form (via :func:`skill_normalize`) so matching is
    case-insensitive and whitespace-tolerant and results are reproducible for the
    evaluator (Requirements 7.1, 7.5).

Example (from design.md):
    ``{"javascript": {"js", "ecmascript"}, "postgresql": {"postgres", "psql"}}``

Reproducibility (Requirement 7.5):
    The vocabulary is a fixed literal versioned in source control. Bump
    :data:`VOCABULARY_VERSION` whenever the entries change so that analysis
    results remain traceable to a known vocabulary snapshot.

Subtasks 3.2 (``RequiredSkill`` + ``extract_required_skills``) and 3.3
(``extract_resume_skills``) build on this data structure and are intentionally
NOT implemented here.
"""

from __future__ import annotations

from app.kernel.normalize import skill_normalize

__all__ = [
    "VOCABULARY_VERSION",
    "SKILL_VOCABULARY",
    "ALIAS_TO_CANONICAL",
    "canonical_for",
]

# Version stamp for the curated vocabulary. Increment when SKILL_VOCABULARY
# changes so analysis output can be traced to a known snapshot (Requirement 7.5).
VOCABULARY_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Raw curated vocabulary
# ---------------------------------------------------------------------------
# Author entries in human-readable form; they are normalized below at import
# time so the source stays readable while the runtime tables stay canonical.
# Grouped by domain purely for readability -- ordering has no runtime meaning
# (the extractor imposes its own deterministic ordering in later subtasks).
_RAW_VOCABULARY: dict[str, set[str]] = {
    # --- Programming languages ------------------------------------------
    "python": {"py", "python3", "cpython"},
    "javascript": {"js", "ecmascript", "es6", "es2015"},
    "typescript": {"ts"},
    "java": set(),
    "c": {"c language", "ansi c"},
    "c++": {"cpp", "cplusplus", "c plus plus"},
    "c#": {"csharp", "c sharp", "dotnet c#"},
    "go": {"golang"},
    "rust": {"rustlang"},
    "ruby": set(),
    "php": set(),
    "swift": set(),
    "kotlin": {"kt"},
    "scala": set(),
    "r": {"r language"},
    "matlab": set(),
    "perl": set(),
    "objective-c": {"objc", "objective c"},
    "dart": set(),
    "bash": {"shell", "shell scripting", "sh"},
    "powershell": {"pwsh"},
    "sql": {"structured query language"},

    # --- Frontend frameworks / libraries --------------------------------
    "react": {"reactjs", "react.js"},
    "angular": {"angularjs", "angular.js"},
    "vue": {"vuejs", "vue.js"},
    "svelte": {"sveltejs"},
    "next.js": {"nextjs", "next js"},
    "redux": set(),
    "jquery": set(),
    "html": {"html5"},
    "css": {"css3"},
    "sass": {"scss"},
    "tailwind css": {"tailwind", "tailwindcss"},
    "bootstrap": set(),

    # --- Backend frameworks ---------------------------------------------
    "node.js": {"node", "nodejs"},
    "express": {"expressjs", "express.js"},
    "django": set(),
    "flask": set(),
    "fastapi": {"fast api"},
    "spring": {"spring boot", "springboot", "spring framework"},
    "rails": {"ruby on rails", "ror"},
    "laravel": set(),
    ".net": {"dotnet", "dot net", ".net core", "asp.net"},
    "graphql": set(),
    "rest": {"rest api", "restful", "restful api"},
    "grpc": set(),

    # --- Databases ------------------------------------------------------
    "postgresql": {"postgres", "psql", "postgre"},
    "mysql": set(),
    "sqlite": {"sqlite3"},
    "mongodb": {"mongo"},
    "redis": set(),
    "elasticsearch": {"elastic search", "elk"},
    "cassandra": set(),
    "oracle": {"oracle db", "oracle database"},
    "microsoft sql server": {"sql server", "mssql", "ms sql"},
    "dynamodb": {"dynamo db"},

    # --- Cloud / DevOps / infrastructure --------------------------------
    "aws": {"amazon web services"},
    "azure": {"microsoft azure"},
    "google cloud platform": {"gcp", "google cloud"},
    "docker": {"dockerize", "containerization"},
    "kubernetes": {"k8s"},
    "terraform": set(),
    "ansible": set(),
    "jenkins": set(),
    "ci/cd": {"cicd", "ci cd", "continuous integration", "continuous delivery",
              "continuous deployment"},
    "linux": {"unix"},
    "nginx": set(),
    "kafka": {"apache kafka"},
    "rabbitmq": {"rabbit mq"},

    # --- Data / ML ------------------------------------------------------
    "machine learning": {"ml"},
    "deep learning": {"dl"},
    "artificial intelligence": {"ai"},
    "natural language processing": {"nlp"},
    "computer vision": {"cv"},
    "data science": set(),
    "data analysis": {"data analytics"},
    "pandas": set(),
    "numpy": set(),
    "tensorflow": {"tf"},
    "pytorch": {"torch"},
    "scikit-learn": {"sklearn", "scikit learn"},
    "spark": {"apache spark", "pyspark"},
    "hadoop": set(),
    "tableau": set(),
    "power bi": {"powerbi"},

    # --- Tools / practices ----------------------------------------------
    "git": set(),
    "github": set(),
    "gitlab": set(),
    "jira": set(),
    "agile": {"agile methodology"},
    "scrum": set(),
    "kanban": set(),
    "unit testing": {"unit tests"},
    "test driven development": {"tdd"},
    "microservices": {"microservice", "micro services"},
    "object oriented programming": {"oop", "object-oriented programming"},

    # --- Soft skills ----------------------------------------------------
    "communication": {"communication skills", "verbal communication",
                       "written communication"},
    "teamwork": {"team work", "collaboration", "team player"},
    "leadership": {"team leadership", "leading teams"},
    "problem solving": {"problem-solving", "analytical thinking"},
    "critical thinking": {"critical-thinking"},
    "time management": {"time-management"},
    "adaptability": {"flexibility"},
    "creativity": {"creative thinking"},
    "attention to detail": {"detail oriented", "detail-oriented"},
    "project management": {"project-management"},
    "presentation": {"presentation skills", "public speaking"},
    "mentoring": {"mentorship", "coaching"},
}


def _build_vocabulary(raw: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    """Normalize the raw vocabulary into canonical -> alias-set form.

    Every canonical key and every alias is passed through
    :func:`skill_normalize` so the runtime tables are guaranteed to be in
    canonical form (Requirement 7.4). The canonical name itself is never
    included in its own alias set.
    """
    built: dict[str, frozenset[str]] = {}
    for canonical, aliases in raw.items():
        norm_canonical = skill_normalize(canonical)
        norm_aliases = {
            a for a in (skill_normalize(alias) for alias in aliases)
            if a and a != norm_canonical
        }
        # Merge if two raw keys normalize to the same canonical name.
        existing = built.get(norm_canonical, frozenset())
        built[norm_canonical] = frozenset(existing | norm_aliases)
    return built


def _build_alias_index(
    vocabulary: dict[str, frozenset[str]],
) -> dict[str, str]:
    """Build a flat normalized-term -> canonical-name lookup index.

    Includes both canonical names (mapping to themselves) and all aliases.
    """
    index: dict[str, str] = {}
    for canonical, aliases in vocabulary.items():
        index[canonical] = canonical
        for alias in aliases:
            # Canonical names always win over an alias collision.
            index.setdefault(alias, canonical)
    return index


# Canonical (normalized) skill name -> frozenset of normalized aliases.
SKILL_VOCABULARY: dict[str, frozenset[str]] = _build_vocabulary(_RAW_VOCABULARY)

# Flat lookup: any normalized canonical name or alias -> canonical name.
ALIAS_TO_CANONICAL: dict[str, str] = _build_alias_index(SKILL_VOCABULARY)


def canonical_for(term: str) -> str | None:
    """Return the canonical skill name for ``term``, or ``None`` if unknown.

    ``term`` is normalized before lookup, so matching is case-insensitive and
    whitespace-tolerant. This is a small, pure convenience over
    :data:`ALIAS_TO_CANONICAL` for use by the extraction functions in later
    subtasks (3.2, 3.3).
    """
    return ALIAS_TO_CANONICAL.get(skill_normalize(term))


# ---------------------------------------------------------------------------
# Subtask 3.2: RequiredSkill dataclass + extract_required_skills
# ---------------------------------------------------------------------------
# Everything below builds on the vocabulary tables defined above. It remains
# part of the PURE kernel: standard library + the sibling normalize helper
# only. No randomness, no wall-clock, no network, no file/DB/HTTP access, so
# identical input text always yields an identical result (Requirement 7.5).

import re
from dataclasses import dataclass

# Extend the public surface with the 3.2 additions without dropping 3.1 names.
__all__ += [
    "RequiredSkill",
    "extract_required_skills",
    "MIN_WEIGHT",
    "MAX_WEIGHT",
    "REQUIRED_CUES",
    "PREFERRED_CUES",
]

# Inclusive bounds for a Required_Skill importance weight (Requirement 7.2).
MIN_WEIGHT = 1
MAX_WEIGHT = 5

# Deterministic phrasing cues. A hit whose surrounding context contains a
# "required"/"must have" cue is boosted; a hit near a "preferred"/"nice to
# have" cue is dampened. Cues are matched case-insensitively against the
# normalized text. Kept as fixed literals so weighting stays reproducible.
REQUIRED_CUES: tuple[str, ...] = (
    "required",
    "require",
    "must have",
    "must-have",
    "must",
    "essential",
    "mandatory",
    "responsibilities",
    "requirements",
    "strong",
    "proficiency in",
    "proficient in",
    "expertise in",
    "expert in",
)

PREFERRED_CUES: tuple[str, ...] = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "good to have",
    "good-to-have",
    "plus",
    "bonus",
    "a plus",
    "optional",
    "desirable",
    "advantage",
    "beneficial",
    "familiarity with",
)

# How far (in characters, within the normalized text) a phrasing cue may sit
# from a skill hit and still be considered to apply to it. Fixed constant, so
# weighting stays deterministic.
_CUE_WINDOW = 60


@dataclass(frozen=True)
class RequiredSkill:
    """A skill the target job requires, with a deterministic importance weight.

    Attributes:
        name: Display name in normalized form (via :func:`skill_normalize`);
            this is also the form used for case-insensitive matching (7.4).
        weight: Importance on the inclusive 1..5 scale (7.2).
    """

    name: str
    weight: int


def _boundary_class(char: str) -> str:
    """Classify a term's edge character to pick the right boundary guard.

    Word-boundary detection via ``\\b`` is unreliable for skill tokens that
    begin or end with punctuation (``c++``, ``c#``, ``.net``, ``ci/cd``). We
    therefore guard boundaries ourselves based on the edge character:

    - ``"word"``: the edge is alphanumeric (e.g. ``python``, ``java``). The
      adjacent text character must not be another word character, otherwise
      ``java`` would match inside ``javascript`` and ``c`` inside ``category``.
    - ``"symbol"``: the edge is punctuation (e.g. the ``+`` in ``c++``). Only a
      directly-adjacent *identical run* would over-match, which the escaped
      literal already prevents, so no alphanumeric guard is needed on that side.
    """
    return "word" if char.isalnum() else "symbol"


def _compile_term_pattern(term: str) -> re.Pattern[str]:
    """Compile a whole-token, whitespace-flexible matcher for one vocab term.

    ``term`` is an already-normalized canonical name or alias (lowercase,
    single-spaced). Internal spaces are allowed to match any whitespace run so
    multi-word phrases such as ``"amazon web services"`` or ``"ci cd"`` are
    found regardless of the exact spacing in the source text. Boundaries are
    guarded per :func:`_boundary_class` so alphanumeric-edged terms match only
    as whole tokens.
    """
    # Escape each space-separated piece, rejoin with a flexible whitespace gap.
    pieces = [re.escape(piece) for piece in term.split(" ") if piece]
    core = r"\s+".join(pieces)

    left_guard = r"(?<![0-9a-z])" if _boundary_class(term[0]) == "word" else ""
    right_guard = r"(?![0-9a-z])" if _boundary_class(term[-1]) == "word" else ""

    return re.compile(left_guard + core + right_guard)


# Precompiled matchers for every alias/canonical term -> its canonical name.
# Built once at import time from the (already normalized) ALIAS_TO_CANONICAL
# table so extraction does no per-call compilation work. Terms are sorted by
# descending length then name purely for deterministic build order; match
# results are aggregated per canonical name so order does not affect output.
_TERM_MATCHERS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (_compile_term_pattern(term), canonical)
    for term, canonical in sorted(
        ALIAS_TO_CANONICAL.items(), key=lambda kv: (-len(kv[0]), kv[0])
    )
)


def _bucket_frequency(count: int) -> int:
    """Bucket a raw occurrence count into the inclusive 1..5 weight scale.

    Deterministic step function: 1 occurrence -> 1, 2 -> 2, 3 -> 3, 4 -> 4,
    5 or more -> 5. A skill can only reach this function with ``count >= 1``.
    """
    if count <= 1:
        return 1
    if count >= MAX_WEIGHT:
        return MAX_WEIGHT
    return count


def _cue_adjustment(text: str, span: tuple[int, int]) -> int:
    """Return a deterministic weight delta from phrasing cues near a hit.

    Looks in a fixed-size window on either side of the matched span. A nearby
    "required"/"must have" cue yields ``+1``; a nearby "preferred"/"nice to
    have" cue yields ``-1``. If both are present the required cue wins (jobs
    list must-haves before nice-to-haves and we bias toward importance). The
    window scan uses simple substring containment on the normalized text, which
    is fully deterministic.
    """
    start, end = span
    left = max(0, start - _CUE_WINDOW)
    right = min(len(text), end + _CUE_WINDOW)
    window = text[left:right]

    has_required = any(cue in window for cue in REQUIRED_CUES)
    has_preferred = any(cue in window for cue in PREFERRED_CUES)

    if has_required:
        return 1
    if has_preferred:
        return -1
    return 0


def _clamp_weight(value: int) -> int:
    """Clamp ``value`` into the inclusive [MIN_WEIGHT, MAX_WEIGHT] range."""
    return max(MIN_WEIGHT, min(MAX_WEIGHT, value))


def extract_required_skills(job_description: str) -> list[RequiredSkill]:
    """Deterministically extract weighted required skills from JD text.

    Procedure (see design.md "Skill Extraction and Normalization"):

    1. Normalize the whole text once so matching and cue scanning share the
       exact case/whitespace rule used everywhere else (7.4, 8.1).
    2. For each vocabulary term (canonical name or alias), find every
       whole-token, case-insensitive occurrence; attribute each hit to its
       canonical skill name. Multi-word phrases match across whitespace.
    3. Weight each canonical skill from deterministic signals only: its total
       occurrence count bucketed into 1..5, plus a required/preferred phrasing
       adjustment, clamped back into 1..5 (7.2).
    4. Names are already normalized canonical forms, so de-duplication is
       inherent; on any collision the highest weight is kept (7.3).
    5. Return the skills sorted by normalized name for a stable, deterministic
       order (7.5).

    An empty result (no vocabulary hits) is a valid, non-error outcome that
    flows through to scoring (7.6).

    Args:
        job_description: Raw target job-description text. ``None``/empty input
            simply yields an empty list.

    Returns:
        A list of :class:`RequiredSkill`, sorted ascending by ``name``.
    """
    if not job_description:
        return []

    text = skill_normalize(job_description)
    if not text:
        return []

    # canonical name -> (occurrence count, summed cue adjustment)
    counts: dict[str, int] = {}
    cue_deltas: dict[str, int] = {}

    # A mutable copy of the text used only for scanning: once a term claims a
    # character span we blank it out (replace with a separator) so a *shorter*
    # overlapping term cannot re-match inside it. _TERM_MATCHERS is ordered
    # longest-first, so e.g. "c++" claims its span before the single-character
    # "c" language is scanned, ensuring "c" does not match inside "c++"
    # (whole-token guarantee from the design). Blanking with a space also keeps
    # phrasing-cue windows meaningful and preserves character offsets so cue
    # spans still line up with the original normalized text.
    scan = list(text)

    for pattern, canonical in _TERM_MATCHERS:
        for match in pattern.finditer("".join(scan)):
            start, end = match.span()
            counts[canonical] = counts.get(canonical, 0) + 1
            cue_deltas[canonical] = cue_deltas.get(canonical, 0) + _cue_adjustment(
                text, match.span()
            )
            for i in range(start, end):
                scan[i] = " "

    if not counts:
        return []

    # Resolve each canonical skill to a single clamped weight. The cue delta is
    # reduced to a sign (net-required vs net-preferred vs neutral) so a term
    # mentioned many times does not accumulate an unbounded pre-clamp swing.
    best: dict[str, int] = {}
    for canonical, count in counts.items():
        base = _bucket_frequency(count)
        net = cue_deltas.get(canonical, 0)
        adjustment = 1 if net > 0 else (-1 if net < 0 else 0)
        weight = _clamp_weight(base + adjustment)
        # De-duplicate case-insensitively, keeping the highest weight (7.3).
        # Names are already normalized so a collision means the same canonical.
        if weight > best.get(canonical, MIN_WEIGHT - 1):
            best[canonical] = weight

    # Sort by normalized name for a stable, deterministic order (7.5).
    return [
        RequiredSkill(name=name, weight=best[name]) for name in sorted(best)
    ]


# ---------------------------------------------------------------------------
# Subtask 3.3: extract_resume_skills
# ---------------------------------------------------------------------------
# Derives the set of candidate skill names a resume mentions, using the exact
# same curated vocabulary, normalization, and whole-token matching rules as
# required-skill extraction. This keeps declared skills, resume-derived skills,
# and required skills comparable under one rule (Requirements 8.1, 5.2). Like
# the rest of the kernel it is pure and deterministic: standard library + the
# sibling normalize helper only, no randomness/clock/network/I/O, so identical
# resume text always yields an identical result.

__all__ += ["extract_resume_skills"]


def extract_resume_skills(resume_text: str | None) -> list[str]:
    """Deterministically derive candidate skill names from resume text.

    Uses the same curated vocabulary, :func:`skill_normalize` rule, and
    whole-token, case-insensitive matching as :func:`extract_required_skills`
    so resume-derived skills compare consistently with declared and required
    skills (Requirements 8.1, 5.2). Unlike required-skill extraction, no
    importance weighting is applied: a resume merely evidences that a candidate
    *has* a skill, so this returns the plain set of matched canonical names.

    Procedure:

    1. Return an empty list immediately for ``None`` or empty/whitespace-only
       input (a resume-less profile is a valid, non-error case).
    2. Normalize the whole text once (7.4) so matching shares the exact
       case/whitespace rule used everywhere else.
    3. Scan for every vocabulary term (canonical name or alias) as a whole
       token; attribute each hit to its canonical skill name. Longer terms are
       matched first and their spans blanked, so a shorter overlapping term
       (e.g. ``c`` inside ``c++``) cannot re-match — identical to the
       required-skill scan.
    4. De-duplicate (the canonical names are already normalized) and return
       them sorted ascending for a stable, deterministic order.

    Args:
        resume_text: Raw resume text, or ``None``. Empty/whitespace-only input
            yields an empty list.

    Returns:
        A sorted list of unique, normalized canonical skill names. Empty when
        the resume is absent or mentions no known skills.
    """
    if not resume_text:
        return []

    text = skill_normalize(resume_text)
    if not text:
        return []

    found: set[str] = set()

    # Mutable scan buffer: once a term claims a span we blank it so a shorter
    # overlapping term cannot re-match inside it (whole-token guarantee). Uses
    # the same longest-first _TERM_MATCHERS ordering as extract_required_skills.
    scan = list(text)

    for pattern, canonical in _TERM_MATCHERS:
        for match in pattern.finditer("".join(scan)):
            start, end = match.span()
            found.add(canonical)
            for i in range(start, end):
                scan[i] = " "

    # Canonical names are already normalized; sort for a deterministic order.
    return sorted(found)
