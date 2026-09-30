# Skill Gap Report — Workflow Guide

This guide explains how to use the `skill-gap-report` Power to produce a
placement-readiness summary.

## Quick start

Call the `generate_skill_gap_report` tool with a job description and, optionally,
the student's declared skills and/or resume text.

Minimal (job description only):

```json
{ "job_description": "We need a backend engineer with Python, Docker, and PostgreSQL." }
```

With declared skills and resume:

```json
{
  "job_description": "Backend engineer: strong Python and Docker required. Kubernetes a plus.",
  "skills": [
    { "name": "Python", "proficiency": 4 },
    { "name": "Docker", "proficiency": 2 }
  ],
  "resume_text": "Built REST APIs in Python; some exposure to PostgreSQL."
}
```

## Reading the result

- `readiness_score` — integer 0–100. Every point is explained by `breakdown`.
- `breakdown` — per required skill: `name`, `weight` (1–5), `category`
  (matched/weak/missing), and integer `points`. Points sum exactly to the score.
- `matched` / `weak` / `missing` — the gap groups. Matched means the student has
  the skill at proficiency ≥ 3; weak means < 3; missing means no match.
- `roadmap` — ordered learning plan (weight desc, then missing before weak, then
  name asc) with `priority_rank` 1..N. Matched skills are excluded.
- `no_required_skills_identified` — `true` when the job description contains no
  skills from the curated vocabulary; the score is 0 in that case.

## Tips

- Proficiency defaults to 1 when omitted or out of range; values are clamped to
  1–5.
- Resume-derived skills are unioned with declared skills; if the same skill is
  both declared (high) and resume-derived (default 1), the higher proficiency
  wins.
- The report is deterministic: identical inputs always produce an identical
  report, so it is safe to cache or compare across runs.
- To compare a student against several roles, call the tool once per job
  description and compare the `readiness_score` and `roadmap` outputs.

## Boundaries

- The Power is **read-only**: it computes and returns a report but persists
  nothing and calls no database or network.
- It contains **no business logic of its own** — it reuses `app.kernel`. To
  change scoring/comparison/roadmap behavior, change the kernel (and its property
  tests), not this Power.
