"""Error response schemas (design "Sample payloads", Requirements 15.2, 18.1,
18.2, 23.3).

These define the exact JSON error shapes the API returns. The validation error
names the failing field (18.2); the not-found and internal errors carry only
generic messages that disclose no storage internals or stack traces (23.3,
18.1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

__all__ = ["ValidationErrorResponse", "NotFoundErrorResponse", "InternalErrorResponse"]


class ValidationErrorResponse(BaseModel):
    """422 body naming the failing field (Requirements 15.2, 18.2)."""

    error: Literal["validation_error"] = "validation_error"
    field: str
    message: str


class NotFoundErrorResponse(BaseModel):
    """404 body with a generic, non-disclosing message (Requirement 23.3)."""

    error: Literal["not_found"] = "not_found"
    message: str = "Resource not found"


class InternalErrorResponse(BaseModel):
    """500 body: generic message, no stack trace or field detail (18.1)."""

    error: Literal["internal_error"] = "internal_error"
    message: str = "An unexpected error occurred"
