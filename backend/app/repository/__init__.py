"""Persistence layer: parameterized SQLite repository.

Re-exports the public repository API so callers (the service layer) can import
from ``app.repository`` directly, e.g. ``from app.repository import Repository``.
"""

from __future__ import annotations

from .repository import (
    AnalysisRecord,
    CertificationRecord,
    ProfileRecord,
    ProjectRecord,
    Repository,
    ResumeRecord,
    SkillRecord,
)

__all__ = [
    "Repository",
    "ProfileRecord",
    "SkillRecord",
    "CertificationRecord",
    "ProjectRecord",
    "ResumeRecord",
    "AnalysisRecord",
]
