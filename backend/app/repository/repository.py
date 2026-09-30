"""Parameterized SQLite repository (Requirements 16.1, 16.2, 16.3, 23.2).

This is a persistence adapter, not business logic: it stores and retrieves rows
using bound ``?`` parameters exclusively (never string-formatted SQL, satisfying
23.2). Validation, duplicate/precedence rules, and orchestration live in the
service layer per the design's layered architecture.

Key behaviors:
    * ``connect`` returns a connection with ``PRAGMA foreign_keys = ON`` so the
      ``ON DELETE CASCADE`` foreign keys actually cascade (16.3).
    * ``initialize`` executes the DDL in ``app/db/schema.sql`` (idempotent via
      ``CREATE TABLE IF NOT EXISTS``), so a fresh database is ready on startup.
    * A single ``Repository`` instance owns one connection to a database file (or
      an in-memory database for tests). Data persists across restarts because the
      file lives on disk / a mounted volume (16.2).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ProfileRow",
    "SkillRow",
    "CertificationRow",
    "ProjectRow",
    "ResumeRow",
    "AnalysisRow",
    "Repository",
]

# Location of the schema DDL relative to this file: app/repository/ -> app/db/.
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


# ---------------------------------------------------------------------------
# Row dataclasses — plain data carriers mirroring the schema tables.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProfileRow:
    id: str
    name: str
    created_at: str


@dataclass(frozen=True)
class SkillRow:
    id: str
    profile_id: str
    name: str
    normalized: str
    skill_type: str
    proficiency: int


@dataclass(frozen=True)
class CertificationRow:
    id: str
    profile_id: str
    name: str


@dataclass(frozen=True)
class ProjectRow:
    id: str
    profile_id: str
    title: str
    description: str | None


@dataclass(frozen=True)
class ResumeRow:
    profile_id: str
    content: str
    updated_at: str


@dataclass(frozen=True)
class AnalysisRow:
    id: str
    profile_id: str
    job_description: str
    readiness_score: int
    breakdown_json: str
    categorization_json: str
    roadmap_json: str
    created_at: str


class Repository:
    """Owns a single SQLite connection and exposes parameterized CRUD methods.

    Args:
        database_path: Filesystem path to the SQLite database, or ``":memory:"``
            for an ephemeral in-memory database (useful in tests).
    """

    def __init__(self, database_path: str = ":memory:") -> None:
        self._database_path = database_path
        self._conn = self._connect(database_path)

    # -- connection / lifecycle ---------------------------------------------
    @staticmethod
    def _connect(database_path: str) -> sqlite3.Connection:
        """Open a connection with foreign-key enforcement and row access by name.

        ``PRAGMA foreign_keys = ON`` is required per connection for the
        ``ON DELETE CASCADE`` constraints to take effect (16.3).
        """
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying SQLite connection."""
        return self._conn

    def initialize(self) -> None:
        """Create the schema if it does not already exist (idempotent).

        Executes the DDL in ``app/db/schema.sql``. Safe to call on every startup
        because the DDL uses ``CREATE TABLE IF NOT EXISTS``.
        """
        ddl = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(ddl)
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    # -- Student_Profile ----------------------------------------------------
    def create_profile(self, profile: ProfileRow) -> ProfileRow:
        self._conn.execute(
            "INSERT INTO student_profile (id, name, created_at) VALUES (?, ?, ?)",
            (profile.id, profile.name, profile.created_at),
        )
        self._conn.commit()
        return profile

    def get_profile(self, profile_id: str) -> ProfileRow | None:
        row = self._conn.execute(
            "SELECT id, name, created_at FROM student_profile WHERE id = ?",
            (profile_id,),
        ).fetchone()
        return _to_profile(row) if row else None

    def update_profile_name(self, profile_id: str, name: str) -> ProfileRow | None:
        cur = self._conn.execute(
            "UPDATE student_profile SET name = ? WHERE id = ?",
            (name, profile_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            return None
        return self.get_profile(profile_id)

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile; cascades remove all owned rows (16.3)."""
        cur = self._conn.execute(
            "DELETE FROM student_profile WHERE id = ?", (profile_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    # -- Skill --------------------------------------------------------------
    def add_skill(self, skill: SkillRow) -> SkillRow:
        """Insert a skill. Raises ``sqlite3.IntegrityError`` on a case-insensitive
        duplicate of the same type on the same profile (the UNIQUE constraint);
        the service layer maps that to a 409 conflict."""
        self._conn.execute(
            "INSERT INTO skill (id, profile_id, name, normalized, skill_type, "
            "proficiency) VALUES (?, ?, ?, ?, ?, ?)",
            (
                skill.id,
                skill.profile_id,
                skill.name,
                skill.normalized,
                skill.skill_type,
                skill.proficiency,
            ),
        )
        self._conn.commit()
        return skill

    def get_skill(self, skill_id: str) -> SkillRow | None:
        row = self._conn.execute(
            "SELECT id, profile_id, name, normalized, skill_type, proficiency "
            "FROM skill WHERE id = ?",
            (skill_id,),
        ).fetchone()
        return _to_skill(row) if row else None

    def list_skills(self, profile_id: str) -> list[SkillRow]:
        rows = self._conn.execute(
            "SELECT id, profile_id, name, normalized, skill_type, proficiency "
            "FROM skill WHERE profile_id = ? ORDER BY skill_type, normalized",
            (profile_id,),
        ).fetchall()
        return [_to_skill(r) for r in rows]

    def skill_exists(
        self, profile_id: str, skill_type: str, normalized: str
    ) -> bool:
        """Whether a same-type skill with this normalized name already exists.

        Lets the service check duplicates explicitly (for 409) rather than
        relying solely on the IntegrityError.
        """
        row = self._conn.execute(
            "SELECT 1 FROM skill WHERE profile_id = ? AND skill_type = ? "
            "AND normalized = ? LIMIT 1",
            (profile_id, skill_type, normalized),
        ).fetchone()
        return row is not None

    def delete_skill(self, skill_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM skill WHERE id = ?", (skill_id,))
        self._conn.commit()
        return cur.rowcount > 0

    # -- Certification ------------------------------------------------------
    def add_certification(self, cert: CertificationRow) -> CertificationRow:
        self._conn.execute(
            "INSERT INTO certification (id, profile_id, name) VALUES (?, ?, ?)",
            (cert.id, cert.profile_id, cert.name),
        )
        self._conn.commit()
        return cert

    def get_certification(self, cert_id: str) -> CertificationRow | None:
        row = self._conn.execute(
            "SELECT id, profile_id, name FROM certification WHERE id = ?",
            (cert_id,),
        ).fetchone()
        return _to_certification(row) if row else None

    def list_certifications(self, profile_id: str) -> list[CertificationRow]:
        rows = self._conn.execute(
            "SELECT id, profile_id, name FROM certification WHERE profile_id = ? "
            "ORDER BY name",
            (profile_id,),
        ).fetchall()
        return [_to_certification(r) for r in rows]

    def delete_certification(self, cert_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM certification WHERE id = ?", (cert_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    # -- Academic_Project ---------------------------------------------------
    def add_project(self, project: ProjectRow) -> ProjectRow:
        self._conn.execute(
            "INSERT INTO academic_project (id, profile_id, title, description) "
            "VALUES (?, ?, ?, ?)",
            (project.id, project.profile_id, project.title, project.description),
        )
        self._conn.commit()
        return project

    def get_project(self, project_id: str) -> ProjectRow | None:
        row = self._conn.execute(
            "SELECT id, profile_id, title, description FROM academic_project "
            "WHERE id = ?",
            (project_id,),
        ).fetchone()
        return _to_project(row) if row else None

    def list_projects(self, profile_id: str) -> list[ProjectRow]:
        rows = self._conn.execute(
            "SELECT id, profile_id, title, description FROM academic_project "
            "WHERE profile_id = ? ORDER BY title",
            (profile_id,),
        ).fetchall()
        return [_to_project(r) for r in rows]

    def delete_project(self, project_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM academic_project WHERE id = ?", (project_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    # -- Resume (single row per profile, 5.6) -------------------------------
    def upsert_resume(self, resume: ResumeRow) -> ResumeRow:
        """Insert or replace the resume for a profile (one row per profile).

        Uses an explicit UPSERT on the ``profile_id`` primary key so submitting a
        new resume replaces the prior text (Requirement 5.6).
        """
        self._conn.execute(
            "INSERT INTO resume (profile_id, content, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(profile_id) DO UPDATE SET "
            "content = excluded.content, updated_at = excluded.updated_at",
            (resume.profile_id, resume.content, resume.updated_at),
        )
        self._conn.commit()
        return resume

    def get_resume(self, profile_id: str) -> ResumeRow | None:
        row = self._conn.execute(
            "SELECT profile_id, content, updated_at FROM resume WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return _to_resume(row) if row else None

    # -- Analysis -----------------------------------------------------------
    def create_analysis(self, analysis: AnalysisRow) -> AnalysisRow:
        self._conn.execute(
            "INSERT INTO analysis (id, profile_id, job_description, "
            "readiness_score, breakdown_json, categorization_json, roadmap_json, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
        self._conn.commit()
        return analysis

    def get_analysis(self, analysis_id: str) -> AnalysisRow | None:
        row = self._conn.execute(
            "SELECT id, profile_id, job_description, readiness_score, "
            "breakdown_json, categorization_json, roadmap_json, created_at "
            "FROM analysis WHERE id = ?",
            (analysis_id,),
        ).fetchone()
        return _to_analysis(row) if row else None

    def list_analyses(self, profile_id: str) -> list[AnalysisRow]:
        rows = self._conn.execute(
            "SELECT id, profile_id, job_description, readiness_score, "
            "breakdown_json, categorization_json, roadmap_json, created_at "
            "FROM analysis WHERE profile_id = ? ORDER BY created_at, id",
            (profile_id,),
        ).fetchall()
        return [_to_analysis(r) for r in rows]


# ---------------------------------------------------------------------------
# Row -> dataclass mappers (kept module-private for clarity).
# ---------------------------------------------------------------------------
def _to_profile(row: sqlite3.Row) -> ProfileRow:
    return ProfileRow(id=row["id"], name=row["name"], created_at=row["created_at"])


def _to_skill(row: sqlite3.Row) -> SkillRow:
    return SkillRow(
        id=row["id"],
        profile_id=row["profile_id"],
        name=row["name"],
        normalized=row["normalized"],
        skill_type=row["skill_type"],
        proficiency=row["proficiency"],
    )


def _to_certification(row: sqlite3.Row) -> CertificationRow:
    return CertificationRow(
        id=row["id"], profile_id=row["profile_id"], name=row["name"]
    )


def _to_project(row: sqlite3.Row) -> ProjectRow:
    return ProjectRow(
        id=row["id"],
        profile_id=row["profile_id"],
        title=row["title"],
        description=row["description"],
    )


def _to_resume(row: sqlite3.Row) -> ResumeRow:
    return ResumeRow(
        profile_id=row["profile_id"],
        content=row["content"],
        updated_at=row["updated_at"],
    )


def _to_analysis(row: sqlite3.Row) -> AnalysisRow:
    return AnalysisRow(
        id=row["id"],
        profile_id=row["profile_id"],
        job_description=row["job_description"],
        readiness_score=row["readiness_score"],
        breakdown_json=row["breakdown_json"],
        categorization_json=row["categorization_json"],
        roadmap_json=row["roadmap_json"],
        created_at=row["created_at"],
    )
