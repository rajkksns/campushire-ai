"""Resume router (Task 12.4, Requirement 5).

A single endpoint, ``PUT /profiles/{id}/resume``, accepts a resume by **paste**
(JSON body ``{"content": "..."}``) or **upload** (multipart file). The router
inspects the request's content type to pick the mode, then delegates to
:class:`ResumeService`, which owns the ordered guards (media type -> size ->
non-empty) and PDF/plain-text extraction. Submitting a resume replaces any
prior one (5.6).

Status codes (design REST API Contract):

* **200** on success (replace-or-create of the single resume).
* **404** if the profile does not exist (service :class:`NotFoundError`).
* **415** unsupported media type, **413** payload too large, **422** empty
  content — all raised by the service and mapped globally in :mod:`app.main`,
  which keeps the guard-ordering single-sourced.

A malformed/absent body (neither valid paste JSON nor a multipart file) is a
client validation error (422) named at the ``body`` field.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError as PydanticValidationError
from starlette.datastructures import UploadFile

from app.dependencies import get_resume_service
from app.schemas.resume import ResumePaste, ResumeResponse
from app.services.errors import ValidationError
from app.services.resume_service import ResumeService

__all__ = ["router"]

router = APIRouter(tags=["resume"])

# Default media type assumed for an uploaded file that declares none. The
# service applies the real media-type guard; we only supply a fallback so a
# browser upload without an explicit content type is still classified.
_DEFAULT_UPLOAD_MEDIA = "application/octet-stream"


@router.put("/profiles/{profile_id}/resume", response_model=ResumeResponse)
async def put_resume(
    profile_id: str,
    request: Request,
    service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """Store a resume by paste or upload (Requirements 5.1-5.6) -> 200/404/415/413/422.

    Mode selection is by content type:

    * ``multipart/form-data`` -> treat as a file **upload**; read the first
      uploaded file's bytes and declared media type and hand them to
      :meth:`ResumeService.save_uploaded_resume` (media/size/extraction guards
      run there, 5.2, 5.4, 5.5).
    * anything else -> treat as a JSON **paste**; validate the body against
      :class:`ResumePaste` and call :meth:`ResumeService.save_pasted_resume`
      (size/non-empty guards run there, 5.3, 5.5).

    The profile-existence check and resume replacement happen inside the
    service, so nothing is persisted when a guard fails (5.6).
    """
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        record = await _handle_upload(profile_id, request, service)
    else:
        record = await _handle_paste(profile_id, request, service)

    return ResumeResponse(
        profile_id=record.profile_id, updated_at=record.updated_at
    )


async def _handle_upload(
    profile_id: str, request: Request, service: ResumeService
):
    """Extract the uploaded file and delegate to the service (upload mode)."""
    form = await request.form()
    upload = _first_upload_file(form)
    if upload is None:
        # Multipart with no file part is a client error named at the body.
        raise ValidationError(
            field="file", message="A resume file is required for upload"
        )

    data = await upload.read()
    media_type = upload.content_type or _DEFAULT_UPLOAD_MEDIA
    return service.save_uploaded_resume(
        profile_id=profile_id,
        filename=upload.filename or "resume",
        media_type=media_type,
        data=data,
    )


async def _handle_paste(
    profile_id: str, request: Request, service: ResumeService
):
    """Validate the JSON paste body and delegate to the service (paste mode)."""
    try:
        payload = await request.json()
    except Exception as exc:  # malformed/empty JSON body
        raise ValidationError(
            field="body", message="Expected a JSON body with a 'content' field"
        ) from exc

    try:
        parsed = ResumePaste.model_validate(payload)
    except PydanticValidationError as exc:
        # Re-raise as a service ValidationError so the global 422 handler names
        # the failing field consistently with the rest of the API.
        first = exc.errors()[0]
        loc = [str(p) for p in first.get("loc", ()) if p != "body"]
        field = loc[-1] if loc else "content"
        message = first.get("msg", "Invalid value").removeprefix("Value error, ")
        raise ValidationError(field=field, message=message) from exc

    return service.save_pasted_resume(profile_id, parsed.content)


def _first_upload_file(form) -> UploadFile | None:
    """Return the first uploaded file in a parsed multipart form, else ``None``.

    ``request.form()`` yields Starlette's :class:`starlette.datastructures.UploadFile`
    (not FastAPI's re-export, which is a distinct subclass under Starlette
    1.3+), so the membership test is against the Starlette class to classify an
    upload reliably.
    """
    for value in form.values():
        if isinstance(value, UploadFile):
            return value
    return None
