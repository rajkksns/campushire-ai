# Product: CampusHire AI

## What it is

CampusHire AI is an AI-powered placement-readiness and skill-gap analyzer for
college students. A student builds a profile (skills, certifications, academic
projects, resume) and supplies a target job description. The system:

1. Extracts the skills the target job requires.
2. Compares them against the student's declared and resume-derived skills.
3. Computes a transparent, deterministic placement-readiness score from 0 to 100.
4. Identifies missing and weak skills.
5. Produces a prioritized learning roadmap.

Results are presented through a clean web dashboard.

## Core value

- **Transparency.** Every point of the readiness score is traceable to a
  contributing factor via an itemized score breakdown. The number is never a
  black box.
- **Determinism.** Identical inputs always produce identical scores, gap
  categorizations, and roadmaps. This is what makes the scoring logic
  trustworthy and what makes property-based testing meaningful.
- **Actionability.** The output is not just a score — it is a categorized gap
  report plus an ordered plan of what to learn first.

## Users

- **Student (primary).** An undergraduate preparing for campus placements. Wants
  to know readiness for a specific role and what to learn next. Technical
  familiarity varies, so output must be clear and non-jargon.
- **Placement Coordinator (secondary).** College staff who review student
  readiness. In this iteration they interact only as viewers of a student's
  generated results; they need scores that are explainable and trustworthy.
- **Evaluator / Judge (Kiro University 2026).** Assesses that the application is
  real, runnable, and demonstrates spec-driven development, steering, hooks,
  property-based testing, Powers, MCP, and custom agents. Needs reproducible
  behavior and verifiable determinism.

## Scope

**In scope:** profile management; skill/certification/project management; resume
ingestion (paste or PDF/plain-text upload); job-description skill extraction;
skill comparison and gap categorization; deterministic scoring; roadmap
generation; analysis persistence and retrieval; dashboard presentation over a
REST API.

**Out of scope (this iteration):** authentication providers, payment,
multi-tenant administration, and live job-board integrations.

## Domain vocabulary

Use these terms consistently in code, tests, and docs:

- **Readiness_Score** — integer 0–100 representing placement readiness.
- **Score_Breakdown** — itemized per-skill point contributions that sum exactly
  to the score.
- **Matched / Weak / Missing skill** — a required skill the student has at
  proficiency ≥ 3, has at proficiency < 3, or lacks entirely.
- **Learning_Roadmap** — ordered list of learning items for weak and missing
  skills, by priority.
- **Analysis** — a persisted result set for one profile and one job description.
