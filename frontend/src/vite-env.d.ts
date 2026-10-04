/// <reference types="vite/client" />

/**
 * Typed Vite environment variables (Task 14.3).
 *
 * `VITE_API_BASE_URL` optionally overrides the API base URL used by
 * `src/api/apiClient.ts`. When unset, the client defaults to `/api`, which the
 * dev server proxies to the backend (see `vite.config.ts`).
 */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
