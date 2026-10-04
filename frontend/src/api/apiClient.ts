/**
 * Typed API client (Task 14.3, Requirements 14.4, 14.5).
 *
 * This module is the ONLY path from the UI to the backend. Every endpoint in
 * `backend/app/routers/` is exposed as a typed function whose request bodies
 * and responses use the shared contract types in `src/types`. Non-2xx
 * responses are parsed into a readable {@link ApiError} so callers surface a
 * human-readable message (14.4) instead of a raw status code.
 *
 * Base URL resolution (14.5): `import.meta.env.VITE_API_BASE_URL` when set,
 * otherwise `/api` — which the Vite dev server proxies to the backend
 * (`http://localhost:8000`) so the browser never makes a cross-origin request
 * and the backend needs no CORS configuration.
 */

import type {
  AnalysisRequest,
  AnalysisResponse,
  ApiErrorBody,
  ApiErrorCode,
  CertificationCreate,
  CertificationResponse,
  DeletedResponse,
  HealthResponse,
  ProfileCreate,
  ProfileDetailResponse,
  ProfileResponse,
  ProfileUpdate,
  ProjectCreate,
  ProjectResponse,
  ResumeResponse,
  SkillCreate,
  SkillResponse,
} from '../types';

/** Base URL for the API. Defaults to the Vite-proxied `/api` prefix (14.5). */
const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  '/api';

/**
 * Error thrown for any non-2xx API response. Carries the HTTP status, the
 * backend error code when present, the failing field for 422 validation
 * errors, and a human-readable message suitable for display (14.4).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code?: ApiErrorCode;
  readonly field?: string;

  constructor(
    status: number,
    message: string,
    code?: ApiErrorCode,
    field?: string,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

/** Type guard: does a parsed JSON body match the backend error shape? */
function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === 'object' &&
    value !== null &&
    'error' in value &&
    'message' in value &&
    typeof (value as Record<string, unknown>).error === 'string' &&
    typeof (value as Record<string, unknown>).message === 'string'
  );
}

/**
 * Convert a failed `Response` into an {@link ApiError} with the best available
 * human-readable message. Tries the structured backend error body first, then
 * falls back to any text, then to a generic status-based message.
 */
async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }

  if (isApiErrorBody(body)) {
    const prefix = body.field ? `${body.field}: ` : '';
    return new ApiError(
      response.status,
      `${prefix}${body.message}`,
      body.error,
      body.field,
    );
  }

  const fallback =
    response.statusText || `Request failed with status ${response.status}`;
  return new ApiError(response.status, fallback);
}

/**
 * Core fetch wrapper. Serializes a JSON body when provided, sets the right
 * headers, and either returns the parsed JSON (typed as `T`) or throws an
 * {@link ApiError}. A 204/empty body resolves to `undefined`.
 */
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const init: RequestInit = { method, headers: {} };

  if (body !== undefined) {
    (init.headers as Record<string, string>)['Content-Type'] =
      'application/json';
    init.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    // Network failure / server unreachable — surface a readable message (14.4).
    throw new ApiError(
      0,
      'Could not reach the server. Check that the backend is running.',
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/**
 * Multipart variant for resume uploads. The browser sets the multipart
 * boundary header automatically from the `FormData`, so we must NOT set
 * `Content-Type` ourselves.
 */
async function requestMultipart<T>(
  method: string,
  path: string,
  form: FormData,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { method, body: form });
  } catch {
    throw new ApiError(
      0,
      'Could not reach the server. Check that the backend is running.',
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

// --------------------------------------------------------------------------- //
// Health
// --------------------------------------------------------------------------- //

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('GET', '/health');
}

// --------------------------------------------------------------------------- //
// Profiles
// --------------------------------------------------------------------------- //

export function createProfile(body: ProfileCreate): Promise<ProfileResponse> {
  return request<ProfileResponse>('POST', '/profiles', body);
}

export function getProfile(profileId: string): Promise<ProfileDetailResponse> {
  return request<ProfileDetailResponse>(
    'GET',
    `/profiles/${encodeURIComponent(profileId)}`,
  );
}

export function updateProfile(
  profileId: string,
  body: ProfileUpdate,
): Promise<ProfileResponse> {
  return request<ProfileResponse>(
    'PUT',
    `/profiles/${encodeURIComponent(profileId)}`,
    body,
  );
}

export function deleteProfile(profileId: string): Promise<DeletedResponse> {
  return request<DeletedResponse>(
    'DELETE',
    `/profiles/${encodeURIComponent(profileId)}`,
  );
}

// --------------------------------------------------------------------------- //
// Skills
// --------------------------------------------------------------------------- //

export function addSkill(
  profileId: string,
  body: SkillCreate,
): Promise<SkillResponse> {
  return request<SkillResponse>(
    'POST',
    `/profiles/${encodeURIComponent(profileId)}/skills`,
    body,
  );
}

export function removeSkill(
  profileId: string,
  skillId: string,
): Promise<DeletedResponse> {
  return request<DeletedResponse>(
    'DELETE',
    `/profiles/${encodeURIComponent(profileId)}/skills/${encodeURIComponent(skillId)}`,
  );
}

// --------------------------------------------------------------------------- //
// Certifications
// --------------------------------------------------------------------------- //

export function addCertification(
  profileId: string,
  body: CertificationCreate,
): Promise<CertificationResponse> {
  return request<CertificationResponse>(
    'POST',
    `/profiles/${encodeURIComponent(profileId)}/certifications`,
    body,
  );
}

export function removeCertification(
  profileId: string,
  certId: string,
): Promise<DeletedResponse> {
  return request<DeletedResponse>(
    'DELETE',
    `/profiles/${encodeURIComponent(profileId)}/certifications/${encodeURIComponent(certId)}`,
  );
}

// --------------------------------------------------------------------------- //
// Projects
// --------------------------------------------------------------------------- //

export function addProject(
  profileId: string,
  body: ProjectCreate,
): Promise<ProjectResponse> {
  return request<ProjectResponse>(
    'POST',
    `/profiles/${encodeURIComponent(profileId)}/projects`,
    body,
  );
}

export function removeProject(
  profileId: string,
  projectId: string,
): Promise<DeletedResponse> {
  return request<DeletedResponse>(
    'DELETE',
    `/profiles/${encodeURIComponent(profileId)}/projects/${encodeURIComponent(projectId)}`,
  );
}

// --------------------------------------------------------------------------- //
// Resume (paste JSON or multipart upload) — PUT /profiles/{id}/resume
// --------------------------------------------------------------------------- //

/** Store a resume by pasting raw text (JSON body `{ content }`). */
export function saveResumeText(
  profileId: string,
  content: string,
): Promise<ResumeResponse> {
  return request<ResumeResponse>(
    'PUT',
    `/profiles/${encodeURIComponent(profileId)}/resume`,
    { content },
  );
}

/**
 * Store a resume by uploading a file (multipart). Accepted media types are
 * `text/plain` and `application/pdf`; the backend enforces media-type (415),
 * size (413), and non-empty (422) guards in that order.
 */
export function uploadResumeFile(
  profileId: string,
  file: File,
): Promise<ResumeResponse> {
  const form = new FormData();
  form.append('file', file);
  return requestMultipart<ResumeResponse>(
    'PUT',
    `/profiles/${encodeURIComponent(profileId)}/resume`,
    form,
  );
}

// --------------------------------------------------------------------------- //
// Analyses
// --------------------------------------------------------------------------- //

export function createAnalysis(
  profileId: string,
  body: AnalysisRequest,
): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(
    'POST',
    `/profiles/${encodeURIComponent(profileId)}/analyses`,
    body,
  );
}

export function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return request<AnalysisResponse>(
    'GET',
    `/analyses/${encodeURIComponent(analysisId)}`,
  );
}

export function listAnalyses(
  profileId: string,
): Promise<AnalysisResponse[]> {
  return request<AnalysisResponse[]>(
    'GET',
    `/profiles/${encodeURIComponent(profileId)}/analyses`,
  );
}
