# T2D Diabetic Nephropathy Cohort Demo — Narrator Cue Sheet

**Length target:** 7–9 minutes
**Audience:** Clinical researchers, data scientists, IDR / OMOP teams, ML engineers
**One-liner before recording:** "Watch a research cohort definition — T2D patients with diabetic nephropathy on metformin, 2020 to 2023 — go from declarative YAML to a MEDS-ready shard that an ML team can consume directly."

---

## Beat 1 — Open on the loaded scenario (0:00–0:40)

**Frame:** Inspector at Step 1 Input → Raw YAML tab, scenario already loaded.

**Narration:**

> Cohort definition is one of the most repeatedly hand-rolled artifacts in clinical research. Every study redefines T2D, redefines diabetic nephropathy, redefines metformin exposure. This scenario captures all three plus a 2020–2023 index window in 250 lines of declarative PSDL. The point of this demo is to show how the same audit-friendly tooling that handles real-time clinical algorithms also handles research cohorts.

**Action:** Scroll slowly through the YAML — pause briefly on `population`, `signal_groups`, `signals`, `logic`.

**Wait:** 1 second.

---

## Beat 2 — Population block (0:40–1:40)

**Frame:** Scroll YAML to the `population:` block (around line 50).

**Narration:**

> Cohort eligibility lives in the population block, not in logic rules. This is intentional — PSDL keeps numeric thresholds in `logic` and categorical inclusion criteria in `population` because they have different audit semantics. Inclusion: adults, T2DM diagnosis, diabetic nephropathy diagnosis, active metformin, index year between 2020 and 2023. Exclusion: type-1 diabetes, chronic dialysis (those are ESRD, not nephropathy under study), and pregnancy. A clinician reviewing this cohort definition can spot a missed exclusion in seconds — that's the auditability the spec is built for.

**Wait:** 2 seconds.

---

## Beat 3 — Validate (1:40–2:10)

**Frame:** Scroll back to the top, click **"Validate Scenario"**.

**Narration:**

> Same structural check the clinical scenario got. Population blocks, signal groups, severity enums, ref consistency — psdl-lang validates all of it.

**Action:** Wait for green "Valid" indicator. Note the 2 unused-signal warnings (`creatinine`, `fasting_glucose`) if visible.

**Narration (after green):**

> Clean parse. Two warnings about signals declared but not used in trends — `creatinine` and `fasting_glucose`. Those are intentional in this cohort — they're requested as data via signal-groups for downstream analytics, even though no logic rule references them directly. Warnings are non-blocking; the cohort definition still ships.

**Wait:** 2 seconds.

---

## Beat 4 — Continue to Preview, examine the outline (2:10–3:30)

**Frame:** Click **"Continue →"** to advance to Step 2.

**Narration:**

> Now we're in the semantic preview. Look at how the outline tree organizes this — population is at the top, then signal groups, then signals, then trends, then logic, then outputs. This isn't just visual: this is the dependency order an execution platform processes them in.

**Action:** Expand the `logic` branch. Find the CKD-stage rules (`ckd_stage_3a`, `ckd_stage_3b`, `ckd_stage_4`, `ckd_stage_5`).

**Narration:**

> Here's the stratification that makes this cohort useful for analysis. We don't just identify nephropathy patients — we KDIGO-stage them by eGFR. Stage 3a is 45 to 60, stage 3b is 30 to 45, stage 4 is 15 to 30, stage 5 is below 15. And `metformin_caution` over here — that's a guideline rule: metformin active with eGFR below 30 is a contraindication flag.

**Wait:** 3 seconds.

---

## Beat 5 — DAG view (3:30–4:30)

**Frame:** Switch to the DAG visualization.

**Narration:**

> Same algorithm as a directed acyclic graph. The signals on the left feed trends in the middle — HbA1c, eGFR, UACR, and their twelve-month deltas — and trends feed the logic rules on the right. The colored rules at the far right are the composite phenotypes: advanced nephropathy, metformin caution, high-risk progression.

**Action:** Pan to show the egfr → ckd_stage_4 → advanced_nephropathy → metformin_caution chain.

**Narration:**

> This is the kind of cohort that's normally one big opaque SQL query that nobody can audit a year later. PSDL forces the structure into the open. Every threshold, every composition, every severity is here on the page.

**Wait:** 3 seconds.

---

## Beat 6 — Terminology anchoring (4:30–5:30)

**Frame:** Click the Anchor button or open the anchoring panel.

**Narration:**

> Anchoring binds the abstract signal references — `hemoglobin_a1c`, `estimated_glomerular_filtration_rate`, `urine_albumin_creatinine_ratio` — to actual OMOP concept IDs. For a research cohort, this is the layer that lets the same PSDL definition run against UF's IDR, MIT's MIMIC-IV, or Stanford's STARR without rewriting a single query — they each provide a datasetSpec that maps these OMOP concepts to their physical tables.

**Action:** Show anchored signals with their LOINC and SNOMED codes + confidence indicators.

**Narration:**

> HbA1c: LOINC 4548-4, high confidence. eGFR: LOINC 33914-3. UACR: LOINC 9318-7. Metformin: RxNorm. These IDs travel in the bundle as the contract between authoring and execution.

**Wait:** 3 seconds.

---

## Beat 7 — Export the bundle (5:30–6:30)

**Frame:** Click **"3 Export"**. Show the bundle JSON preview.

**Narration:**

> The certified bundle is the unit a research collaboration ships. It's checksummed and self-contained — the YAML, the parsed IR, the terminology anchors at high or medium confidence, the audit block citing ADA 2023 and KDIGO 2022, and a human-readable summary. An IRB review can read the audit block without ever opening the YAML.

**Action:** Scroll the bundle JSON. Highlight `audit.intent` and `audit.rationale`.

**Wait:** 2 seconds.

---

## Beat 8 — MEDS Preview — the ML handoff (6:30–8:00)

**Frame:** Right column of Export step, **"Preview MEDS shape"** card.

**Narration:**

> Here's where the research cohort actually meets the ML team. The Medical Event Data Standard — MEDS — is the format that ETHOS, CLMBR, and the MIMIC-IV-MEDS benchmark all consume. Before any institution writes a single ETL job, Inspector can generate a synthetic preview: ten event rows in the exact shape the cohort will produce. Subject ID, time, code, numeric value.

**Action:** Click **"Generate 10-row preview"**.

**Narration (after card populates):**

> Ten synthetic events, three synthetic subjects. The subject IDs are negative integers — by construction these can never collide with real OMOP person IDs. The code chips show what the ML team will receive: LOINC 4548-4 for HbA1c, LOINC 33914-3 for eGFR, LOINC 9318-7 for UACR, RxNorm for metformin. The Parquet was validated against the official `meds.schema.data_schema` before write — so when this cohort runs against real data at UF or anywhere else, the ML team gets a file that's bit-compatible with whatever benchmark they're already using.

**Wait:** 4 seconds on the code chips.

---

## Beat 9 — Closing (8:00–8:30)

**Frame:** Wide shot of the Export step. Both the bundle and the MEDS preview card visible.

**Narration:**

> One PSDL definition. One auditable pipeline. Two artifacts: a certified bundle for execution platforms, and a MEDS preview that lets an ML team plan their pipeline before the institution has touched the data. This is the future of reproducible clinical research.

**Action:** Hold the frame. Cut.

---

## After recording (off-camera)

Open DevTools console and run:

```js
window.__saveBundle();
window.__saveMeds();
```

Drop the downloaded files into `docs/demos/t2d-nephropathy-cohort/artifacts/`:

- `t2d-cohort-bundle.json`
- `t2d-cohort-meds-preview.json`

---

## Quick reference

| Beat | Click | Watch for |
|------|-------|-----------|
| 3 | Validate Scenario | Green + 2 non-blocking warnings |
| 4 | Continue → / Step 2 | CKD-stage rules in outline |
| 5 | DAG tab (if separate) | egfr → ckd_stage → advanced_nephropathy chain |
| 6 | Anchor button | LOINC + RxNorm chips on signals |
| 7 | Step 3 Export | Audit block visible in bundle JSON |
| 8 | Generate 10-row preview | Code chips for all anchored signals |

---

## Why this demo matters for IDR / UF Shands

This is the scenario shape that answers Ben Staley and Jason's "we want to replace ad-hoc Atlas cohorts" ask. Same PSDL definition, two institutions, deterministic MEDS handoff — that's the ML-native cohort pipeline they don't have today.
