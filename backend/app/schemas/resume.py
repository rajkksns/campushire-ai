"""Resume request/response schemas (Requirement 5).

This models the JSON *paste* body only; multipart/file upload, media-type, and
size guards are a router/service concern handled later (Requirements 5.2, 5.4,
5.5). The pasted ``content`` must be non-empty after trimming (Requirement
5.3). Note: unlike names/titles, the trimmed value is validated but the
original content is preserved so resume text keeps its internal formatting.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import StrictModel

__all__ = ["ResumePaste", "ResumeResponse"]


class ResumePaste(StrictModel):
    """Request body for pasting resume text (Requirement 5.1, 5.3)."""

    content: str = Field(description="Raw resume text; must be non-empty after trim.")

    @field_validator("content")
    @classmethod
    def _reject_blank_content(cls, value: str) -> str:
        """Reject empty/whitespace-only content (5.3).

        The content is validated against its trimmed form but returned
        unchanged so meaningful internal whitespace/newlines in the resume are
        preserved for downstream skill extraction.
        """
        if not value.strip():
            raise ValueError("resume content must not be empty or whitespace-only")
        return value


class ResumeResponse(BaseModel):
    """Minimal confirmation returned after storing a resume (Requirement 5.1)."""

    profile_id: str
    updated_at: str
