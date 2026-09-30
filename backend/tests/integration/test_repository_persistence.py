"""Integration tests for repository persistence, cascade delete, and restart
durability (Task 8.3).

These are I/O integration tests, not property tests: they exercise real
on-disk SQLite persistence via a temporary file (``tmp_path``) rather than an
in-memory database, so durability across a *re-opened* connection is genuinely
exercised.

Requirements covered:

* **16.2** — records persist across a restart (a re-opened connection) byte-for
  -byte unchanged.
* **16.3** — deleting a profile cascades to all owned rows (skills,
  certifications, projects, resume, analyses).
* **13.1** — a persisted analysis is stored with its score, breakdown,
  categorization, and roadmap and reads back with full fidelity.

The tests deliberately keep normalization self-contained (a simple inline
lowercase/trim) and do NOT import the kernel, so this file only ever touches the
persistence adapter under test.
"""

from __future__ import annotations

import json

from app.repository.repository import (
    AnalysisRecord,
    CertificationRecord,
    ProfileRecord,
    ProjectRecord,
    Repository,
    ResumeRecord,
    SkillRecord,
)


# --------------------------------------------------------------------------- #
# Helpers (self-contained — no kernel import)
# --------------------------------------------------------------------------- #
def _normalize(name: str) -> str:
    """Minimal self-contained normalization for the repository test.

    Intentionally NOT the kernel rule: this test only needs a stable
    ``normalized`` value to satisfy the ``skill`` table's NOT NULL / uniqueness
    columns, so a simple lowercase + trim is sufficient and keeps the
    persistence test decoupled from analysis logic.
    """
    return name.strip().lower()


def _skill(profile_id: str) -> SkillRecord:
    return SkillRecord(
        id="skill-1",
        profile_id=profile_id,
        name="Python",
        normalized=_normalize("  Python  "),
        skill_type="technical",
        proficiency=4,
    )


def _certification(profile_id: str) -> CertificationRecord:
    return CertificationRecord(
        id="cert-1",
        profile_id=profile_id,
        name="AWS Certified Developer",
    )


def _project(profile_id: str) -> ProjectRecord:
    return ProjectRecord(
        id="project-1",
        profile_id=profile_id,
        title="Skill Gap Analyzer",
        description="A deterministic placement-readiness tool.",
    )


def _resume(profile_id: str) -> ResumeRecord:
    return ResumeRecord(
        profile_id=profile_id,
        content="Experienced in Python, SQL, and REST API design.",
        updated_at="2026-01-15T09:30:00Z",
    )


def _analysis(profile_id: str) -> AnalysisRecord:
    """A fully-populated analysis with realistic JSON payloads and a valid
    score in [0, 100] (Requirement 13.1)."""
    breakdown = [
        {"skill": "python", "category": "matched", "weight": 3, "points": 40},
        {"skill": "sql", "category": "weak", "weight": 2, "points": 13},
        {"skill": "docker", "category": "missing", "weight": 1, "points": 0},
    ]
    categorization = {
        "matched": ["python"],
        "weak": ["sql"],
        "missing": ["docker"],
    }
    roadmap = [
        {"skill": "docker", "priority": 1, "reason": "missing required skill"},
        {"skill": "sql", "priority": 2, "reason": "weak proficiency"},
    ]
    return AnalysisRecord(
        id="analysis-1",
        profile_id=profile_id,
        job_description="Backend engineer: Python, SQL, Docker.",
        readiness_score=53,
        breakdown_json=json.dumps(breakdown, sort_keys=True),
        categorization_json=json.dumps(categorization, sort_keys=True),
        roadmap_json=json.dumps(roadmap, sort_keys=True),
        created_at="2026-01-15T10:00:00Z",
    )


def _seed_full_profile(repo: Repository, profile_id: str = "profile-1") -> None:
    """Insert a profile plus one of every owned record type."""
    repo.create_profile(
        ProfileRecord(id=profile_id, name="Ada Lovelace", created_at="2026-01-15T09:00:00Z")
    )
    repo.add_skill(_skill(profile_id))
    repo.add_certification(_certification(profile_id))
    repo.add_project(_project(profile_id))
    repo.upsert_resume(_resume(profile_id))
    repo.create_analysis(_analysis(profile_id))


# --------------------------------------------------------------------------- #
# 1. Restart durability (Requirements 16.2, 13.1)
# --------------------------------------------------------------------------- #
def test_records_persist_across_reopened_connection(tmp_path):
    """Everything written by one connection reads back byte-for-byte unchanged
    from a second connection opened against the same on-disk file."""
    db_path = str(tmp_path / "campushire.db")
    profile_id = "profile-1"

    expected_profile = ProfileRecord(
        id=profile_id, name="Ada Lovelace", created_at="2026-01-15T09:00:00Z"
    )
    expected_skill = _skill(profile_id)
    expected_cert = _certification(profile_id)
    expected_project = _project(profile_id)
    expected_resume = _resume(profile_id)
    expected_analysis = _analysis(profile_id)

    # -- first "run": write everything, then close the connection --------- #
    first = Repository(db_path)
    first.initialize_schema()
    first.create_profile(expected_profile)
    first.add_skill(expected_skill)
    first.add_certification(expected_cert)
    first.add_project(expected_project)
    first.upsert_resume(expected_resume)
    first.create_analysis(expected_analysis)
    first.close()

    # -- second "run": re-open the SAME file, schema init is idempotent --- #
    second = Repository(db_path)
    second.initialize_schema()  # idempotent (CREATE TABLE IF NOT EXISTS)
    try:
        assert second.get_profile(profile_id) == expected_profile

        skills = second.list_skills(profile_id)
        assert skills == [expected_skill]

        certs = second.list_certifications(profile_id)
        assert certs == [expected_cert]

        projects = second.list_projects(profile_id)
        assert projects == [expected_project]

        assert second.get_resume(profile_id) == expected_resume

        # Analysis JSON columns + score survive unchanged (Requirement 13.1).
        stored_analysis = second.get_analysis(expected_analysis.id)
        assert stored_analysis == expected_analysis
        assert stored_analysis.readiness_score == expected_analysis.readiness_score
        assert stored_analysis.breakdown_json == expected_analysis.breakdown_json
        assert stored_analysis.categorization_json == expected_analysis.categorization_json
        assert stored_analysis.roadmap_json == expected_analysis.roadmap_json
        assert second.list_analyses(profile_id) == [expected_analysis]
    finally:
        second.close()


# --------------------------------------------------------------------------- #
# 2. Cascade delete (Requirement 16.3)
# --------------------------------------------------------------------------- #
def test_delete_profile_cascades_to_all_owned_rows(tmp_path):
    """Deleting a profile removes every owned skill/cert/project/resume/analysis,
    verified against a freshly re-opened connection so no orphans linger."""
    db_path = str(tmp_path / "campushire.db")
    profile_id = "profile-1"

    repo = Repository(db_path)
    repo.initialize_schema()
    try:
        _seed_full_profile(repo, profile_id)

        # Sanity: owned rows exist before the delete.
        assert repo.get_profile(profile_id) is not None
        assert repo.list_skills(profile_id)
        assert repo.list_certifications(profile_id)
        assert repo.list_projects(profile_id)
        assert repo.get_resume(profile_id) is not None
        assert repo.list_analyses(profile_id)

        # Delete the parent profile; foreign keys are enabled so cascade fires.
        assert repo.delete_profile(profile_id) is True

        # Everything owned is gone on this connection.
        assert repo.get_profile(profile_id) is None
        assert repo.list_skills(profile_id) == []
        assert repo.list_certifications(profile_id) == []
        assert repo.list_projects(profile_id) == []
        assert repo.get_resume(profile_id) is None
        assert repo.list_analyses(profile_id) == []
    finally:
        repo.close()

    # Strong assertion: a brand-new connection sees no orphaned owned rows.
    reopened = Repository(db_path)
    try:
        assert reopened.get_profile(profile_id) is None
        assert reopened.list_skills(profile_id) == []
        assert reopened.list_certifications(profile_id) == []
        assert reopened.list_projects(profile_id) == []
        assert reopened.get_resume(profile_id) is None
        assert reopened.list_analyses(profile_id) == []
    finally:
        reopened.close()


# --------------------------------------------------------------------------- #
# 3. Analysis round-trip fidelity (Requirement 13.1)
# --------------------------------------------------------------------------- #
def test_analysis_round_trip_fidelity(tmp_path):
    """A retrieved AnalysisRecord equals the stored one (frozen dataclass
    equality), including every JSON payload column and the score."""
    db_path = str(tmp_path / "campushire.db")
    profile_id = "profile-1"

    with Repository(db_path) as repo:
        repo.initialize_schema()
        repo.create_profile(
            ProfileRecord(
                id=profile_id, name="Grace Hopper", created_at="2026-01-15T09:00:00Z"
            )
        )
        stored = _analysis(profile_id)
        returned_on_write = repo.create_analysis(stored)

        # The method returns exactly what it stored.
        assert returned_on_write == stored

        # And a subsequent read is byte-for-byte identical.
        fetched = repo.get_analysis(stored.id)
        assert fetched == stored
        assert fetched.readiness_score == stored.readiness_score
        assert fetched.breakdown_json == stored.breakdown_json
        assert fetched.categorization_json == stored.categorization_json
        assert fetched.roadmap_json == stored.roadmap_json

        # The JSON payloads deserialize back to their original structures.
        assert json.loads(fetched.breakdown_json) == json.loads(stored.breakdown_json)
        assert json.loads(fetched.categorization_json) == json.loads(
            stored.categorization_json
        )
        assert json.loads(fetched.roadmap_json) == json.loads(stored.roadmap_json)
