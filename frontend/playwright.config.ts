import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E config for QuantAI.
 *
 * The app is a static export (`output: 'export'` → `out/`), so we serve that
 * directory with `serve` rather than `next start`. By default the suite runs with
 * NO backend — it exercises the public landing page, the login form, and guest
 * navigation, all of which work offline via demo fallbacks. Playwright starts the
 * server itself (or reuses one already on :3000). Run `npm run build` first.
 *
 * To also run the authenticated login → screener → portfolio flow, start the
 * backend on :8000 and run with `E2E_BACKEND=1`.
 */
const PORT = Number(process.env.E2E_PORT || 3000)
const baseURL = `http://localhost:${PORT}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    // Serve the static export (`out/`). Assumes `npm run build` has run.
    command: `npx serve out -l ${PORT} --no-port-switching`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
