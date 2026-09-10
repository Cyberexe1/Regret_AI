import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

/**
 * Separate from vite.config.ts (which the app dev server/build use) so
 * test-only configuration (jsdom environment, setup file) never affects
 * the production build. No real network access happens in any test here -
 * `global.fetch` is mocked per-test; nothing calls a real backend, AWS
 * service, or Bedrock/DynamoDB endpoint.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    css: false,
  },
});
