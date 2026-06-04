import { test, expect, type Page } from '@playwright/test';

// A realistic clinical scenario (not a toy): AKI early-detection with two lab
// signals, three trends, and staged logic rules.
const SCENARIO = `# PSDL Example: AKI Early Detection
scenario: AKI_Early_Detection
version: "0.3.1"
description: "Detect early signs of Acute Kidney Injury"

signals:
  Cr:
    ref: creatinine
    concept_id: 3016723
    unit: mg/dL

  BUN:
    ref: blood_urea_nitrogen
    concept_id: 3013682
    unit: mg/dL

trends:
  cr_delta_48h:
    expr: delta(Cr, 48h)
    description: "Creatinine change over 48 hours"

  cr_delta_24h:
    expr: delta(Cr, 24h)
    description: "Creatinine change over 24 hours"

  bun_delta_48h:
    expr: delta(BUN, 48h)
    description: "BUN change over 48 hours"

logic:
  aki_stage1:
    when: cr_delta_48h >= 0.3
    severity: medium
    description: "AKI Stage 1 - Creatinine rise >= 0.3 mg/dL in 48h"

  aki_stage2:
    when: cr_delta_48h >= 0.3 AND cr_delta_24h >= 0.5
    severity: high
    description: "AKI Stage 2 - Progressing injury"

  renal_concern:
    when: aki_stage1 AND bun_delta_48h >= 5
    severity: high
    description: "Combined renal function concern"`;

// A realistic cohort extraction for that scenario: pull the creatinine + BUN time
// series for an inpatient cohort, concept- and date-filtered (NOT `SELECT *`).
const COHORT_SQL = `SELECT p.person_id, m.measurement_concept_id, m.measurement_datetime, m.value_as_number
FROM person p
JOIN visit_occurrence v ON v.person_id = p.person_id
JOIN measurement m ON m.person_id = p.person_id AND m.visit_occurrence_id = v.visit_occurrence_id
WHERE m.measurement_concept_id IN (3016723, 3013682)
  AND m.measurement_datetime >= '2150-01-01'`;

async function dismissGuide(page: Page) {
  const skip = page.getByRole('button', { name: 'Skip' });
  if (await skip.isVisible().catch(() => false)) await skip.click();
}

test('full workflow: author → validate → DAG → certify → live preflight on real MIMIC', async ({ page }) => {
  await page.goto('/');
  await dismissGuide(page);

  // --- Input: author the scenario and validate ---
  await page.getByRole('button', { name: 'Raw YAML' }).click();
  await page.getByRole('textbox', { name: /Start typing your PSDL/i }).fill(SCENARIO);
  await page.getByRole('button', { name: 'Validate Scenario' }).click();
  await expect(page.getByText('Valid PSDL').first()).toBeVisible();

  // --- Preview: the scenario DAG ---
  await page.getByRole('button', { name: 'Continue to Preview' }).click();
  await expect(page.getByText('Scenario DAG')).toBeVisible();

  // --- Export: the certified bundle ---
  await page.getByRole('button', { name: 'Continue to Export' }).click();
  await expect(page.getByText('Certified Bundle')).toBeVisible();
  await expect(page.getByText(/AKI_Early_Detection\.json/)).toBeVisible();

  // --- Prepare: advance to step 4, switch to the Preflight panel ---
  await page.getByRole('button', { name: 'Next step' }).click();
  await expect(page.getByText(/Your scenario is certified/)).toBeVisible();
  await page.getByRole('button', { name: 'Preflight query' }).click();

  // The live-DB toggle exists only because the server has PREFLIGHT_DB_URL set.
  const live = page.getByRole('checkbox');
  await expect(live).toBeVisible();
  await live.check();

  // Run the realistic cohort extraction against the REAL MIMIC-OMOP database.
  await page.getByRole('textbox', { name: /SELECT person_id FROM person/i }).fill(COHORT_SQL);
  await page.getByRole('combobox', { name: 'Dialect' }).selectOption('postgres');
  await page.getByRole('button', { name: 'Run on local DB' }).click();

  // The report must come from a real EXPLAIN plan (live) with HIGH confidence,
  // and the scoped cohort query must be cheap against the real DB.
  await expect(page.getByText(/Live plan from your local database/)).toBeVisible();
  await expect(page.getByText('confidence: HIGH').first()).toBeVisible();
  await expect(page.getByText('runtime: FAST')).toBeVisible();
});

test('preflight flags the naive full-scan as expensive (live plan on real MIMIC)', async ({ page }) => {
  await page.goto('/preflight');
  await dismissGuide(page);

  const live = page.getByRole('checkbox');
  await expect(live).toBeVisible();
  await live.check();

  // The mistake a DS makes: an unfiltered scan of the 158M-row measurement table.
  await page.getByRole('textbox', { name: /SELECT person_id FROM person/i }).fill('SELECT * FROM measurement');
  await page.getByRole('combobox', { name: 'Dialect' }).selectOption('postgres');
  await page.getByRole('button', { name: 'Run on local DB' }).click();

  await expect(page.getByText(/Live plan from your local database/)).toBeVisible();
  await expect(page.getByText('confidence: HIGH').first()).toBeVisible();
  // A full scan of the real measurement table is NOT fast.
  await expect(page.getByText('runtime: HEAVY')).toBeVisible();
});
