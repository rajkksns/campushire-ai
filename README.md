# CampusHire AI

A placement-readiness and skill-gap analyzer for college students. A student adds skills, certifications, projects and a resume, then pastes a target job description. CampusHire AI returns a transparent **0-100 readiness score**, a **matched / weak / missing** skill breakdown, and a **prioritized learning roadmap**.

Built for **Kiro University 2026** (AWS User Group Madurai).

## Tech stack
- Frontend: React + TypeScript (Vite)
- Backend: Python + FastAPI
- Database: SQLite
- Tests: pytest + Hypothesis (property-based testing)

## Run locally
Backend (terminal 1):
    cd backend
    pip install -e ".[dev]"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Frontend (terminal 2):
    cd frontend
    npm install
    npm run dev

Open http://localhost:5173 for the dashboard, or http://127.0.0.1:8000/docs for the API.

## Run tests
    cd backend
    python -m pytest

## How scoring works
Each required skill gets a weight. Skills at proficiency 3 or above are matched (full points), below 3 are weak (half points), and absent skills are missing (0 points). Points are allocated with a deterministic largest-remainder method, so they always add up exactly to the score and the same input always gives the same result.

## Kiro features used
- **Spec-driven development:** `.kiro/specs/campushire-ai/` (requirements.md, design.md, tasks.md) drove every task.
- **Steering documents:** `.kiro/steering/` (product.md, tech.md, structure.md).
- **Hooks:** `.kiro/hooks/backend-pytest-on-save.kiro.hook` runs the test suite when a backend Python file is saved.
- **Property-based testing:** Hypothesis properties in `backend/tests` check score bounds, point conservation, determinism and roadmap ordering.
- **Powers:** `.kiro/powers/skill-gap-report/` (POWER.md, power.json, MCP server, steering guide).
- **MCP:** custom FastMCP server in `backend/mcp_server`, registered in `.kiro/settings/mcp.json`.
- **Custom agents:** `.kiro/agents/campushire-reviewer.json` reviews profiles and code against the spec.
