"""Skill Gap Report Power — MCP server.

A thin, reusable Model Context Protocol server that produces a placement-
readiness summary for a CampusHire AI student profile against a target job
description. It reuses the project's pure analysis kernel and adds NO new
business logic, so the determinism and transparency guarantees are inherited
unchanged:

    extract_required_skills(jd) + extract_resume_skills(resume)
        -> compare(student, required)
        -> score(compared)      (readiness score + breakdown)
        -> generate(compared)   (prioritized roadmap)

Read-only: it persists nothing and performs no database or network I/O.

Run it from the ``backend/`` directory so both the ``app`` package and the
``mcp`` SDK resolve:

    python ../.kiro/powers/skill-gap-report/server/report_power.py

The pipeline order and assembly mirror the design's AnalysisService so the
report is identical to what the API would return for the same inputs.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Make the backend/ directory importable regardless of the launch cwd, so this
# Power can be run/packaged independently while still reusing the real kernel.
# backend/ is three levels up from this file:
# backend/.kiro/... no — this file lives at <repo>/.kiro/powers/skill-gap-report/server/
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_BACKEND_DIR = os.path.join(_REPO_ROOT, "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from mcp.server.fastmcp import FastMCP

from app.kernel.comparator import Category, StudentSkill, compare
from app.kernel.extractor import extract_required_skills, extract_resume_skills
from app.kernel.roadmap import generate
from app.kernel.scoring import score

mcp = FastMCP("skill-gap-report")


def _coerce_student_skills(
    skills: list[dict[str, Any]] | None,
    resume_text: str | None,
) -> list[StudentSkill]:
    """Build the union of declared and resume-derived student skills.

    Declared skills come from ``skills`` (proficiency defaults to 1 when absent
    or invalid). Resume-derived skills are added at the default proficiency of 1;
    the comparator's name->max-proficiency map ensures a declared skill with a
    higher proficiency still wins. This mirrors the design's union rule.
    """
    student: list[StudentSkill] = []

    for entry in skills or []:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        raw_prof = entry.get("proficiency", 1)
        try:
            proficiency = int(raw_prof)
        except (TypeError, ValueError):
            proficiency = 1
        proficiency = max(1, min(5, proficiency))
        student.append(StudentSkill(name=name, proficiency=proficiency))

    for name in extract_resume_skills(resume_text):
        student.append(StudentSkill(name=name, proficiency=1))

    return student


@mcp.tool()
def generate_skill_gap_report(
    job_description: str,
    skills: list[dict[str, Any]] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    """Produce a placement-readiness report for a profile vs. a job description.

    Args:
        job_description: Target job-description text.
        skills: Optional declared skills, each ``{"name", "proficiency"}`` with
            proficiency on the 1..5 scale (defaults to 1 when omitted).
        resume_text: Optional resume text; recognized skills are unioned with the
            declared skills (max proficiency wins).

    Returns:
        A dict with ``readiness_score``, ``breakdown``, ``matched``/``weak``/
        ``missing`` groups, ``roadmap``, and ``no_required_skills_identified``.
    """
    required = extract_required_skills(job_description)

    # Empty extraction is a valid outcome: score 0, empty everything (design 7.6).
    if not required:
        return {
            "readiness_score": 0,
            "no_required_skills_identified": True,
            "breakdown": [],
            "matched": [],
            "weak": [],
            "missing": [],
            "roadmap": [],
        }

    student = _coerce_student_skills(skills, resume_text)
    compared = compare(student, required)
    result = score(compared)
    roadmap = generate(compared)

    matched = [
        {"name": c.name, "weight": c.weight, "proficiency": c.proficiency}
        for c in compared
        if c.category is Category.MATCHED
    ]
    weak = [
        {"name": c.name, "weight": c.weight, "proficiency": c.proficiency}
        for c in compared
        if c.category is Category.WEAK
    ]
    missing = [
        {"name": c.name, "weight": c.weight}
        for c in compared
        if c.category is Category.MISSING
    ]

    return {
        "readiness_score": result.readiness_score,
        "no_required_skills_identified": False,
        "breakdown": [
            {
                "name": b.name,
                "weight": b.weight,
                "category": b.category.value,
                "points": b.points,
            }
            for b in result.breakdown
        ],
        "matched": matched,
        "weak": weak,
        "missing": missing,
        "roadmap": [
            {
                "name": r.name,
                "weight": r.weight,
                "category": r.category.value,
                "priority_rank": r.priority_rank,
            }
            for r in roadmap
        ],
    }


def main() -> None:
    """Entry point: run the Power's MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
