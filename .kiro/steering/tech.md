# Technology & Conventions

## Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Frontend | React 18 + TypeScript + Vite | Type-safe SPA; Vite for dev/build. |
| Backend | Python 3.11 + FastAPI + Pydantic v2 | Async REST; schema validation at the boundary. |
| Persistence | SQLite (`sqlite3` stdlib, parameterized) | Embedded DB; file on a mounted volume for durability. |
| PDF parsing | `pypdf` (pure-Python) | Deterministic, dependency-light resume text extraction. |
| Testing | `pytest` + `hypothesis` | Example/edge/integration tests plus property-based tests for the kernel. |
| Frontend testing | Vitest + Testing Library | Component tests. |
| Packaging | Docker + Docker Compose | Reproducible frontend + backend + mounted volume. |

## Build & test commands

Run backend commands from the `backend/` directory.

- Install (with dev tools): `pip install -e ".[dev]"`
- Run the full backend test suite: `python -m pytest`
- Run only property tests: `python -m pytest tests/properties`
- Run the API (dev): `uvicorn app.main:app --reload` (run manually in a terminal;
  do not launch long-running servers from automated steps)
- Frontend dev/build/test: `npm run dev` / `npm run build` / `npm run test`
  (run from `frontend/`)
- Full stack: `docker compose up`

Property-based tests run a minimum of 100 examples (configured under
`[tool.hypothesis]` in `backend/pyproject.toml`).

## The pure-kernel principle (most important rule)

The analysis kernel — `skill_normalize`, `Skill_Extractor`, `Skill_Comparator`,
`Scoring_Engine`, `Roadmap_Generator` — is a set of **pure, deterministic,
side-effect-free functions**. This is the correctness-critical core and the
surface that property-based testing validates.

Rules for anything under `app/kernel/`:

- **No I/O of any kind.** The kernel must never import FastAPI, `sqlite3`, file
  I/O, or networking. It depends only on the standard library and the sibling
  `normalize` helper.
- **No nondeterminism.** No randomness, no wall-clock, no environment reads, no
  network. Identical inputs must always produce identical outputs.
- **No reliance on iteration order.** Never depend on Python dict/set iteration
  order or database row order. Any function that emits a collection must sort by
  an explicit, total ordering key.
- **Immutable data.** Kernel inputs and outputs are `@dataclass(frozen=True)` so
  results cannot be mutated after computation.
- **Adapters stay thin.** FastAPI routers, the SQLite repository, and the resume
  parser are I/O adapters that marshal data into and out of the pure kernel.
  Business logic that can be pure belongs in the kernel.

## Determinism & scoring invariants

These invariants are enforced by property tests; preserve them in any change.

- **Single normalization rule.** All skill-name matching goes through
  `skill_normalize` (trim, collapse internal whitespace to one space, lowercase).
  It is idempotent and case/whitespace invariant. Declared skills, resume-derived
  skills, and required skills all compare under this one rule.
- **Deterministic ordering everywhere.** Extraction, comparison, and roadmap
  outputs are sorted by explicit total-order keys (see design). Ties are broken
  deterministically (e.g. alphabetical by normalized name).
- **Integer point conservation.** The readiness score is an integer in [0, 100]
  whose per-skill point contributions sum **exactly** to the score. Fractional
  weighted allocations are reconciled with the largest-remainder (Hamilton)
  method, distributing the remainder by fractional part desc, then weight desc,
  then normalized name asc. Use round-half-up (not banker's rounding) for the
  target.
- **Category factors.** matched = 1.0, weak = 0.5, missing = 0.0. This ordering
  underlies the monotonicity guarantees; keep it monotonic (matched ≥ weak ≥
  missing).
- **Degenerate cases.** Empty required set → score 0 with empty breakdown;
  all-matched → 100; all-missing → 0; total weight 0 → treat every skill as
  equally weighted (w = 1) using the same rounding rule.
- **Proficiency threshold.** A matched student skill with proficiency ≥ 3 is
  MATCHED; < 3 is WEAK; no match is MISSING. Default proficiency is 1.

When changing scoring, comparison, extraction, or roadmap logic, run the property
suite (`python -m pytest tests/properties`) and confirm all properties still hold.

## Coding conventions

### Python (backend)

- Target Python 3.11; use `from __future__ import annotations` and modern typing
  (`list[X]`, `X | None`).
- Full type hints on public functions; dataclasses for structured data.
- Module and function docstrings explain intent and cite the requirement or
  design section they satisfy where relevant.
- Validate and sanitize all request input at the boundary with Pydantic before
  persistence.
- **All SQLite access uses bound `?` parameters** — never string-formatted SQL.
- Follow the layered dependency direction: routers → services → (kernel +
  repository); the kernel depends on nothing but stdlib + `normalize`.

### API & error handling

- Responses are JSON. Status codes: 200/201 success, 400/422 client validation,
  404 missing, 409 conflict, 413 payload too large, 415 unsupported media, 500
  internal.
- **404 takes precedence over 409**: check parent-resource existence before
  evaluating conflicts.
- 422 validation errors name the failing field; 500 returns a generic message
  with no stack trace or field detail. Not-found messages disclose no storage
  internals.

### TypeScript (frontend)

- Strict TypeScript. Shared types mirror the API contract.
- The typed API client is the **only** path to the backend; surface API errors
  as human-readable messages.
- All form inputs have visible associated labels; validation messages render
  adjacent to their input.

## Testing conventions

- Property-based tests live in `backend/tests/properties/`, one property per
  test, tagged with its property number in the docstring, min 100 iterations.
- Example, edge, and integration tests cover CRUD, transport, persistence, and
  the resume/analysis flows (things with side effects or no universal quantifier).
- Prefer running tests non-interactively (e.g. `--run` for watch-mode runners).
- Do not create throwaway sanity/verify scripts in the repo; use inline checks or
  proper tests.
