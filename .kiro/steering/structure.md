# Project Structure

## Repository layout

```
campushire-ai/
├── .kiro/
│   ├── specs/campushire-ai/     # requirements.md, design.md, tasks.md
│   ├── steering/                # product.md, tech.md, structure.md
│   └── hooks/                   # agent hooks
├── backend/                     # Python + FastAPI service
│   ├── app/
│   │   ├── main.py              # FastAPI app bootstrap, error handlers, router wiring
│   │   ├── kernel/              # PURE, deterministic analysis kernel (no I/O)
│   │   ├── routers/             # FastAPI HTTP routers (thin transport adapters)
│   │   ├── services/            # orchestration between routers, kernel, repository
│   │   ├── repository/          # parameterized SQLite data access
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── db/                  # schema.sql and DB helpers
│   ├── tests/
│   │   ├── properties/          # Hypothesis property-based tests (kernel)
│   │   ├── unit/                # example/edge unit tests
│   │   └── integration/         # persistence + end-to-end API tests
│   └── pyproject.toml           # dependencies, pytest & hypothesis config
├── frontend/                    # React + TypeScript + Vite SPA
│   └── src/
│       ├── App.tsx              # app shell + navigation
│       ├── views/               # ProfileView, AnalysisView, ResultsView
│       ├── components/          # SkillsPanel, CertsPanel, ProjectsPanel, ResumePanel, ...
│       ├── api/                 # typed API client (apiClient.ts)
│       └── types/               # shared TS types mirroring the API contract
├── docker-compose.yml           # backend + frontend + persistent SQLite volume
└── README.md
```

## Backend layers & dependency direction

Strict one-way dependencies: **routers → services → (kernel + repository)**.
The kernel depends only on the standard library and its own `normalize` helper.

- **`app/kernel/`** — the correctness-critical core. Pure functions only; no
  FastAPI, no `sqlite3`, no file/network I/O. See `tech.md` for the pure-kernel
  rules.
  - `normalize.py` — `skill_normalize`, the single canonicalization rule used
    everywhere for skill matching.
  - `extractor.py` — curated skill vocabulary + alias table, `RequiredSkill`,
    `extract_required_skills`, `extract_resume_skills`.
  - `comparator.py` — `Category`, `StudentSkill`, `ComparedSkill`,
    `PROFICIENCY_THRESHOLD`, `compare`.
  - `scoring.py` — `BreakdownItem`, `ScoreResult`, `CATEGORY_FACTOR`, `score`
    (largest-remainder / Hamilton allocation).
  - `roadmap.py` — `RoadmapItem`, `generate`.
- **`app/repository/`** — all SQLite access, using bound `?` parameters only.
  Connection factory enables `PRAGMA foreign_keys = ON`; schema initialized on
  startup.
- **`app/schemas/`** — Pydantic v2 models that validate input at the boundary
  and define response shapes.
- **`app/services/`** — orchestration:
  - `ProfileService` — profiles, skills, certifications, projects CRUD.
  - `ResumeService` — resume paste/upload, media/size guards, text extraction.
  - `AnalysisService` — runs the kernel pipeline, persists and retrieves
    analyses.
- **`app/routers/`** — FastAPI endpoints (health, profile/skills/certs/projects,
  resume, analysis). Map service results and exceptions to HTTP status codes.
- **`app/main.py`** — creates the app, registers routers, initializes the DB,
  and installs global validation (422) and generic-error (500) handlers.

## Analysis pipeline

`AnalysisService` drives the kernel in a fixed order:

```
extract_required_skills(jd) ─┐
extract_resume_skills(resume)┴─> compare(student, required)
        ─> score(compared)  ─> generate(compared)  ─> persist Analysis
```

Because the pipeline is deterministic, the fully materialized `Analysis`
(score, breakdown, categorization, roadmap) is stored as JSON and read back
without recomputation.

## Frontend structure

- **`App.tsx`** — navigation between the profile and analysis views; state kept
  per active profile.
- **`views/`** — `ProfileView` (profile identity + panels), `AnalysisView`
  (job-description input + progress), `ResultsView` (score, breakdown table,
  matched/weak/missing groups, ordered roadmap).
- **`components/`** — panels for skills (technical and soft as separate labeled
  groups), certifications (re-fetch on active-profile change), projects, resume.
- **`api/apiClient.ts`** — the single typed gateway to the backend.
- **`types/`** — TypeScript types mirroring the REST contract.

## File-placement conventions

- New pure analysis logic → `app/kernel/` (and add a property test in
  `tests/properties/`).
- New endpoint → add the route in `app/routers/`, the orchestration in
  `app/services/`, and request/response models in `app/schemas/`.
- New persisted entity → add DDL in `app/db/schema.sql` and access methods in
  `app/repository/`.
- Tests mirror the layer they cover: property tests for the kernel, integration
  tests for persistence and API flows, unit tests for isolated logic.
- Kiro artifacts live under `.kiro/` (specs, steering, hooks).
