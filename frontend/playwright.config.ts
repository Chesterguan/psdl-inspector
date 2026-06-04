import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const BACKEND = path.resolve(__dirname, '../backend');

// The real local database for the live-plan e2e: MIMIC-IV loaded into OMOP CDM
// (prometheno-postgres). Override via PREFLIGHT_DB_URL in the environment.
const MIMIC_DSN =
  process.env.PREFLIGHT_DB_URL ||
  'postgresql://prometheno:prometheno_dev_2024@localhost:5434/prometheno_omop';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: 'http://localhost:9806',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      // Inspector backend with a live local DB configured (real EXPLAIN path).
      command: '.venv/bin/uvicorn app.main:app --port 8200 --log-level warning',
      cwd: BACKEND,
      url: 'http://localhost:8200/api/preflight/catalogs',
      reuseExistingServer: false,
      timeout: 60_000,
      env: { PREFLIGHT_DB_URL: MIMIC_DSN },
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:9806',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
