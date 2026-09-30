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

## MCP server

A small custom Model Context Protocol server lives in `mcp_server/`. It exposes
read-only, deterministic tools over the analysis kernel:

- `list_known_skills` — curated skill vocabulary (with version + count)
- `normalize_skill` — wraps `skill_normalize`
- `resolve_skill_alias` — maps a term/alias to its canonical skill name
- `preview_required_skills` — runs `extract_required_skills` on job-description text

Run it from this `backend/` directory (so both the `app` package and the `mcp`
SDK resolve). It speaks MCP over stdio:

```bash
python -m mcp_server.server
```

Kiro launches it automatically via `.kiro/settings/mcp.json`. The package is
named `mcp_server` (not `mcp`) so it does not shadow the installed `mcp` SDK.
