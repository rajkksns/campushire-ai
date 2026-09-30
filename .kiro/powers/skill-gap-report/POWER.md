---
name: skill-gap-report
displayName: Skill Gap Report
description: Produce a transparent, deterministic placement-readiness summary for a CampusHire AI student profile against a target job description, using the existing analysis kernel (extractor -> comparator -> scoring -> roadmap).
keywords:
  - skill-gap
  - skill gap report
  - placement readiness
  - readiness score
  - campushire
  - roadmap
version: 1.0.0
---

# Skill Gap Report Power

## What this Power does

Given a **student profile** (declared skills with proficiencies, plus optional
resume text) and a **target job description**, this Power produces a placement-
readiness summary:

- a **readiness score** (integer 0–100),
- a **score breakdown** where every point traces to a skill (conservation),
- **matched / weak / missing** skill groups, and
- a **prioritized learning roadmap**.

It is a thin, reusable wrapper over the project's pure analysis kernel
(`app.kernel`): `extract_required_skills` + `extract_resume_skills` ->
`compare` -> `score` -> `generate`. Because the kernel is deterministic, the
report is fully reproducible: identical inputs always yield an identical report.

## When to use

- You want a one-shot readiness summary without going through the REST API or UI.
- You are demoing or sanity-checking the analysis pipeline for a given profile
  and job description.
- You want to compare readiness across several target roles for the same profile.

Do **not** use it to mutate data — it is read-only and persists nothing.

## Tools

This Power provides one MCP tool via the `skill-gap-report` server:

### `generate_skill_gap_report`

Runs the full analysis pipeline and returns the readiness summary.

Arguments:
- `job_description` (string, required): target job-description text.
- `skills` (array, optional): the student's declared skills, each
  `{ "name": string, "proficiency": integer 1..5 }`. Proficiency defaults to 1
  if omitted.
- `resume_text` (string, optional): resume text; skills found here are unioned
  with declared skills (max proficiency wins).

Returns an object with:
- `readiness_score` (int 0..100),
- `breakdown` (list of `{ name, weight, category, points }`),
- `matched` / `weak` / `missing` (lists of skill entries),
- `roadmap` (ordered list of `{ name, weight, category, priority_rank }`),
- `no_required_skills_identified` (bool) — true when the JD yields no known
  skills (score is 0 in that case).

## How it is packaged

- `POWER.md` — this manifest/documentation.
- `power.json` — machine-readable metadata + MCP server registration.
- `server/report_power.py` — the FastMCP server implementing the tool. It reuses
  `backend/app/kernel` and adds no new business logic, so the determinism and
  transparency guarantees are inherited unchanged.
- `steering/skill-gap-report-guide.md` — a short workflow guide.

## Running the Power's server

The server reuses the backend kernel, so run it from the `backend/` directory
(so the `app` package and the `mcp` SDK resolve):

```bash
python ../.kiro/powers/skill-gap-report/server/report_power.py
```

Kiro launches it automatically via the MCP registration in `power.json` /
`.kiro/settings/mcp.json`.
