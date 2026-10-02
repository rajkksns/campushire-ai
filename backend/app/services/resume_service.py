"""ResumeService: resume paste/upload ingestion with ordered guards.

This service accepts a resume as either pasted text or an uploaded file,
enforces media/size/content guards in a fixed order, extracts plain text
(decoding plain text directly, parsing PDFs with ``pypdf``), and replaces the
profile's single stored resume (Requirements 5.1-5.6).

Layering: it depends only on the repository and ``pypdf`` (an I/O adapter
isolated to this module so the kernel stays pure). It never imports FastAPI or
sqlite3. The one wall-clock read lives here in the adapter layer.

Guard order (persist NOTHING if any guard fails):
    1. media type must be ``text/plain`` or ``application/pdf`` -> else 415
    2. size must be <= 5 MB -> else 413
    3. extracted text must be non-empty after strip -> else 422
Then verify the profile exists (404 otherwise) and upsert the resume (5.1, 5.6).
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from pypdf import PdfReader

from app.repository.repository import Repository, ResumeRecord
from app.services.errors import (
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaError,
    ValidationError,
)

__all__ = ["ResumeService", "MAX_RESUME_BYTES", "SUPPORTED_MEDIA_TYPES"]

# Resume uploads are capped at 5 MB (Requirement 5.5).
MAX_RESUME_BYTES = 5 * 1024 * 1024

# Only these media types are accepted (Requirement 5.4).
MEDIA_TEXT = "text/plain"
MEDIA_PDF = "application/pdf"
SUPPORTED_MEDIA_TYPES = frozenset({MEDIA_TEXT, MEDIA_PDF})


def _now_iso() -> str:
    """Return the current time as an ISO-8601 UTC string (adapter-layer clock)."""
    return datetime.now(timezone.utc).isoformat()


class ResumeService:
    """Validate, extract, and persist a profile's resume."""

    def __init__(self, repository: Repository) -> None:
        """Store the injected repository.

        Args:
            repository: The persistence adapter (dependency injection).
        """
        self._repo = repository

    # -- public entry points --------------------------------------------- #
    def save_pasted_resume(self, profile_id: str, content: str) -> ResumeRecord:
        """Store pasted resume text (Requirements 5.1, 5.3, 5.6).

        Pasted text is treated as ``text/plain``: no media guard is needed, but
        the content size and non-emptiness guards still apply, in order.

        Args:
            profile_id: Target profile.
            content: The pasted resume text.

        Returns:
            The persisted :class:`ResumeRecord`.

        Raises:
            PayloadTooLargeError: If the UTF-8 encoding exceeds 5 MB (5.5).
            ValidationError: If the text is empty after stripping (5.3).
            NotFoundError: If the profile does not exist.
        """
        # Guard 2 (size): measure the encoded byte length so the limit matches
        # the uploaded-bytes path. (Guard 1/media is implicit for paste.)
        encoded = content.encode("utf-8")
        self._guard_size(len(encoded))

        # Guard 3 (non-empty after strip).
        text = self._require_non_empty(content)

        return self._persist(profile_id, text)

    def save_uploaded_resume(
        self,
        profile_id: str,
        filename: str,
        media_type: str,
        data: bytes,
    ) -> ResumeRecord:
        """Store an uploaded resume file (Requirements 5.1-5.6).

        Enforces the guards in the fixed order media -> size -> content, then
        persists. Nothing is written if any guard fails.

        Args:
            profile_id: Target profile.
            filename: The upload's filename (used only for diagnostics).
            media_type: The declared media type; must be ``text/plain`` or
                ``application/pdf`` (5.4).
            data: The raw file bytes.

        Returns:
            The persisted :class:`ResumeRecord`.

        Raises:
            UnsupportedMediaError: If the media type is not supported (415, 5.4).
            PayloadTooLargeError: If the file exceeds 5 MB (413, 5.5).
            ValidationError: If the extracted text is empty after strip (422, 5.3).
            NotFoundError: If the profile does not exist (404).
        """
        # Guard 1 (media type) — strip any "; charset=..." parameter so a
        # declared "text/plain; charset=utf-8" still matches (5.4).
        normalized_media = media_type.split(";", 1)[0].strip().lower()
        if normalized_media not in SUPPORTED_MEDIA_TYPES:
            raise UnsupportedMediaError(
                "Resume must be plain text or PDF"
            )

        # Guard 2 (size) (5.5).
        self._guard_size(len(data))

        # Guard 3 (extract text, then non-empty after strip) (5.2, 5.3).
        extracted = self._extract_text(normalized_media, data)
        text = self._require_non_empty(extracted)

        return self._persist(profile_id, text)

    # -- guards ----------------------------------------------------------- #
    @staticmethod
    def _guard_size(size_bytes: int) -> None:
        """Raise :class:`PayloadTooLargeError` if ``size_bytes`` exceeds the cap.

        The boundary is inclusive: exactly ``MAX_RESUME_BYTES`` is accepted;
        anything larger is rejected (Requirement 5.5).
        """
        if size_bytes > MAX_RESUME_BYTES:
            raise PayloadTooLargeError("Resume exceeds the 5 MB limit")

    @staticmethod
    def _require_non_empty(text: str) -> str:
        """Return the resume text or raise :class:`ValidationError` if blank.

        Rejects content that is empty or whitespace-only after stripping. The
        original (unstripped) text is returned when non-empty so stored content
        is preserved verbatim (Requirement 5.3).
        """
        if not text.strip():
            raise ValidationError(
                field="content", message="Resume text must not be empty"
            )
        return text

    # -- extraction ------------------------------------------------------- #
    @staticmethod
    def _extract_text(media_type: str, data: bytes) -> str:
        """Extract resume text from raw bytes by media type (Requirement 5.2).

        Plain text is a decode passthrough (UTF-8, replacing undecodable bytes
        so a stray byte never crashes ingestion). PDFs are parsed with
        ``pypdf``'s :class:`PdfReader`, concatenating each page's extracted
        text. ``pypdf`` usage is isolated to this adapter method so the kernel
        stays pure.

        Args:
            media_type: Already-normalized media type (``text/plain`` or
                ``application/pdf``).
            data: Raw file bytes.

        Returns:
            The extracted text (may be empty; the caller applies the non-empty
            guard).
        """
        if media_type == MEDIA_TEXT:
            return data.decode("utf-8", errors="replace")

        # media_type == MEDIA_PDF (the only other supported type).
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    # -- persistence ------------------------------------------------------ #
    def _persist(self, profile_id: str, text: str) -> ResumeRecord:
        """Verify the profile exists then upsert its resume (5.1, 5.6).

        The profile-existence check happens AFTER the content guards per the
        task's guard order, but still before any write, so nothing is persisted
        for a nonexistent profile.

        Raises:
            NotFoundError: If the profile does not exist (404).
        """
        if self._repo.get_profile(profile_id) is None:
            raise NotFoundError("Profile not found")

        record = ResumeRecord(
            profile_id=profile_id, content=text, updated_at=_now_iso()
        )
        return self._repo.upsert_resume(record)
