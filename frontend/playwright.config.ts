import { defineConfig, devices } from '@playwright/test';

/**
 * HiveMind E2E Test Configuration.
 * 
 * We primarily test against the MOCK environment for speed and reliability.
 */
export default defineConfig({
    testDir: './',
    testMatch: '**/*.spec.ts',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    use: {
        /* Base URL should match Vite's default dev port */
        baseURL: 'http://localhost:5173',
        trace: 'on',
        video: 'on',
        screenshot: 'on',
    },

    /* Configure projects for major browsers */
    projects: [
        // Setup project
        {
          name: 'setup',
          testMatch: /auth\.setup\.ts/,
        },
        {
            name: 'chromium',
            use: { 
              ...devices['Desktop Chrome'],
              // Use prepared auth state.
              storageState: 'playwright/.auth/user.json',
            },
            dependencies: ['setup'],
        },
    ],

    /* Run local dev server before starting tests (in Mock mode) */
    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: true,
        timeout: 120 * 1000,
    },
});
