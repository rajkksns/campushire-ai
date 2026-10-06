
// --------------------------------------------------------------------------- //
// Enums (string-literal unions matching the backend Literal values)
// --------------------------------------------------------------------------- //

/** `skill_type` is exactly "technical" or "soft" (common.py `SkillType`). */
export type SkillType = 'technical' | 'soft';

/** Breakdown category mirrors the kernel `Category` enum (common.py). */
export type BreakdownCategory = 'matched' | 'weak' | 'missing';

/** Roadmap items only ever cover gaps (common.py `RoadmapCategory`). */
export type RoadmapCategory = 'missing' | 'weak';

/** Maximum accepted job-description length after trimming (common.py). */
export const MAX_JOB_DESCRIPTION_LENGTH = 20000;

/** Inclusive proficiency bounds (skill.py: ge=1, le=5). */
export const MIN_PROFICIENCY = 1;
export const MAX_PROFICIENCY = 5;

/** Accepted resume upload media types (resume_service ordered guards, 5.4). */
export const RESUME_MEDIA_TYPES = ['text/plain', 'application/pdf'] as const;
export type ResumeMediaType = (typeof RESUME_MEDIA_TYPES)[number];

// --------------------------------------------------------------------------- //
// Profile (schemas/profile.py)
// --------------------------------------------------------------------------- //

/** Request body for `POST /profiles` and `PUT /profiles/{id}`. */
export interface ProfileCreate {
  name: string;
}
export type ProfileUpdate = ProfileCreate;

/** `POST`/`PUT` response: identity + creation timestamp (ProfileResponse). */
export interface ProfileResponse {
  id: string;
  name: string;
  created_at: string;
}

/** `GET /profiles/{id}` detail with owned collections (ProfileDetailResponse). */
export interface ProfileDetailResponse {
  id: string;
  name: string;
  created_at: string;
  skills: SkillResponse[];
  certifications: CertificationResponse[];
  projects: ProjectResponse[];
}

// --------------------------------------------------------------------------- //
// Skill (schemas/skill.py)
// --------------------------------------------------------------------------- //

/**
 * Request body for `POST /profiles/{id}/skills`.
 * `proficiency` defaults to 1 server-side when omitted (2.5); it is optional
 * here so callers may rely on that default.
 */
export interface SkillCreate {
  name: string;
  skill_type: SkillType;
  proficiency?: number;
}

export interface SkillResponse {
  id: string;
  name: string;
  skill_type: SkillType;
  proficiency: number;
}

// --------------------------------------------------------------------------- //
// Certification (schemas/certification.py)
// --------------------------------------------------------------------------- //

export interface CertificationCreate {
  name: string;
}

export interface CertificationResponse {
  id: string;
  name: string;
}

// --------------------------------------------------------------------------- //
// Project (schemas/project.py)
// --------------------------------------------------------------------------- //

/** `description` is optional and stored as provided when present (4.3). */
export interface ProjectCreate {
  title: string;
  description?: string | null;
}

export interface ProjectResponse {
  id: string;
  title: string;
  description?: string | null;
}

// --------------------------------------------------------------------------- //
// Resume (schemas/resume.py)
// --------------------------------------------------------------------------- //

/** JSON paste body for `PUT /profiles/{id}/resume` (ResumePaste). */
export interface ResumePaste {
  content: string;
}

/** Confirmation returned after storing a resume (ResumeResponse). */
export interface ResumeResponse {
  profile_id: string;
  updated_at: string;
}

// --------------------------------------------------------------------------- //
// Analysis (schemas/analysis.py)
// --------------------------------------------------------------------------- //

/** Request body for `POST /profiles/{id}/analyses` (AnalysisRequest). */
export interface AnalysisRequest {
  job_description: string;
}

/** One itemized score contribution (BreakdownItemResponse, 10.10). */
export interface BreakdownItemResponse {
  name: string;
  weight: number;
  category: BreakdownCategory;
  points: number;
}

/** A matched required skill with the student's proficiency (11). */
export interface MatchedSkillResponse {
  name: string;
  weight: number;
  proficiency: number;
}

/** A weak required skill with the student's proficiency (11.2). */
export interface WeakSkillResponse {
  name: string;
  weight: number;
  proficiency: number;
}

/** A missing required skill (11.1). */
export interface MissingSkillResponse {
  name: string;
  weight: number;
}

/** One ordered roadmap item for a gap skill (RoadmapItemResponse, 12.7). */
export interface RoadmapItemResponse {
  name: string;
  weight: number;
  category: RoadmapCategory;
  priority_rank: number;
}

/**
 * Fully materialized analysis result (AnalysisResponse).
 * `readiness_score` is an integer in [0, 100]. The ordered lists preserve the
 * kernel's deterministic ordering as returned by the server.
 */
export interface AnalysisResponse {
  id: string;
  readiness_score: number;
  breakdown: BreakdownItemResponse[];
  matched: MatchedSkillResponse[];
  weak: WeakSkillResponse[];
  missing: MissingSkillResponse[];
  roadmap: RoadmapItemResponse[];
}

// --------------------------------------------------------------------------- //
// Errors (schemas/errors.py + main.py error-body builders)
// --------------------------------------------------------------------------- //

/**
 * Discriminated error `error` codes the backend may return (main.py builders).
 * 422 bodies additionally carry a `field`; the rest carry only `message`.
 */
export type ApiErrorCode =
  | 'validation_error'
  | 'not_found'
  | 'conflict'
  | 'unsupported_media_type'
  | 'payload_too_large'
  | 'internal_error';

/**
 * Shape of any JSON error body returned by the API. `field` is present only on
 * `validation_error` (422) bodies naming the single failing field (18.2).
 */
export interface ApiErrorBody {
  error: ApiErrorCode;
  message: string;
  field?: string;
}

// --------------------------------------------------------------------------- //
// Generic deleted/health confirmations
// --------------------------------------------------------------------------- //

/** `{ "status": "deleted" }` returned by DELETE endpoints. */
export interface DeletedResponse {
  status: string;
}

/** `{ "status": "ok" }` returned by `GET /health`. */
export interface HealthResponse {
  status: string;
}
