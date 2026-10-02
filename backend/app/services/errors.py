"""Framework-agnostic service-layer exception hierarchy.

The service layer raises these exceptions to signal business-rule outcomes
without knowing anything about HTTP. The router layer (Task 12) translates each
to a status code and JSON error body:

* :class:`NotFoundError`        -> 404 (Requirements 15.4, 23.3)
* :class:`ConflictError`        -> 409 (Requirement 2.6)
* :class:`ValidationError`      -> 422 (Requirements 15.2, 18.2)
* :class:`UnsupportedMediaError`-> 415 (Requirement 5.4)
* :class:`PayloadTooLargeError` -> 413 (Requirement 5.5)

Keeping this hierarchy free of FastAPI/sqlite3 imports preserves the layered
dependency direction (routers -> services -> kernel + repository): services
depend only on the kernel and the repository, never on the transport layer.

The CRITICAL precedence rule (Requirement 15.5) is enforced by the *services*,
not by these classes: a service always verifies parent-resource existence
(raising :class:`NotFoundError`) BEFORE evaluating a conflict, so e.g. adding a
duplicate skill under a nonexistent profile yields 404, never 409.
"""

from __future__ import annotations

__all__ = [
    "ServiceError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "UnsupportedMediaError",
    "PayloadTooLargeError",
]


class ServiceError(Exception):
    """Base class for all service-layer errors.

    Routers can catch this single type as a fallback; specific subclasses map
    to specific HTTP status codes.
    """


class NotFoundError(ServiceError):
    """A requested resource does not exist -> HTTP 404.

    The message is deliberately generic and discloses no storage internals
    (table names, SQL, ids of unrelated rows) so error responses leak nothing
    about the persistence layer (Requirement 23.3).
    """

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)
        self.message = message


class ConflictError(ServiceError):
    """A uniqueness/business constraint is violated -> HTTP 409.

    Raised, for example, when adding a skill whose normalized name already
    exists for the profile under the same skill type (case-insensitive
    duplicate, Requirement 2.6).
    """

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message)
        self.message = message


class ValidationError(ServiceError):
    """A business rule not expressible in the Pydantic schema failed -> HTTP 422.

    Most input validation happens in the request schemas; this is for rules the
    service enforces directly, such as rejecting a resume whose extracted text
    is empty after stripping (Requirement 5.3). It carries the offending
    ``field`` and a human-readable ``message`` so the router can name the field
    in the 422 body (Requirements 15.2, 18.2).
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class UnsupportedMediaError(ServiceError):
    """An upload's media type is not accepted -> HTTP 415.

    Only ``text/plain`` and ``application/pdf`` resumes are supported
    (Requirement 5.4).
    """

    def __init__(self, message: str = "Unsupported media type") -> None:
        super().__init__(message)
        self.message = message


class PayloadTooLargeError(ServiceError):
    """An upload exceeds the maximum accepted size -> HTTP 413.

    Resume uploads are capped at 5 MB (Requirement 5.5).
    """

    def __init__(self, message: str = "Payload too large") -> None:
        super().__init__(message)
        self.message = message
