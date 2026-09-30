"""Shared normalization helper for the pure analysis kernel.

This module is intentionally dependency-free: it imports only the standard
library (``re``) and performs no I/O. It must never import FastAPI, sqlite3,
or any adapter code, preserving the kernel's determinism and testability
(Requirement 20).
"""

import re

__all__ = ["skill_normalize"]


def skill_normalize(name: str) -> str:
    """Canonical form for case-insensitive, whitespace-tolerant matching.

    Trims leading/trailing whitespace, collapses internal whitespace runs to a
    single space, and lowercases the result.

    The function is pure and idempotent:
    ``skill_normalize(skill_normalize(x)) == skill_normalize(x)``, and invariant
    to letter case and to surrounding/internal whitespace.

    Args:
        name: The raw skill name to normalize.

    Returns:
        The canonical, normalized form of ``name``.
    """
    return re.sub(r"\s+", " ", name).strip().lower()
