# Implementation Plan: CampusHire AI

## Overview

This plan turns the CampusHire AI design into incremental coding steps. The backend is Python 3.11 + FastAPI + Pydantic v2 with a pure, deterministic analysis kernel; persistence is parameterized SQLite; the frontend is React 18 + TypeScript + Vite. Testing uses pytest + Hypothesis (Properties 1–12 for the pure kernel) plus example/edge/integration/smoke tests, and Vitest/RTL-style component tests for the frontend.

The build order follows the layered architecture: shared kernel first (normalize → extractor → comparator → scoring → roadmap), then persistence, then schemas/services, then routers and error handling, then frontend, then Docker packaging and Kiro-artifact checks. Property tests are placed immediately after the kernel component they validate so determinism/conservation regressions surface early. Tasks that write the same file are separated into different waves (see Task Dependency Graph).

## Tasks

- [x] 1. Scaffold backend project structure and tooling
  - Create `backend/` layout: `app/`, `app/routers/`, `app/services/`, `app/kernel/`, `app/repository/`, `app/schemas/`, `app/db/`, and `tests/{properties,unit,integration}/`
  - Add `backend/pyproject.toml` declaring dependencies (fastapi, uvicorn, pydantic v2, pypdf, pytest, hypothesis) and configuring pytest test paths
  - Create empty `__init__.py` package markers so kernel/services/repository import cleanly
  - _Requirements: 21.5, 20.1_

- [x] 2. Implement the shared normalization helper
  - [x] 2.1 Implement `skill_normalize` in `app/kernel/normalize.py`
    - Trim leading/trailing whitespace, collapse internal whitespace runs to a single space, lowercase
    - Ensure the function is pure (no I/O, no FastAPI/sqlite imports) and idempotent
    - _Requirements: 7.4, 2.6, 8.1_

  - [x]* 2.2 Write property test for normalization
    - **Property 1: Normalization is idempotent and case/whitespace invariant**
    - **Validates: Requirements 7.4, 2.6**
    - Place in `tests/properties/test_normalize_properties.py`, min 100 iterations, tagged with the property number

- [ ] 3. Implement the Skill_Extractor and curated vocabulary
  - [x] 3.1 Define the curated skill vocabulary and alias table in `app/kernel/extractor.py`
    - Static canonical-name → alias-set dictionary versioned in source control for reproducibility
    - _Requirements: 7.1, 7.5_

  - [x] 3.2 Implement `RequiredSkill` dataclass and `extract_required_skills`
    - Whole-token, case-insensitive matching against vocabulary + aliases
    - Deterministic weighting signals (frequency bucketed 1–5, required/must-have boost) clamped to 1..5
    - Normalize names via `skill_normalize`, de-duplicate case-insensitively keeping highest weight, sort by normalized name
    - Return empty list as a valid outcome (no error) when no vocabulary hits
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 3.3 Implement `extract_resume_skills`
    - Derive normalized candidate skill names from resume text using the same vocabulary and normalization; accept `None`/empty input
    - _Requirements: 8.1, 5.2_

  - [x]* 3.4 Write property test for extraction output invariants
    - **Property 2: Extraction output invariants**
    - **Validates: Requirements 7.2, 7.3**

  - [x]* 3.5 Write property test for extraction determinism
    - **Property 3: Extraction is deterministic**
    - **Validates: Requirements 7.5**

- [ ] 4. Implement the Skill_Comparator
  - [x] 4.1 Implement categories, dataclasses, and `compare` in `app/kernel/comparator.py`
    - Define `Category` enum, `StudentSkill`, `ComparedSkill`, and `PROFICIENCY_THRESHOLD = 3`
    - Build a normalized-name → max-proficiency map over the union of declared + resume-derived skills (order-invariant)
    - Categorize each required skill: matched (proficiency ≥ 3), weak (proficiency < 3), missing (no match); sort output by normalized name
    - Guarantee exactly one category per required skill and that category counts sum to the required count
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2, 9.3_

  - [x]* 4.2 Write property test for correct total partition
    - **Property 4: Categorization is a correct total partition**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**

  - [x]* 4.3 Write property test for comparison determinism and order-invariance
    - **Property 5: Comparison is deterministic and order-invariant**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [ ] 5. Implement the Scoring_Engine (largest-remainder / Hamilton)
  - [x] 5.1 Implement scoring dataclasses and the deterministic allocation in `app/kernel/scoring.py`
    - Define `BreakdownItem`, `ScoreResult`, and `CATEGORY_FACTOR` (matched 1.0, weak 0.5, missing 0.0)
    - Handle degenerate cases: empty required set → score 0 + empty breakdown; all-matched → 100; all-missing → 0
    - When total weight is 0, treat every skill as equally weighted (w=1)
    - Compute fractional `earned_i`, `target = round(raw_score)` clamped to [0,100], distribute remainder by frac desc, then weight desc, then normalized name asc
    - Emit breakdown ordered by the same total order; ensure integer points sum exactly to the score
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.10, 10.11, 10.12, 10.13_

  - [x]* 5.2 Write property test for score bounds
    - **Property 6: Score is an integer within bounds**
    - **Validates: Requirements 10.1**

  - [x]* 5.3 Write property test for score conservation
    - **Property 7: Breakdown conserves the score**
    - **Validates: Requirements 10.3, 10.4, 10.13**

  - [x]* 5.4 Write property test for scoring determinism
    - **Property 8: Scoring is deterministic**
    - **Validates: Requirements 10.2**

  - [x]* 5.5 Write property test for extreme categorizations mapping to bounds
    - **Property 9: Extreme categorizations map to score bounds**
    - **Validates: Requirements 10.5, 10.6, 10.12, 7.6**

  - [x]* 5.6 Write property test for score monotonicity
    - **Property 10: Score is monotonic in categorization**
    - **Validates: Requirements 10.7, 10.8, 10.9**

  - [x]* 5.7 Write property test for breakdown completeness and traceability
    - **Property 11: Breakdown is complete and traceable**
    - **Validates: Requirements 10.10**

  - [x]* 5.8 Write unit tests for exact largest-remainder tie-break and weighted proportionality
    - Assert the exact remainder-distribution outcome on a hand-computed example and a weighted-proportionality example
    - _Requirements: 10.4, 10.11_

- [ ] 6. Implement the Roadmap_Generator
  - [x] 6.1 Implement `RoadmapItem` and `generate` in `app/kernel/roadmap.py`
    - One item per missing and weak skill; exclude matched skills
    - Sort by weight desc, then missing before weak, then normalized name asc; assign `priority_rank` 1..N
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x]* 6.2 Write property test for roadmap membership and deterministic ordering
    - **Property 12: Roadmap membership and deterministic ordering**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6**

- [x] 7. Checkpoint - pure kernel complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement SQLite schema and parameterized repository
  - [x] 8.1 Author the database schema DDL in `app/db/schema.sql`
    - Define `student_profile`, `skill`, `certification`, `academic_project`, `resume`, `analysis` tables with CHECK constraints, `ON DELETE CASCADE` foreign keys, and the case-insensitive skill uniqueness constraint
    - _Requirements: 16.1, 16.3, 2.6_

  - [x] 8.2 Implement the parameterized repository in `app/repository/repository.py`
    - Connection factory enabling `PRAGMA foreign_keys = ON`; schema initialization on startup
    - CRUD methods for profiles, skills, certifications, projects, resume (single row per profile), and analyses using bound `?` parameters only (no string-formatted SQL)
    - _Requirements: 16.1, 16.2, 16.3, 23.2_

  - [x]* 8.3 Write integration tests for persistence, cascade delete, and restart durability
    - Verify records persist across a re-opened connection, cascade delete removes owned rows, and stored analyses read back unchanged
    - _Requirements: 16.2, 16.3, 13.1_

  - [x]* 8.4 Write SQL-injection-attempt example test
    - Store a skill name containing `'; DROP TABLE skill; --`, read it back verbatim, and assert the table is intact
    - _Requirements: 23.2, 23.1_

- [ ] 9. Implement Pydantic request/response schemas
  - [x] 9.1 Define request/response models in `app/schemas/`
    - Profile create/update, skill add (type + proficiency default 1), certification, project, resume, analysis request/response, and error response shapes
    - Field validators: non-empty/whitespace-trimmed names and titles, proficiency integer 1..5, job description non-empty and ≤ 20000 chars
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 15.2, 15.3, 18.2, 23.1_

  - [ ]* 9.2 Write unit tests for schema validation edge cases
    - Whitespace-only names/titles, proficiency out of range, JD length boundary at 20000, missing proficiency defaulting to 1
    - _Requirements: 1.2, 2.4, 2.5, 3.2, 4.2, 6.3_

- [-] 10. Implement the service layer
  - [-] 10.1 Implement `ProfileService` in `app/services/profile_service.py`
    - CRUD for profiles, skills, certifications, projects; enforce default proficiency 1 and case-insensitive duplicate rejection; parent-existence checks so 404 precedes 409
    - _Requirements: 1.1, 1.3, 1.5, 2.1, 2.2, 2.5, 2.6, 2.7, 3.1, 3.3, 4.1, 4.4, 15.5_

  - [-] 10.2 Implement `ResumeService` in `app/services/resume_service.py`
    - Accept pasted text or uploaded file; ordered guards — media type (`text/plain`/`application/pdf`) else 415, size ≤ 5 MB else 413, resulting text non-empty else 422; PDF text extraction via `pypdf`, passthrough for plain text; replace existing resume
    - Persist nothing when any guard fails
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [-] 10.3 Implement `AnalysisService` in `app/services/analysis_service.py`
    - Load profile skills + resume, run extractor → comparator → scoring → roadmap, assemble result, persist the `Analysis`, and expose retrieval + list operations
    - Return a valid analysis flagged "no required skills identified" with score 0 when extraction yields nothing
    - _Requirements: 6.1, 7.6, 8.1, 10.12, 11.1, 11.2, 13.1, 13.2, 13.4_

  - [ ]* 10.4 Write unit tests for ResumeService ordered guards
    - Assert 415 precedes 413 precedes 422 emptiness, empty resume rejection, and 5 MB boundary
    - _Requirements: 5.3, 5.4, 5.5_

  - [ ]* 10.5 Write integration test for PDF text extraction
    - Extract text from a small generated PDF and confirm it is stored as resume text
    - _Requirements: 5.2_

- [ ] 11. Checkpoint - persistence and services complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement FastAPI app, error handling, and routers
  - [ ] 12.1 Implement app bootstrap and error handling in `app/main.py`
    - Create FastAPI app, register routers, initialize DB, add global exception handler returning generic 500, and a validation handler returning 422 naming the failing field
    - Define the exception hierarchy resolving 404-over-409 precedence and generic not-found messages
    - _Requirements: 15.1, 15.3, 15.5, 18.1, 18.2, 23.3_

  - [ ] 12.2 Implement health router in `app/routers/health.py`
    - `GET /health` returning success status
    - _Requirements: 15.6_

  - [ ] 12.3 Implement profile/skills/certs/projects routers in `app/routers/profile.py`
    - Endpoints for profile create/get/update/delete, skill add/remove, certification add/remove, project add/remove with correct 200/201/404/409/422 status codes
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 3.1, 3.2, 3.3, 4.1, 4.2, 4.4, 15.4, 16.3_

  - [ ] 12.4 Implement resume router in `app/routers/resume.py`
    - `PUT /profiles/{id}/resume` for paste or upload with 200/404/415/413/422 status codes
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 15.4_

  - [ ] 12.5 Implement analysis router in `app/routers/analysis.py`
    - `POST /profiles/{id}/analyses`, `GET /analyses/{id}`, `GET /profiles/{id}/analyses` with 201/200/404/422 status codes
    - _Requirements: 6.1, 6.2, 6.3, 11.1, 11.2, 13.2, 13.3, 13.4, 15.4_

  - [ ]* 12.6 Write integration tests for status codes and precedence
    - Assert 404-over-409 (duplicate skill under nonexistent profile → 404), 422 field naming, generic 500 body, and not-found non-disclosure
    - _Requirements: 15.4, 15.5, 18.1, 18.2, 23.3_

  - [ ]* 12.7 Write end-to-end integration test for the analysis flow
    - create profile → add skills → submit resume → run analysis → retrieve persisted analysis
    - _Requirements: 13.1, 13.2, 13.4_

  - [ ]* 12.8 Write smoke test for health endpoint
    - Assert `GET /health` returns success
    - _Requirements: 15.6_

- [ ] 13. Checkpoint - backend API complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Scaffold frontend project and shared types
  - [ ] 14.1 Initialize React + TypeScript + Vite project under `frontend/`
    - Configure Vite, TypeScript, and package.json scripts; set up a component test runner (Vitest + Testing Library)
    - _Requirements: 14.1_

  - [ ] 14.2 Define shared TypeScript types mirroring the API contract in `frontend/src/types/`
    - Types for profile, skill, certification, project, resume, analysis (score, breakdown, matched/weak/missing, roadmap), and error responses
    - _Requirements: 15.3_

  - [ ] 14.3 Implement the typed API client in `frontend/src/api/apiClient.ts`
    - Typed fetch wrapper as the only path to the backend; surface API errors as human-readable messages
    - _Requirements: 14.4, 14.5_

- [ ] 15. Implement frontend views and components
  - [ ] 15.1 Implement app shell and navigation in `frontend/src/App.tsx`
    - Navigation between profile view and analysis view; per-active-profile state
    - _Requirements: 14.1_

  - [ ] 15.2 Implement ProfileView and panels in `frontend/src/views/ProfileView.tsx` and `frontend/src/components/`
    - Display active profile name + id; SkillsPanel (technical and soft as separate labeled groups), CertsPanel (re-fetch on active-profile change), ProjectsPanel (titles + descriptions), ResumePanel (paste/upload)
    - Labeled inputs via `htmlFor`/`id`; validation messages rendered adjacent to inputs via `aria-describedby`
    - _Requirements: 1.6, 2.8, 3.4, 3.5, 4.5, 5.1, 22.1, 22.3_

  - [ ] 15.3 Implement AnalysisView and ResultsView in `frontend/src/views/`
    - Labeled job-description text area, in-progress indicator; ResultsView shows score + numeric value, breakdown table, matched/weak/missing groups, and ordered roadmap
    - _Requirements: 6.4, 11.3, 12.7, 14.2, 14.3, 22.1, 22.2_

  - [ ]* 15.4 Write component tests for the frontend
    - Assert labeled inputs (22.1), score-plus-breakdown presentation (22.2), adjacent validation messages (22.3), separate skill groups (2.8), gap groups (11.3), ordered roadmap (12.7), in-progress indicator (14.3), and human-readable error surfacing (14.4)
    - _Requirements: 2.8, 11.3, 12.7, 14.2, 14.3, 14.4, 22.1, 22.2, 22.3_

- [ ] 16. Checkpoint - frontend complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 17. Package with Docker and wire Kiro artifacts
  - [ ] 17.1 Author backend and frontend Dockerfiles
    - `backend/Dockerfile` (uvicorn FastAPI) and `frontend/Dockerfile` (build React SPA, serve statically via nginx)
    - _Requirements: 19.1, 19.2_

  - [ ] 17.2 Author `docker-compose.yml` with a persistent SQLite volume
    - Define `backend` and `frontend` services, published ports, `DATABASE_PATH` on a named volume mounted into the backend so data survives restarts
    - _Requirements: 19.1, 19.2, 19.3, 16.2_

  - [ ] 17.3 Add Kiro workflow artifacts under `.kiro/`
    - Steering docs (determinism + scoring-invariants + style), at least one hook (run property suite on kernel edits), Powers/MCP config, and a custom agent config
    - _Requirements: 21.1, 21.2, 21.3, 21.4_

  - [ ]* 17.4 Write smoke tests for deployment and Kiro-artifact presence
    - Assert compose-built Dashboard + API respond and the mounted volume survives restart; presence checks for steering, hooks, Powers/MCP config, and custom agent
    - _Requirements: 19.1, 19.2, 19.3, 21.1, 21.2, 21.3, 21.4_

- [ ] 18. Final checkpoint - ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP; core implementation tasks are never optional.
- Each task references specific requirement/acceptance-criteria numbers for traceability.
- The pure kernel (`normalize`, `extractor`, `comparator`, `scoring`, `roadmap`) is implemented and property-tested before any I/O adapters so determinism/conservation regressions surface early.
- Each property-based test runs a minimum of 100 iterations and is tagged with its property number.

### Property → Requirement 20 coverage mapping

The property-based tests (Properties 1–12) satisfy Requirement 20 as follows:

| Property | Test task | Validates (Req 10/9/12/etc.) | Requirement 20 clause |
|----------|-----------|------------------------------|-----------------------|
| Property 1 | 2.2 | 7.4, 2.6 | 20.1 (kernel coverage) |
| Property 2 | 3.4 | 7.2, 7.3 | 20.1 (kernel coverage) |
| Property 3 | 3.5 | 7.5 | 20.1 (kernel coverage) |
| Property 4 | 4.2 | 8.1–8.6 | 20.1 (kernel coverage) |
| Property 5 | 4.3 | 9.1, 9.2, 9.3 | 20.6 (comparator order-invariance) |
| Property 6 | 5.2 | 10.1 | 20.4 (bounds) |
| Property 7 | 5.3 | 10.3, 10.4, 10.13 | 20.3 (conservation) |
| Property 8 | 5.4 | 10.2 | 20.2 (scoring determinism) |
| Property 9 | 5.5 | 10.5, 10.6, 10.12, 7.6 | 20.1 (kernel coverage) |
| Property 10 | 5.6 | 10.7, 10.8, 10.9 | 20.5 (monotonicity) |
| Property 11 | 5.7 | 10.10 | 20.1 (kernel coverage) |
| Property 12 | 6.2 | 12.1–12.6 | 20.7 (roadmap deterministic ordering) |

- Requirement 20.1 (pytest coverage of all four kernel components) is met by the property suite (tasks 2.2, 3.4, 3.5, 4.2, 4.3, 5.2–5.7, 6.2) plus the unit tests in task 5.8.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "8.1", "14.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "8.2", "9.1", "14.2"] },
    { "id": 3, "tasks": ["3.2", "3.3", "8.3", "8.4", "9.2", "14.3"] },
    { "id": 4, "tasks": ["3.4", "3.5", "4.1", "10.1", "10.2", "15.1"] },
    { "id": 5, "tasks": ["4.2", "4.3", "5.1", "10.3", "10.4", "10.5", "15.2", "15.3"] },
    { "id": 6, "tasks": ["5.2", "5.3", "5.4", "5.5", "5.6", "5.7", "5.8", "6.1", "12.1", "15.4"] },
    { "id": 7, "tasks": ["6.2", "12.2", "12.3", "12.4", "12.5"] },
    { "id": 8, "tasks": ["12.6", "12.7", "12.8", "17.1", "17.3"] },
    { "id": 9, "tasks": ["17.2"] },
    { "id": 10, "tasks": ["17.4"] }
  ]
}
```
