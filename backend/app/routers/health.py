"""Health-check router (Task 12.2, Requirement 15.6).

A trivial liveness endpoint used by Docker Compose health checks and smoke
tests. It touches no services and no database, so it stays fast and cannot fail
for business reasons.
"""

from __future__ import annotations

from fastapi import APIRouter

__all__ = ["router"]

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a success status (Requirement 15.6)."""
    return {"status": "ok"}
