# PSDL AI-Generate Benchmark — Seed Scenarios

> **STATUS: DRAFT — seed scenarios pending clinician validation.**
> Ground-truth scenarios for benchmarking Inspector's **Generate (AI)** function
> (see issue #19). Each is anchored to its **true protocol/source paper** — the
> citation is the ground truth that correctness / completeness / faithfulness are
> scored against. Thresholds below are drawn from the cited papers; a clinician
> should verify before these are treated as authoritative.

**How to run:** feed each `NL prompt` to `POST /api/generate/scenario`
(`provider: "ollama"` or `"openai"`), then score the output:

1. **Validity** — passes `psdl-lang` (automatic, from the generate response)
2. **Clinical correctness** — logic & thresholds match the cited protocol (1–5)
3. **Completeness** — all protocol signals/criteria captured (1–5)
4. **Faithfulness** — no thresholds/concepts absent from the cited paper (1–5)
5. **Usability** — ship as-is / minor edits / major edits

**PSDL fit note:** logic `when:` is numeric-only (trend comparisons + AND/OR).
Categorical criteria (e.g. "on dialysis", "post-op") go in the population block or
are encoded as 0/1 numeric flags.

---

## 1. Acute Kidney Injury — KDIGO staging

**Citation:** KDIGO Acute Kidney Injury Work Group. *KDIGO Clinical Practice Guideline for Acute Kidney Injury.* Kidney Int Suppl. 2012;2(1):1–138.

**Intent:** Detect and stage AKI from serum creatinine kinetics.

**Signals:** serum creatinine (mg/dL, OMOP 3016723); (baseline creatinine reference)

**Logic (numeric):**
- Stage 1: SCr increase ≥ 0.3 mg/dL within 48 h, **or** 1.5–1.9× baseline within 7 days
- Stage 2: SCr 2.0–2.9× baseline
- Stage 3: SCr ≥ 3.0× baseline, **or** SCr ≥ 4.0 mg/dL, **or** initiation of RRT

**Time windows:** Δ over 48 h; ratio vs 7-day baseline.

**NL prompt:**
> Build a PSDL scenario that detects and stages acute kidney injury by the KDIGO criteria using serum creatinine. Stage 1 is a creatinine rise of at least 0.3 mg/dL within 48 hours or 1.5 to 1.9 times baseline within 7 days; stage 2 is 2.0 to 2.9 times baseline; stage 3 is at least 3.0 times baseline or an absolute creatinine of 4.0 mg/dL or more. Use creatinine trends over 24 and 48 hour windows.

---

## 2. Sepsis screen — qSOFA (Sepsis-3)

**Citation:** Singer M, Deutschman CS, Seymour CW, et al. *The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3).* JAMA. 2016;315(8):801–810. doi:10.1001/jama.2016.0287.

**Intent:** Flag patients at high risk of poor sepsis outcomes (qSOFA ≥ 2).

**Signals:** respiratory rate (breaths/min); systolic blood pressure (mmHg); Glasgow Coma Scale (score, as a numeric mentation proxy)

**Logic (numeric):**
- qSOFA points: respiratory rate ≥ 22 (1), systolic BP ≤ 100 (1), GCS < 15 (1)
- High risk: qSOFA total ≥ 2

**NL prompt:**
> Create a PSDL scenario implementing the qSOFA sepsis screen from Sepsis-3. Award one point each for respiratory rate of 22 or more, systolic blood pressure of 100 mmHg or less, and a Glasgow Coma Scale below 15. Flag the patient as high risk for sepsis when two or more of these criteria are met.

---

## 3. Systemic Inflammatory Response Syndrome (SIRS)

**Citation:** Bone RC, Balk RA, Cerra FB, et al. *Definitions for sepsis and organ failure and guidelines for the use of innovative therapies in sepsis.* (ACCP/SCCM Consensus). Chest. 1992;101(6):1644–1655.

**Intent:** Detect SIRS (≥ 2 of 4 criteria).

**Signals:** temperature (°C); heart rate (bpm); respiratory rate (breaths/min); white blood cell count (×10⁹/L)

**Logic (numeric):**
- Criteria: temperature > 38 °C or < 36 °C; heart rate > 90; respiratory rate > 20; WBC > 12 or < 4 (×10⁹/L)
- SIRS: ≥ 2 criteria met

**NL prompt:**
> Generate a PSDL scenario for SIRS using the 1992 ACCP/SCCM criteria. The four criteria are: temperature above 38°C or below 36°C; heart rate above 90; respiratory rate above 20; and white blood cell count above 12 or below 4 (x10^9/L). Flag SIRS when at least two criteria are present.

---

## 4. Diabetic Ketoacidosis (DKA)

**Citation:** Kitabchi AE, Umpierrez GE, Miles JM, Fisher JN. *Hyperglycemic crises in adult patients with diabetes.* (ADA Consensus). Diabetes Care. 2009;32(7):1335–1343. doi:10.2337/dc09-9032.

**Intent:** Identify and grade DKA severity.

**Signals:** plasma glucose (mg/dL); arterial pH; serum bicarbonate (mEq/L); anion gap (mEq/L)

**Logic (numeric):**
- DKA: glucose > 250 mg/dL **and** bicarbonate < 18 **and** anion gap > 10 (with arterial pH < 7.30)
- Severity by pH/bicarbonate: mild pH 7.25–7.30 / HCO₃ 15–18; moderate pH 7.00–7.24 / HCO₃ 10–14; severe pH < 7.00 / HCO₃ < 10

**NL prompt:**
> Build a PSDL scenario to detect diabetic ketoacidosis per the ADA criteria: plasma glucose above 250 mg/dL, arterial pH below 7.30, serum bicarbonate below 18 mEq/L, and an anion gap above 10. Stage severity as mild, moderate, or severe using pH (7.25–7.30, 7.00–7.24, below 7.00) and bicarbonate (15–18, 10–14, below 10).

---

## 5. Laboratory Tumor Lysis Syndrome (Cairo-Bishop)

**Citation:** Cairo MS, Bishop M. *Tumour lysis syndrome: new therapeutic strategies and classification.* Br J Haematol. 2004;127(1):3–11. doi:10.1111/j.1365-2141.2004.05094.x.

**Intent:** Detect laboratory TLS (≥ 2 metabolic abnormalities within 3 days before to 7 days after cytotoxic therapy).

**Signals:** uric acid (mg/dL); potassium (mEq/L); phosphate (mg/dL); calcium (mg/dL)

**Logic (numeric):**
- Abnormalities: uric acid ≥ 8; potassium ≥ 6.0; phosphate ≥ 4.5 (adult); calcium ≤ 7.0
- Laboratory TLS: ≥ 2 of the above present

**NL prompt:**
> Create a PSDL scenario for laboratory tumor lysis syndrome by the Cairo-Bishop classification. The metabolic abnormalities are: uric acid 8 mg/dL or higher; potassium 6.0 mEq/L or higher; phosphate 4.5 mg/dL or higher; and calcium 7.0 mg/dL or lower. Flag laboratory TLS when two or more abnormalities are present.

---

## 6. Drug-induced QT prolongation / Torsades risk

**Citation:** Drew BJ, Ackerman MJ, Funk M, et al. *Prevention of Torsade de Pointes in Hospital Settings.* (AHA/ACCF Scientific Statement). Circulation. 2010;121(8):1047–1060. doi:10.1161/CIRCULATIONAHA.109.192704.

**Intent:** Flag dangerous QTc prolongation.

**Signals:** corrected QT interval QTc (ms); serum potassium (mEq/L); serum magnesium (mg/dL)

**Logic (numeric):**
- High risk: QTc > 500 ms, **or** an increase in QTc ≥ 60 ms from baseline
- Modifier flag: hypokalemia (K < 3.5) or hypomagnesemia (Mg < 1.7) raising risk

**Time windows:** Δ QTc vs baseline.

**NL prompt:**
> Generate a PSDL scenario that flags drug-induced QT prolongation per the AHA/ACCF statement. High risk is a corrected QT interval above 500 ms, or an increase of 60 ms or more from baseline. Also raise concern when potassium is below 3.5 mEq/L or magnesium is below 1.7 mg/dL. Use a QTc trend versus baseline.

---

## 7. Chronic Kidney Disease — GFR staging (KDIGO)

**Citation:** KDIGO CKD Work Group. *KDIGO 2012 Clinical Practice Guideline for the Evaluation and Management of CKD.* Kidney Int Suppl. 2013;3(1):1–150.

**Intent:** Stage CKD by eGFR (G1–G5).

**Signals:** estimated GFR (mL/min/1.73 m²)

**Logic (numeric):**
- G1 ≥ 90; G2 60–89; G3a 45–59; G3b 30–44; G4 15–29; G5 < 15

**NL prompt:**
> Build a PSDL scenario that stages chronic kidney disease by eGFR using the KDIGO G categories: G1 is 90 or above, G2 is 60 to 89, G3a is 45 to 59, G3b is 30 to 44, G4 is 15 to 29, and G5 is below 15 mL/min/1.73m². Emit the stage as the output.

---

## 8. Neutropenic fever (IDSA)

**Citation:** Freifeld AG, Bow EJ, Sepkowitz KA, et al. *Clinical Practice Guideline for the Use of Antimicrobial Agents in Neutropenic Patients with Cancer: 2010 Update by the IDSA.* Clin Infect Dis. 2011;52(4):e56–e93. doi:10.1093/cid/cir073.

**Intent:** Detect febrile neutropenia.

**Signals:** absolute neutrophil count ANC (cells/µL); temperature (°C)

**Logic (numeric):**
- Febrile neutropenia: ANC < 500 (or < 1000 and expected to fall below 500) **and** single oral temperature ≥ 38.3 °C (or ≥ 38.0 °C sustained over 1 h)

**NL prompt:**
> Create a PSDL scenario for febrile neutropenia per the IDSA guideline: an absolute neutrophil count below 500 cells/µL together with a single oral temperature of 38.3°C or higher (or 38.0°C sustained for an hour). Flag the patient when both conditions are met.

---

## Results — OpenAI `gpt-4o-mini` (2026-06-04)

Raw outputs in [`outputs/openai/`](outputs/openai/). Scores are **provisional (AI-reviewed, pending clinician sign-off)**: Validity is automatic; Correctness/Completeness/Faithfulness are 1–5 vs the cited protocol.

| # | Scenario | Valid? | Correct | Complete | Faithful | Usability |
|---|----------|--------|---------|----------|----------|-----------|
| 1 | AKI staging (KDIGO) | ✅ | 5 | 4 | 5 | ship (minor) |
| 2 | qSOFA (Sepsis-3) | ✅ | 5 | 5 | 5 | **ship as-is** |
| 3 | SIRS (1992) | ✅ | 3 | 5 | 5 | edit logic |
| 4 | DKA (ADA) | ✅ | 5 | 5 | 5 | **ship as-is** |
| 5 | Lab TLS (Cairo-Bishop) | ✅ | 5 | 5 | 5 | **ship as-is** |
| 6 | Drug-induced QT (AHA) | ✅ | 5 | 4 | 5 | ship (minor) |
| 7 | CKD staging (KDIGO) | ✅ | 5 | 5 | 5 | **ship as-is** |
| 8 | Febrile neutropenia (IDSA) | ❌ | — | — | — | **fix required** |

**Summary:** 7/8 valid; 5 essentially ship-ready (qSOFA, DKA, TLS, CKD + AKI). gpt-4o-mini nailed exact thresholds and staging on the lab-driven scenarios.

**Notable findings:**
- **#8 (neutropenic fever) — invalid after 4 auto-correction attempts.** Error: `Logic 'neutropenia' references unknown term 'ANC'`. The model referenced the raw **signal** `ANC` in a `when:` expression instead of a derived **trend** (e.g. `anc_current`) — even though it got this right elsewhere (#1 used `cr_current`/`cr_delta_48h`). The retry loop couldn't recover. Clear, reproducible failure mode for the prompt/grammar.
- **#3 (SIRS) — clinically mis-modeled the "≥ 2 of 4" rule.** It encoded `(fever OR hypothermia) AND (tachycardia OR tachypnea OR leukocytosis OR leukopenia)` — i.e. temperature **AND** one other — which misses valid SIRS like tachycardia + tachypnea. Interestingly it *did* use the correct point-sum pattern (`(a + b + c) >= 2`) for qSOFA (#2) and TLS (#5), so this is an inconsistency, not a capability gap.
- **#6 (QT)** — treats hypokalemia/hypomagnesemia as standalone high-risk triggers (OR) rather than risk *modifiers*; minor.
- **Strengths:** exact KDIGO AKI staging, ADA DKA severity bands, Cairo-Bishop thresholds, and KDIGO CKD G-stages were all reproduced precisely with no hallucinated numbers.

> Next: OpenAI vs Ollama comparison (deferred — local run risks crashing the machine), and a clinician pass on Correctness/Completeness/Faithfulness.

---

## MIMIC live-preflight smoke test (2026-06-04)

For each scenario, its signals were mapped to the **real `measurement_concept_id`s present in the local MIMIC-IV→OMOP database**, a cohort extraction query was built (inpatient join + concept + date filter), and **preflighted live** against MIMIC (real Postgres `EXPLAIN` — metadata only, never executed).

| # | Scenario | Signals in MIMIC `measurement` | Verdict | Runtime | Conf | Live est. rows |
|---|----------|-------------------------------|---------|---------|------|----------------|
| 1 | AKI staging | 1/1 (creatinine) | 🟢 GO | FAST | HIGH | 13 |
| 2 | qSOFA | **0/3** (RR, SBP, GCS absent) | — | — | — | — |
| 3 | SIRS | 1/4 (WBC; temp/HR/RR absent) | 🟢 GO | FAST | HIGH | 13 |
| 4 | DKA | 1/4 (glucose; pH/HCO₃/anion-gap absent) | 🟢 GO | FAST | HIGH | 16 |
| 5 | Lab TLS | 3/4 (K, phosphate, calcium; urate absent) | 🟢 GO | FAST | HIGH | 32 |
| 6 | Drug QT | 1/3 (K; QTc/Mg absent) | 🟢 GO | FAST | HIGH | 13 |
| 7 | CKD staging | **0/1** (eGFR is derived, absent) | — | — | — | — |
| 8 | Febrile neutropenia | 1/2 (neutrophils/ANC; temp absent) | 🟢 GO | FAST | HIGH | 5 |

**Findings:**

- **Every scoped extraction is GO / FAST / HIGH-confidence.** Concept- and date-filtered cohort pulls are cheap against MIMIC, confirmed by a real query plan. (The naive *unfiltered* equivalents BLOCK at EXTREME — see the README walkthrough; preflight is what tells the two apart.)
- **The real story is data availability.** Only the **lab** signals exist in this MIMIC `measurement` table. The **vitals** (heart rate, respiratory rate, systolic BP, temperature, GCS) and **derived** values (eGFR, anion gap, pH, QTc, uric acid, magnesium) are **absent here**, so:
  - **#2 (qSOFA)** and **#7 (CKD)** have **0** signals available → they can't be run against this site's `measurement` table at all.
  - **#3 (SIRS), #4 (DKA), #6 (QT)** are only **partially** covered → an extraction would silently drop most signals.
- This is exactly the value of pairing the **Data Catalog** + **Preflight**: before running anything you see *which* of an AI-generated scenario's signals your institution actually has, and that the scoped extraction is cheap. (Note the anchoring step bound several signals to SNOMED-style concepts that don't match MIMIC's LOINC-coded labs — the portability gap the site `datasetSpec` resolves.)

**Confirmed (followed up):** the vitals aren't mislocated — they were **not loaded** into this OMOP instance. The ETL ingested *labevents → `measurement`* only; `observation` is essentially empty (4 rows) and HR/RR/BP/temp concepts have **0 rows**. The top `measurement` concepts are all labs (glucose, hematocrit, hemoglobin, creatinine, platelets, BUN, leukocytes). (Also: ~56.5M `measurement` rows are unmapped — `measurement_concept_id = 0` — LOINC mapping gaps.) Loading MIMIC's `chartevents` would add the vitals. This is exactly the kind of gap a **data catalog surfaces before anyone writes an extraction that can't run**.
