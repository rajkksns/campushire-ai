/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite + React configuration with the Vitest component test runner wired in.
// Tests run under jsdom with globals enabled and a setup file that registers
// the jest-dom matchers (Task 14.1).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
