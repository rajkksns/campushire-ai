"""Integration test proving the repository is immune to SQL injection because
every SQLite access uses bound ``?`` parameters (Task 8.4).

Requirements covered:

* **23.2** — all SQLite access uses bound ``?`` parameters, so a value that
  *looks like* SQL is stored and returned as inert data, never executed.
* **23.1** — user-controlled input cannot be interpreted as SQL; a classic
  ``'; DROP TABLE skill; --`` payload placed in a skill ``name`` is persisted
  verbatim and does not alter the schema.

These are I/O integration tests (not property tests): they use a real on-disk
SQLite file via ``tmp_path`` so the payload travels through the same
connection/parameter-binding path production uses. Normalization is kept
self-contained (a simple lowercase/trim) so this file never imports the kernel.
"""

from __future__ import annotations

import sqlite3

from app.repository.repository import (
    ProfileRecord,
    Repository,
    SkillRecord,
)

# The canonical injection payload from the task. If bound parameters were NOT
# used, the "; DROP TABLE skill; --" fragment would end the INSERT statement and
# drop the table; with bound parameters it is stored as an ordinary string.
INJECTION = "'; DROP TABLE skill; --"

# Every table the schema is expected to define (Requirement 23.1: nothing else
# gets dropped either).
EXPECTED_TABLES = {
    "student_profile",
    "skill",
    "certification",
    "academic_project",
    "resume",
    "analysis",
}


# --------------------------------------------------------------------------- #
# Helpers (self-contained — no kernel import)
# --------------------------------------------------------------------------- #
def _normalize(name: str) -> str:
    """Minimal self-contained normalization (lowercase + trim), sufficient to
    satisfy the ``skill`` table's NOT NULL ``normalized`` column without pulling
    in the kernel."""
    return name.strip().lower()


def _table_names(db_path: str) -> set[str]:
    """Return the set of table names via a short-lived, READ-ONLY verification
    connection.

    The repository intentionally exposes no raw SQL, so ``sqlite_master`` is
    queried through a separate connection opened purely for assertions. It is
    read-only and closed immediately.
    """
    check = sqlite3.connect(db_path)
    try:
        rows = check.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        check.close()


# --------------------------------------------------------------------------- #
# 1. Injection payload in a skill NAME (primary case)
# --------------------------------------------------------------------------- #
def test_injection_in_skill_name_is_stored_verbatim_and_table_survives(tmp_path):
    """A ``'; DROP TABLE skill; --`` skill name is persisted as inert data: the
    ``skill`` table survives, the name reads back byte-for-byte, and a normal
    skill can still be inserted afterward (Requirements 23.1, 23.2)."""
    db_path = str(tmp_path / "campushire.db")
    profile_id = "profile-1"

    repo = Repository(db_path)
    repo.initialize_schema()
    try:
        repo.create_profile(
            ProfileRecord(
                id=profile_id,
                name="Ada Lovelace",
                created_at="2026-01-15T09:00:00Z",
            )
        )

        malicious = SkillRecord(
            id="skill-injection",
            profile_id=profile_id,
            name=INJECTION,
            normalized=_normalize(INJECTION),
            skill_type="technical",
            proficiency=3,
        )
        repo.add_skill(malicious)

        # The `skill` table must still exist — the DROP TABLE did NOT execute.
        assert "skill" in _table_names(db_path)

        # The malicious row was stored, and the name is returned VERBATIM.
        fetched = repo.get_skill("skill-injection")
        assert fetched is not None
        assert fetched.name == INJECTION  # byte-for-byte equal, no truncation
        assert fetched == malicious

        # It also comes back through the list path unchanged.
        listed = repo.list_skills(profile_id)
        assert listed == [malicious]

        # The table remains fully usable: a normal skill inserts and reads back.
        normal = SkillRecord(
            id="skill-normal",
            profile_id=profile_id,
            name="Python",
            normalized=_normalize("Python"),
            skill_type="technical",
            proficiency=4,
        )
        repo.add_skill(normal)
        assert repo.get_skill("skill-normal") == normal
    finally:
        repo.close()

    # After the connection is closed and the file re-opened, the injection row
    # is still intact and the schema is unchanged.
    reopened = Repository(db_path)
    try:
        again = reopened.get_skill("skill-injection")
        assert again is not None
        assert again.name == INJECTION
    finally:
        reopened.close()

    assert "skill" in _table_names(db_path)


# --------------------------------------------------------------------------- #
# 2. Injection payload used on READ / lookup paths
# --------------------------------------------------------------------------- #
def test_injection_in_lookup_paths_matches_nothing_and_does_not_raise(tmp_path):
    """Passing an injection string to lookup methods (``get_profile``,
    ``get_skill``, ``skill_exists``) returns "no match" without raising a SQL
    error and without touching the schema — bound parameters protect reads too
    (Requirements 23.1, 23.2)."""
    db_path = str(tmp_path / "campushire.db")
    profile_id = "profile-1"

    repo = Repository(db_path)
    repo.initialize_schema()
    try:
        repo.create_profile(
            ProfileRecord(
                id=profile_id,
                name="Grace Hopper",
                created_at="2026-01-15T09:00:00Z",
            )
        )
        repo.add_skill(
            SkillRecord(
                id="skill-1",
                profile_id=profile_id,
                name="Python",
                normalized=_normalize("Python"),
                skill_type="technical",
                proficiency=4,
            )
        )

        # Injection-style arguments on lookup paths simply find nothing.
        assert repo.get_profile(INJECTION) is None
        assert repo.get_skill(INJECTION) is None
        assert repo.skill_exists("technical", INJECTION, INJECTION) is False
        assert repo.skill_exists(INJECTION, INJECTION, INJECTION) is False

        # A legitimate lookup still works, proving the data is untouched.
        assert repo.skill_exists("technical", _normalize("Python"), profile_id) is True
    finally:
        repo.close()

    # No table was dropped by any lookup attempt.
    assert "skill" in _table_names(db_path)


# --------------------------------------------------------------------------- #
# 3. No table anywhere in the schema was dropped
# --------------------------------------------------------------------------- #
def test_full_schema_intact_after_injection_attempts(tmp_path):
    """After storing an injection payload, the complete expected set of tables
    still exists — the payload dropped nothing (Requirement 23.1)."""
    db_path = str(tmp_path / "campushire.db")
    profile_id = "profile-1"

    repo = Repository(db_path)
    repo.initialize_schema()
    try:
        repo.create_profile(
            ProfileRecord(
                id=profile_id,
                name="Katherine Johnson",
                created_at="2026-01-15T09:00:00Z",
            )
        )
        repo.add_skill(
            SkillRecord(
                id="skill-injection",
                profile_id=profile_id,
                name=INJECTION,
                normalized=_normalize(INJECTION),
                skill_type="soft",
                proficiency=2,
            )
        )
    finally:
        repo.close()

    tables = _table_names(db_path)
    assert EXPECTED_TABLES.issubset(tables), (
        f"expected all schema tables to survive; missing "
        f"{EXPECTED_TABLES - tables}"
    )
