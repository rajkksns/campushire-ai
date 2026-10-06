/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite + React configuration with the Vitest component test runner wired in.
// Tests run under jsdom with globals enabled and a setup file that registers
// the jest-dom matchers (Task 14.1).
//
// The dev server proxies `/api` to the FastAPI backend on 127.0.0.1:8000 so
// the browser makes same-origin requests and the backend needs no CORS
// configuration (Task 14.3). The `/api` prefix is stripped before forwarding
// because the backend routes are mounted at the root (e.g. `/profiles`,
// `/health`), matching the default base URL in `src/api/apiClient.ts`.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
