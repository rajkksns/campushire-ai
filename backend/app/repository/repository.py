"""Parameterized SQLite repository (Task 8.2).

This module is the sole persistence adapter for CampusHire AI. It owns all
SQLite access and follows two hard rules from the steering docs:

* **All SQL uses bound ``?`` parameters** — never string-formatted SQL — so
  user-controlled values can never be interpreted as SQL (Requirements 23.1,
  23.2).
* **Foreign keys are enforced per connection** via ``PRAGMA foreign_keys = ON``
  so ``ON DELETE CASCADE`` removes all rows owned by a deleted profile
  (Requirement 16.3).

The schema is loaded from ``app/db/schema.sql`` and initialized on startup
(Requirement 16.1). The repository stores and returns plain, immutable record
dataclasses; it contains no analysis/business logic (that lives in the pure
kernel and the service layer) — it is a thin I/O adapter per the layered
dependency direction (routers → services → repository).

Records survive process/container restarts because the database is a file on a
mounted volume (Requirement 16.2); nothing here holds state beyond the open
connection.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ProfileRecord",
    "SkillRecord",
    "CertificationRecord",
    "ProjectRecord",
    "ResumeRecord",
    "AnalysisRecord",
    "Repository",
]

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


# --------------------------------------------------------------------------- #
# Record types
#
# Plain, immutable row projections. These mirror the columns in schema.sql and
# carry no behavior; they exist so callers (the service layer) get typed data
# instead of raw tuples/rows. They are deliberately independent of the kernel
# dataclasses so persistence and analysis stay decoupled.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProfileRecord:
    """A ``student_profile`` row."""

    id: str
    name: str
    created_at: str


@dataclass(frozen=True)
class SkillRecord:
    """A ``skill`` row. ``normalized`` is ``skill_normalize(name)`` supplied by
    the caller (the service layer), keeping normalization a single kernel rule.
    """

    id: str
    profile_id: str
    name: str
    normalized: str
    skill_type: str
    proficiency: int


@dataclass(frozen=True)
class CertificationRecord:
    """A ``certification`` row."""

    id: str
    profile_id: str
    name: str


@dataclass(frozen=True)
class ProjectRecord:
    """An ``academic_project`` row."""

    id: str
    profile_id: str
    title: str
    description: str | None


@dataclass(frozen=True)
class ResumeRecord:
    """A ``resume`` row (exactly one per profile)."""

    profile_id: str
    content: str
    updated_at: str


@dataclass(frozen=True)
class AnalysisRecord:
    """An ``analysis`` row. The derived JSON columns store the fully
    materialized result so it can be read back without recomputation
    (Requirements 13.1–13.4).
    """

    id: str
    profile_id: str
    job_description: str
    readiness_score: int
    breakdown_json: str
    categorization_json: str
    roadmap_json: str
    created_at: str


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #
class Repository:
    """Parameterized SQLite data-access layer.

    A single instance owns one :class:`sqlite3.Connection`. Every method uses
    bound ``?`` parameters exclusively. ``PRAGMA foreign_keys = ON`` is enabled
    on the connection so cascade deletes work as declared in the schema.
    """

    def __init__(self, database_path: str) -> None:
        """Open (or create) the database at ``database_path``.

        Args:
            database_path: Filesystem path to the SQLite file, or
                ``":memory:"`` for an ephemeral database (used by tests). The
                path is passed straight to :func:`sqlite3.connect`; it is not a
                SQL value, so there is no injection surface here.
        """
        # check_same_thread=False keeps the connection usable from FastAPI's
        # threadpool workers; access is otherwise serialized by SQLite.
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Enforce foreign keys for THIS connection so ON DELETE CASCADE fires
        # (Requirement 16.3). PRAGMA cannot be parameterized and takes no user
        # input, so a literal statement is correct and safe here.
        self._conn.execute("PRAGMA foreign_keys = ON")

    # -- lifecycle -------------------------------------------------------- #
    def initialize_schema(self) -> None:
        """Create all tables/indexes if absent by executing ``schema.sql``.

        Idempotent: the DDL uses ``CREATE TABLE IF NOT EXISTS`` so calling this
        on startup is safe whether the database is new or already populated
        (Requirement 16.1).
        """
        ddl = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self._conn:
            self._conn.executescript(ddl)

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def __enter__(self) -> Repository:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- profiles --------------------------------------------------------- #
    def create_profile(self, profile: ProfileRecord) -> ProfileRecord:
        """Insert a new profile and return it."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO student_profile (id, name, created_at) "
                "VALUES (?, ?, ?)",
                (profile.id, profile.name, profile.created_at),
            )
        return profile

    def get_profile(self, profile_id: str) -> ProfileRecord | None:
        """Return the profile with ``profile_id`` or ``None`` if absent."""
        row = self._conn.execute(
            "SELECT id, name, created_at FROM student_profile WHERE id = ?",
            (profile_id,),
        ).fetchone()
        return _to_profile(row) if row is not None else None

    def list_profiles(self) -> list[ProfileRecord]:
        """Return all profiles ordered by name then id (deterministic)."""
        rows = self._conn.execute(
            "SELECT id, name, created_at FROM student_profile "
            "ORDER BY name ASC, id ASC"
        ).fetchall()
        return [_to_profile(r) for r in rows]

    def update_profile_name(self, profile_id: str, name: str) -> bool:
        """Rename a profile. Returns ``True`` if a row was updated."""
        with self._conn:
            cur = self._conn.execute(
                "UPDATE student_profile SET name = ? WHERE id = ?",
                (name, profile_id),
            )
        return cur.rowcount > 0

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile; owned rows cascade. Returns ``True`` if removed."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM student_profile WHERE id = ?",
                (profile_id,),
            )
        return cur.rowcount > 0

    # -- skills ----------------------------------------------------------- #
    def add_skill(self, skill: SkillRecord) -> SkillRecord:
        """Insert a skill.

        Raises:
            sqlite3.IntegrityError: if the ``(profile_id, skill_type,
                normalized)`` uniqueness constraint is violated. The service
                layer maps this to a 409 conflict (Requirement 2.6).
        """
        with self._conn:
            self._conn.execute(
                "INSERT INTO skill "
                "(id, profile_id, name, normalized, skill_type, proficiency) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    skill.id,
                    skill.profile_id,
                    skill.name,
                    skill.normalized,
                    skill.skill_type,
                    skill.proficiency,
                ),
            )
        return skill

    def get_skill(self, skill_id: str) -> SkillRecord | None:
        """Return a single skill by id, or ``None``."""
        row = self._conn.execute(
            "SELECT id, profile_id, name, normalized, skill_type, proficiency "
            "FROM skill WHERE id = ?",
            (skill_id,),
        ).fetchone()
        return _to_skill(row) if row is not None else None

    def list_skills(self, profile_id: str) -> list[SkillRecord]:
        """Return a profile's skills in a deterministic order."""
        rows = self._conn.execute(
            "SELECT id, profile_id, name, normalized, skill_type, proficiency "
            "FROM skill WHERE profile_id = ? "
            "ORDER BY skill_type ASC, normalized ASC, id ASC",
            (profile_id,),
        ).fetchall()
        return [_to_skill(r) for r in rows]

    def skill_exists(self, skill_type: str, normalized: str, profile_id: str) -> bool:
        """Return whether a same-type, same-normalized skill already exists."""
        row = self._conn.execute(
            "SELECT 1 FROM skill "
            "WHERE profile_id = ? AND skill_type = ? AND normalized = ? "
            "LIMIT 1",
            (profile_id, skill_type, normalized),
        ).fetchone()
        return row is not None

    def delete_skill(self, profile_id: str, skill_id: str) -> bool:
        """Delete a skill owned by ``profile_id``. Returns ``True`` if removed."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM skill WHERE id = ? AND profile_id = ?",
                (skill_id, profile_id),
            )
        return cur.rowcount > 0

    # -- certifications --------------------------------------------------- #
    def add_certification(self, cert: CertificationRecord) -> CertificationRecord:
        """Insert a certification."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO certification (id, profile_id, name) "
                "VALUES (?, ?, ?)",
                (cert.id, cert.profile_id, cert.name),
            )
        return cert

    def list_certifications(self, profile_id: str) -> list[CertificationRecord]:
        """Return a profile's certifications in a deterministic order."""
        rows = self._conn.execute(
            "SELECT id, profile_id, name FROM certification "
            "WHERE profile_id = ? ORDER BY name ASC, id ASC",
            (profile_id,),
        ).fetchall()
        return [_to_certification(r) for r in rows]

    def delete_certification(self, profile_id: str, cert_id: str) -> bool:
        """Delete a certification owned by ``profile_id``."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM certification WHERE id = ? AND profile_id = ?",
                (cert_id, profile_id),
            )
        return cur.rowcount > 0

    # -- projects --------------------------------------------------------- #
    def add_project(self, project: ProjectRecord) -> ProjectRecord:
        """Insert an academic project."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO academic_project (id, profile_id, title, description) "
                "VALUES (?, ?, ?, ?)",
                (project.id, project.profile_id, project.title, project.description),
            )
        return project

    def list_projects(self, profile_id: str) -> list[ProjectRecord]:
        """Return a profile's projects in a deterministic order."""
        rows = self._conn.execute(
            "SELECT id, profile_id, title, description FROM academic_project "
            "WHERE profile_id = ? ORDER BY title ASC, id ASC",
            (profile_id,),
        ).fetchall()
        return [_to_project(r) for r in rows]

    def delete_project(self, profile_id: str, project_id: str) -> bool:
        """Delete a project owned by ``profile_id``."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM academic_project WHERE id = ? AND profile_id = ?",
                (project_id, profile_id),
            )
        return cur.rowcount > 0

    # -- resume (single row per profile) ---------------------------------- #
    def upsert_resume(self, resume: ResumeRecord) -> ResumeRecord:
        """Insert or replace the profile's single resume (Requirement 5.6).

        The ``resume`` table is keyed by ``profile_id``; an ``ON CONFLICT``
        upsert replaces any prior content so exactly one resume exists per
        profile.
        """
        with self._conn:
            self._conn.execute(
                "INSERT INTO resume (profile_id, content, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(profile_id) DO UPDATE SET "
                "content = excluded.content, updated_at = excluded.updated_at",
                (resume.profile_id, resume.content, resume.updated_at),
            )
        return resume

    def get_resume(self, profile_id: str) -> ResumeRecord | None:
        """Return the profile's resume, or ``None`` if none exists."""
        row = self._conn.execute(
            "SELECT profile_id, content, updated_at FROM resume WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return _to_resume(row) if row is not None else None

    def delete_resume(self, profile_id: str) -> bool:
        """Delete the profile's resume. Returns ``True`` if one was removed."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM resume WHERE profile_id = ?",
                (profile_id,),
            )
        return cur.rowcount > 0

    # -- analyses --------------------------------------------------------- #
    def create_analysis(self, analysis: AnalysisRecord) -> AnalysisRecord:
        """Persist a fully materialized analysis (Requirements 13.1–13.4)."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO analysis "
                "(id, profile_id, job_description, readiness_score, "
                "breakdown_json, categorization_json, roadmap_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    analysis.id,
                    analysis.profile_id,
                    analysis.job_description,
                    analysis.readiness_score,
                    analysis.breakdown_json,
                    analysis.categorization_json,
                    analysis.roadmap_json,
                    analysis.created_at,
                ),
            )
        return analysis

    def get_analysis(self, analysis_id: str) -> AnalysisRecord | None:
        """Return a persisted analysis by id, or ``None`` (Requirement 13.2)."""
        row = self._conn.execute(
            "SELECT id, profile_id, job_description, readiness_score, "
            "breakdown_json, categorization_json, roadmap_json, created_at "
            "FROM analysis WHERE id = ?",
            (analysis_id,),
        ).fetchone()
        return _to_analysis(row) if row is not None else None

    def list_analyses(self, profile_id: str) -> list[AnalysisRecord]:
        """Return a profile's analyses, newest first, id-tiebroken (13.4)."""
        rows = self._conn.execute(
            "SELECT id, profile_id, job_description, readiness_score, "
            "breakdown_json, categorization_json, roadmap_json, created_at "
            "FROM analysis WHERE profile_id = ? "
            "ORDER BY created_at DESC, id ASC",
            (profile_id,),
        ).fetchall()
        return [_to_analysis(r) for r in rows]


# --------------------------------------------------------------------------- #
# Row → record mappers (single place each column list is projected)
# --------------------------------------------------------------------------- #
def _to_profile(row: sqlite3.Row) -> ProfileRecord:
    return ProfileRecord(id=row["id"], name=row["name"], created_at=row["created_at"])


def _to_skill(row: sqlite3.Row) -> SkillRecord:
    return SkillRecord(
        id=row["id"],
        profile_id=row["profile_id"],
        name=row["name"],
        normalized=row["normalized"],
        skill_type=row["skill_type"],
        proficiency=row["proficiency"],
    )


def _to_certification(row: sqlite3.Row) -> CertificationRecord:
    return CertificationRecord(
        id=row["id"], profile_id=row["profile_id"], name=row["name"]
    )


def _to_project(row: sqlite3.Row) -> ProjectRecord:
    return ProjectRecord(
        id=row["id"],
        profile_id=row["profile_id"],
        title=row["title"],
        description=row["description"],
    )


def _to_resume(row: sqlite3.Row) -> ResumeRecord:
    return ResumeRecord(
        profile_id=row["profile_id"],
        content=row["content"],
        updated_at=row["updated_at"],
    )


def _to_analysis(row: sqlite3.Row) -> AnalysisRecord:
    return AnalysisRecord(
        id=row["id"],
        profile_id=row["profile_id"],
        job_description=row["job_description"],
        readiness_score=row["readiness_score"],
        breakdown_json=row["breakdown_json"],
        categorization_json=row["categorization_json"],
        roadmap_json=row["roadmap_json"],
        created_at=row["created_at"],
    )
