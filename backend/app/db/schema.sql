-- CampusHire AI — SQLite schema (Requirements 16.1, 16.3, 2.6, 23.2).
--
-- Design notes:
--   * Every foreign key uses ON DELETE CASCADE so deleting a Student_Profile
--     removes all owned skills, certifications, projects, resume, and analyses
--     (Requirement 16.3). Cascades require `PRAGMA foreign_keys = ON` per
--     connection, which the repository enables.
--   * CHECK constraints enforce non-empty (trimmed) names/titles, the 1..5
--     proficiency range, the technical/soft skill type, and the 0..100 score.
--   * The `skill` table's UNIQUE (profile_id, skill_type, normalized) constraint
--     enforces case-insensitive duplicate rejection of same-type skills on the
--     same profile (Requirement 2.6); `normalized` stores skill_normalize(name).
--   * `resume` is keyed by `profile_id` so exactly one resume exists per profile
--     (Requirement 5.6).
--   * All access is via bound `?` parameters in the repository (Requirement
--     23.2); this file contains only static DDL.

CREATE TABLE IF NOT EXISTS student_profile (
    id          TEXT PRIMARY KEY,                       -- UUID
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill (
    id            TEXT PRIMARY KEY,
    profile_id    TEXT NOT NULL
                    REFERENCES student_profile(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    normalized    TEXT NOT NULL,                         -- skill_normalize(name)
    skill_type    TEXT NOT NULL CHECK (skill_type IN ('technical', 'soft')),
    proficiency   INTEGER NOT NULL DEFAULT 1
                    CHECK (proficiency BETWEEN 1 AND 5),
    UNIQUE (profile_id, skill_type, normalized)          -- case-insensitive dedupe (2.6)
);

CREATE TABLE IF NOT EXISTS certification (
    id          TEXT PRIMARY KEY,
    profile_id  TEXT NOT NULL
                  REFERENCES student_profile(id) ON DELETE CASCADE,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS academic_project (
    id          TEXT PRIMARY KEY,
    profile_id  TEXT NOT NULL
                  REFERENCES student_profile(id) ON DELETE CASCADE,
    title       TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT
);

CREATE TABLE IF NOT EXISTS resume (
    profile_id  TEXT PRIMARY KEY
                  REFERENCES student_profile(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,                           -- one resume per profile (5.6)
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis (
    id                  TEXT PRIMARY KEY,
    profile_id          TEXT NOT NULL
                          REFERENCES student_profile(id) ON DELETE CASCADE,
    job_description     TEXT NOT NULL,
    readiness_score     INTEGER NOT NULL
                          CHECK (readiness_score BETWEEN 0 AND 100),
    breakdown_json      TEXT NOT NULL,                   -- serialized Score_Breakdown
    categorization_json TEXT NOT NULL,                   -- matched/weak/missing lists
    roadmap_json        TEXT NOT NULL,                   -- ordered Learning_Roadmap
    created_at          TEXT NOT NULL
);

-- Helpful indexes for the common "list owned rows for a profile" queries.
CREATE INDEX IF NOT EXISTS idx_skill_profile ON skill (profile_id);
CREATE INDEX IF NOT EXISTS idx_certification_profile ON certification (profile_id);
CREATE INDEX IF NOT EXISTS idx_academic_project_profile ON academic_project (profile_id);
CREATE INDEX IF NOT EXISTS idx_analysis_profile ON analysis (profile_id);
