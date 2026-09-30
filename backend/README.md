# CampusHire AI — Backend

Python 3.11 + FastAPI + Pydantic v2 service with a pure, deterministic skill-gap
analysis kernel and parameterized SQLite persistence.

## Layout

- `app/` — application package
  - `routers/` — FastAPI routers (API layer)
  - `services/` — orchestration between routers, kernel, and repository
  - `kernel/` — pure, deterministic analysis kernel (no I/O)
  - `repository/` — parameterized SQLite persistence
  - `schemas/` — Pydantic request/response models
  - `db/` — schema DDL and initialization assets
- `tests/` — `properties/` (Hypothesis), `unit/`, `integration/`

## Setup

```bash
pip install -e ".[dev]"
```

## Testing

```bash
pytest
```
