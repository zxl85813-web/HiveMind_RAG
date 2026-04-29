import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**'],
    reporters: process.env.CI
      ? ['default', ['allure-vitest/reporter', { resultsDir: 'allure-results' }]]
      : ['default'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      include: [
        'src/hooks/**',
        'src/stores/**',
        'src/services/**',
        'src/guards/**',
        'src/config/**',
        'src/components/common/**',
      ],
      exclude: [
        'src/pages/**',
        'src/components/chat/**',
        'src/components/knowledge/**',
        'src/components/agents/**',
        'src/main.tsx',
        'src/App.tsx',
        'src/i18n/**',
        'src/mock/**',
        'src/styles/**',
        'src/assets/**',
        'src/types/**',
        '**/*.css',
        '**/*.module.css',
      ],
    },
  },
});
