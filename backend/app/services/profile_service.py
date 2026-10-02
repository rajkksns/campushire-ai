"""ProfileService: profile, skill, certification, and project orchestration.

This service sits between the routers and the repository (layered dependency
direction: routers -> services -> kernel + repository). It depends only on the
pure kernel (``skill_normalize``) and the :class:`Repository`; it never imports
FastAPI or sqlite3 directly.

It owns the two cross-cutting business rules for profile-owned collections:

* **Single normalization rule.** Skill names are canonicalized with the
  kernel's :func:`skill_normalize` and the normalized form is stored on the
  record, so the repository's uniqueness constraint and the comparator share
  one rule (Requirements 2.6, 8.1).
* **404-over-409 precedence (Requirement 15.5).** Every mutating sub-resource
  operation verifies the parent profile exists FIRST, raising
  :class:`NotFoundError` (404) before any conflict check runs. Thus a duplicate
  skill under a nonexistent profile yields 404, not 409.

Identifiers are generated with :func:`uuid.uuid4` and timestamps are ISO-8601
UTC strings produced here in the adapter layer (the kernel stays clock-free).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.kernel.normalize import skill_normalize
from app.repository.repository import (
    CertificationRecord,
    ProfileRecord,
    ProjectRecord,
    Repository,
    SkillRecord,
)
from app.services.errors import ConflictError, NotFoundError

__all__ = ["ProfileService"]

# Default proficiency when a skill is added without one (Requirement 2.5). The
# request schema already defaults this, but the service stays correct when
# called directly.
_DEFAULT_PROFICIENCY = 1


def _new_id() -> str:
    """Return a fresh opaque identifier (hex form of a random UUID)."""
    return uuid4().hex


def _now_iso() -> str:
    """Return the current time as an ISO-8601 UTC string.

    This is the single allowed non-kernel source of wall-clock time; it lives
    in the service/adapter layer so the analysis kernel stays deterministic.
    """
    return datetime.now(timezone.utc).isoformat()


class ProfileService:
    """CRUD orchestration for profiles and their owned collections."""

    def __init__(self, repository: Repository) -> None:
        """Store the injected repository.

        Args:
            repository: The persistence adapter. The service does not open or
                own database connections itself (dependency injection), keeping
                it testable with an in-memory :class:`Repository`.
        """
        self._repo = repository

    # -- internal helpers ------------------------------------------------- #
    def _require_profile(self, profile_id: str) -> ProfileRecord:
        """Return the profile or raise :class:`NotFoundError` (404).

        Centralizes the parent-existence check that enforces the 404-over-409
        precedence (Requirement 15.5): callers invoke this before any conflict
        evaluation.
        """
        profile = self._repo.get_profile(profile_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile

    # -- profiles --------------------------------------------------------- #
    def create_profile(self, name: str) -> ProfileRecord:
        """Create a new profile and return the stored record (Requirement 1.1).

        Args:
            name: The profile name (already trimmed/validated at the boundary).

        Returns:
            The persisted :class:`ProfileRecord` with its generated id and
            creation timestamp.
        """
        record = ProfileRecord(id=_new_id(), name=name, created_at=_now_iso())
        return self._repo.create_profile(record)

    def get_profile_detail(
        self, profile_id: str
    ) -> tuple[
        ProfileRecord,
        list[SkillRecord],
        list[CertificationRecord],
        list[ProjectRecord],
    ]:
        """Assemble a profile with its owned collections (Requirements 1.3, 1.4).

        Args:
            profile_id: The profile to load.

        Returns:
            A tuple ``(profile, skills, certifications, projects)``. The router
            maps this to ``ProfileDetailResponse``.

        Raises:
            NotFoundError: If the profile does not exist (1.4).
        """
        profile = self._require_profile(profile_id)
        skills = self._repo.list_skills(profile_id)
        certs = self._repo.list_certifications(profile_id)
        projects = self._repo.list_projects(profile_id)
        return profile, skills, certs, projects

    def update_profile_name(self, profile_id: str, name: str) -> ProfileRecord:
        """Rename a profile (Requirement 1.5).

        Args:
            profile_id: The profile to rename.
            name: The new name (trimmed/validated at the boundary).

        Returns:
            The updated :class:`ProfileRecord`.

        Raises:
            NotFoundError: If the profile does not exist.
        """
        existing = self._require_profile(profile_id)
        self._repo.update_profile_name(profile_id, name)
        return ProfileRecord(
            id=existing.id, name=name, created_at=existing.created_at
        )

    def delete_profile(self, profile_id: str) -> None:
        """Delete a profile; owned rows cascade in the DB (Requirement 16.3).

        Args:
            profile_id: The profile to delete.

        Raises:
            NotFoundError: If the profile does not exist.
        """
        if not self._repo.delete_profile(profile_id):
            raise NotFoundError("Profile not found")

    # -- skills ----------------------------------------------------------- #
    def add_skill(
        self,
        profile_id: str,
        name: str,
        skill_type: str,
        proficiency: int | None = None,
    ) -> SkillRecord:
        """Add a skill to a profile (Requirements 2.1, 2.2, 2.5, 2.6, 15.5).

        Enforces the 404-over-409 precedence: the profile's existence is
        checked FIRST, so a duplicate skill under a nonexistent profile raises
        :class:`NotFoundError` (404), not :class:`ConflictError` (409)
        (Requirement 15.5).

        The name is canonicalized with :func:`skill_normalize` and the
        normalized form stored on the record so the repository uniqueness
        constraint and the comparator share one rule (Requirements 2.6, 8.1).

        Args:
            profile_id: Parent profile.
            name: Skill name (trimmed/validated at the boundary).
            skill_type: ``"technical"`` or ``"soft"``.
            proficiency: Integer 1..5; defaults to 1 when omitted (2.5).

        Returns:
            The stored :class:`SkillRecord`.

        Raises:
            NotFoundError: If the profile does not exist (checked first, 15.5).
            ConflictError: If a same-type, same-normalized skill already exists
                for the profile (case-insensitive duplicate, 2.6).
        """
        self._require_profile(profile_id)  # 404 precedes 409 (15.5)

        normalized = skill_normalize(name)
        if self._repo.skill_exists(skill_type, normalized, profile_id):
            raise ConflictError("Skill already exists for this profile")

        level = _DEFAULT_PROFICIENCY if proficiency is None else proficiency
        record = SkillRecord(
            id=_new_id(),
            profile_id=profile_id,
            name=name,
            normalized=normalized,
            skill_type=skill_type,
            proficiency=level,
        )
        return self._repo.add_skill(record)

    def remove_skill(self, profile_id: str, skill_id: str) -> None:
        """Remove a skill from a profile (Requirement 2.7).

        Verifies the parent profile exists first (15.5), then deletes the
        skill.

        Args:
            profile_id: Parent profile.
            skill_id: The skill to remove.

        Raises:
            NotFoundError: If the profile or the skill does not exist.
        """
        self._require_profile(profile_id)
        if not self._repo.delete_skill(profile_id, skill_id):
            raise NotFoundError("Skill not found")

    # -- certifications --------------------------------------------------- #
    def add_certification(self, profile_id: str, name: str) -> CertificationRecord:
        """Add a certification to a profile (Requirement 3.1).

        Verifies the parent profile exists first (15.5).

        Args:
            profile_id: Parent profile.
            name: Certification name (trimmed/validated at the boundary).

        Returns:
            The stored :class:`CertificationRecord`.

        Raises:
            NotFoundError: If the profile does not exist.
        """
        self._require_profile(profile_id)
        record = CertificationRecord(
            id=_new_id(), profile_id=profile_id, name=name
        )
        return self._repo.add_certification(record)

    def remove_certification(self, profile_id: str, cert_id: str) -> None:
        """Remove a certification from a profile (Requirement 3.3).

        Args:
            profile_id: Parent profile.
            cert_id: The certification to remove.

        Raises:
            NotFoundError: If the profile or the certification does not exist.
        """
        self._require_profile(profile_id)
        if not self._repo.delete_certification(profile_id, cert_id):
            raise NotFoundError("Certification not found")

    # -- projects --------------------------------------------------------- #
    def add_project(
        self, profile_id: str, title: str, description: str | None = None
    ) -> ProjectRecord:
        """Add an academic project to a profile (Requirement 4.1).

        Verifies the parent profile exists first (15.5).

        Args:
            profile_id: Parent profile.
            title: Project title (trimmed/validated at the boundary).
            description: Optional project description.

        Returns:
            The stored :class:`ProjectRecord`.

        Raises:
            NotFoundError: If the profile does not exist.
        """
        self._require_profile(profile_id)
        record = ProjectRecord(
            id=_new_id(),
            profile_id=profile_id,
            title=title,
            description=description,
        )
        return self._repo.add_project(record)

    def remove_project(self, profile_id: str, project_id: str) -> None:
        """Remove an academic project from a profile (Requirement 4.4).

        Args:
            profile_id: Parent profile.
            project_id: The project to remove.

        Raises:
            NotFoundError: If the profile or the project does not exist.
        """
        self._require_profile(profile_id)
        if not self._repo.delete_project(profile_id, project_id):
            raise NotFoundError("Project not found")
