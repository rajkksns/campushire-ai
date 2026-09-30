"""CampusHire AI MCP server.

A small Model Context Protocol server that exposes read-only tools backed by the
project's pure, deterministic analysis kernel. It lets Kiro (and any MCP client)
inspect the curated skill vocabulary and exercise the canonicalization and
extraction logic without touching the database, network, or any mutable state.

Design notes:
    - The server is a *thin adapter* over ``app.kernel``. All real logic lives in
      the kernel; this module only marshals arguments in and results out. This
      keeps the determinism guarantees intact (see steering ``tech.md``).
    - No I/O beyond stdio transport: no DB, no filesystem writes, no network.
    - Tools are deterministic: identical arguments always return identical
      results, mirroring the kernel they wrap.
    - This package is named ``mcp_server`` (not ``mcp``) so it does not shadow
      the installed ``mcp`` SDK when launched from ``backend/``.

Run it:
    From the ``backend/`` directory (so both the ``app`` package and the ``mcp``
    SDK are importable):

        python -m mcp_server.server

    The server speaks MCP over stdio, which is how Kiro launches it (see
    ``.kiro/settings/mcp.json``).
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.kernel.extractor import (
    SKILL_VOCABULARY,
    VOCABULARY_VERSION,
    canonical_for,
    extract_required_skills,
)
from app.kernel.normalize import skill_normalize

# The MCP server instance. The name is what clients display for this server.
mcp = FastMCP("campushire-ai")


@mcp.tool()
def list_known_skills() -> dict[str, Any]:
    """Return the curated skill vocabulary the analyzer recognizes.

    The vocabulary maps each canonical (normalized) skill name to its set of
    aliases. It is static and versioned in source control, so the result is
    fully reproducible.

    Returns:
        A dict with:
          - ``version``: the vocabulary version stamp.
          - ``count``: number of canonical skills.
          - ``skills``: a sorted list of ``{"name", "aliases"}`` entries, where
            ``aliases`` is a sorted list of normalized alias strings.
    """
    skills = [
        {"name": canonical, "aliases": sorted(aliases)}
        for canonical, aliases in sorted(SKILL_VOCABULARY.items())
    ]
    return {
        "version": VOCABULARY_VERSION,
        "count": len(skills),
        "skills": skills,
    }


@mcp.tool()
def normalize_skill(name: str) -> dict[str, str]:
    """Canonicalize a skill name using the analyzer's normalization rule.

    Wraps ``skill_normalize``: trims, collapses internal whitespace to a single
    space, and lowercases. This is the exact rule used everywhere for
    case-insensitive, whitespace-tolerant skill matching.

    Args:
        name: The raw skill name to normalize.

    Returns:
        A dict with the original ``input`` and its ``normalized`` form.
    """
    return {"input": name, "normalized": skill_normalize(name)}


@mcp.tool()
def resolve_skill_alias(term: str) -> dict[str, Any]:
    """Resolve a term (canonical name or alias) to its canonical skill name.

    Useful for checking whether a given word is recognized by the vocabulary and,
    if so, which canonical skill it maps to (e.g. ``"k8s" -> "kubernetes"``).

    Args:
        term: The term to look up. It is normalized before lookup, so matching
            is case-insensitive and whitespace-tolerant.

    Returns:
        A dict with:
          - ``term``: the original input.
          - ``normalized``: its normalized form.
          - ``recognized``: whether the term is in the vocabulary.
          - ``canonical``: the canonical skill name, or ``None`` if unknown.
    """
    normalized = skill_normalize(term)
    canonical = canonical_for(term)
    return {
        "term": term,
        "normalized": normalized,
        "recognized": canonical is not None,
        "canonical": canonical,
    }


@mcp.tool()
def preview_required_skills(job_description: str) -> dict[str, Any]:
    """Preview the weighted required skills extracted from a job description.

    Runs the deterministic ``extract_required_skills`` kernel function so you can
    see exactly what the analyzer would identify (and with what importance
    weights) for a given job-description text. Read-only: nothing is persisted.

    Args:
        job_description: Raw target job-description text.

    Returns:
        A dict with:
          - ``count``: number of distinct required skills identified.
          - ``required_skills``: a list of ``{"name", "weight"}`` entries, sorted
            by normalized name (weight is on the inclusive 1..5 scale).
    """
    required = extract_required_skills(job_description)
    return {
        "count": len(required),
        "required_skills": [
            {"name": rs.name, "weight": rs.weight} for rs in required
        ],
    }


def main() -> None:
    """Entry point: run the MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
