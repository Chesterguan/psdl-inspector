# Sepsis Screening Demo — Narrator Cue Sheet

**Length target:** 6–8 minutes
**Audience:** Clinical informatics, CMIO, sepsis QI teams
**One-liner before recording:** "Watch a sepsis screening algorithm get validated, terminology-anchored, and previewed as MEDS-format event data — all in a single auditable pass."

---

## Beat 1 — Open on the loaded scenario (0:00–0:30)

**Frame:** Inspector at Step 1 Input → Raw YAML tab. The scenario YAML is visible in the editor (helper.js loaded it). Read these from the YAML header so the viewer's eye lands on the right place.

**Narration:**

> This is a Sepsis-3 screening scenario in PSDL — qSOFA criteria combined with lactate. Three things make it tricky: the population is gated to ED/ICU/Ward adults, the logic is an OR-of-AND with severity escalation, and the signals span vitals, labs, and a derived GCS observation. We're going to take it from declarative YAML to a certified, MEDS-previewable bundle — without touching any patient data.

**Action:** Scroll slowly through the YAML so viewers see `population`, `signals`, `trends`, `logic`, `outputs`.

**Wait:** 1 second after scrolling stops.

---

## Beat 2 — Validate (0:30–1:15)

**Frame:** YAML editor with the **"Validate Scenario"** button at the bottom.

**Narration:**

> Step one is structural validation through psdl-lang — the same library that ships on PyPI. This is checking grammar, ref consistency, severity-level enums, the works.

**Action:** Click **"Validate Scenario"**. Wait for the green "Valid" indicator to appear.

**Narration (after green light):**

> Clean parse. Zero errors. This is the gate that stops malformed scenarios from ever reaching downstream execution platforms.

**Wait:** 2 seconds.

---

## Beat 3 — Advance to Preview, hit the Outline tree (1:15–2:30)

**Frame:** Click **"Continue →"** or the **"2 Preview"** step.

**Narration:**

> Step two is the semantic preview. The left panel is the outline — it's a structural decomposition: signals at the top, trends derived from signals, logic rules referencing trends, and outputs at the bottom.

**Action:** Click into the outline tree, expand `logic` if it's collapsed. Hover or click `sepsis_screen_positive`.

**Narration:**

> Here's the punch line of the algorithm. The rule `sepsis_screen_positive` requires `qsofa_2` AND `lactate_elevated`. `qsofa_2` itself is `tachypnea AND (hypotension OR altered_mental_status)`. Inspector traces this dependency graph in real time — if I rename a signal upstream, every downstream rule lights up red until I fix it.

**Wait:** 3 seconds on the rule.

---

## Beat 4 — DAG visualization (2:30–4:00)

**Frame:** Switch to the **DAG** tab if it's separate, or scroll to the DAG panel.

**Narration:**

> The DAG view is the same algorithm rendered as a directed acyclic graph — signals on the left, trends in the middle, logic rules on the right, outputs at the far right. Severity is color-coded: green is low, orange is medium, red is high, dark red is critical.

**Action:** Slowly pan/zoom to show the qSOFA → sepsis_screen_positive → septic_shock cascade.

**Narration:**

> What I want you to notice is `septic_shock` over here. It's `sepsis_screen_positive AND hypotension AND lactate_high`. Inspector lets you visually audit that the algorithm composes the way the paper describes — Singer et al., JAMA 2016. No hidden short-circuits.

**Wait:** 3 seconds.

---

## Beat 5 — Anchor terminology (4:00–5:00)

**Frame:** Find the **Anchor** / terminology binding panel (sidebar or button on the Preview step).

**Narration:**

> Step three before export: terminology anchoring. PSDL signals are abstract references — `respiratory_rate`, `lactate`, `glasgow_coma_scale`. Anchoring binds each one to an OMOP concept ID at high confidence, or marks it for human review at lower confidence. This is the contract between authoring and any institution that wants to execute this scenario.

**Action:** Trigger anchoring (button click or automatic). Show the results panel: anchored signals get a green check, vocabulary chip (LOINC, SNOMED), and confidence level.

**Narration:**

> Each anchor records the vocabulary, the concept code, the concept name, and the confidence band. This metadata travels with the bundle.

**Wait:** 3 seconds.

---

## Beat 6 — Advance to Export, look at the bundle (5:00–6:00)

**Frame:** Click **"3 Export"**. The right-side panel shows the certified bundle preview.

**Narration:**

> Step three is the certified audit bundle — checksummed, versioned, and self-contained. It carries the raw YAML, the parsed IR, the terminology anchors with confidence levels, validation result, audit block, and an IRB-ready summary. This bundle is what an execution platform consumes — nothing else needs to be shipped.

**Action:** Scroll through the bundle JSON preview so the viewer sees `terminology_anchors`, `validation`, `audit`.

**Wait:** 2 seconds.

---

## Beat 7 — MEDS Preview card (6:00–7:30)

**Frame:** Right column of the Export step. Find the **"Preview MEDS shape"** card.

**Narration:**

> And this is what's new. Before any real data is touched, Inspector can synthesize a ten-row preview in MEDS format — the Medical Event Data Standard — using the concept IDs we just anchored. It's the same Parquet schema MIMIC-IV-MEDS and ETHOS use. Your ML team sees the column shape and the code strings they'll receive *before* the institution writes a single line of ETL.

**Action:** Click **"Generate 10-row preview"**. Wait for the card to populate.

**Narration (after card shows results):**

> Ten synthetic events, three synthetic subjects — subject IDs are deliberately negative integers so they can never be confused with real OMOP person IDs. The code strings show the bound vocabulary and concept code: LOINC over here, SNOMED for the diagnosis-side signals. And the parquet was validated against the official `meds.schema.data_schema` before it was written.

**Wait:** 3 seconds on the code chips.

---

## Beat 8 — Closing (7:30–8:00)

**Frame:** Wide shot showing the whole Export step with bundle + MEDS card both visible.

**Narration:**

> One scenario, one auditable pipeline, two handoffs: a certified bundle for execution platforms, and a MEDS preview for ML teams. No PHI was read. The whole thing ran on metadata.

**Action:** Hold the frame. Cut.

---

## After recording (off-camera)

Open the console one more time and run:

```js
window.__saveBundle();
window.__saveMeds();
```

Drop the two downloaded files into `docs/demos/sepsis-screening/artifacts/` and rename:

- `sepsis-bundle.json`
- `sepsis-meds-preview.json`

Drop any screenshots you grabbed (Cmd+Shift+4) into `docs/demos/sepsis-screening/screenshots/` named to match the beat number (`01-input.png`, `02-validate.png`, …).

---

## Quick reference

| Beat | Click | Watch for |
|------|-------|-----------|
| 2 | Validate Scenario | Green "Valid" indicator |
| 3 | Continue → / Step 2 | Outline tree populated |
| 4 | DAG tab (if separate) | Severity-colored nodes |
| 5 | Anchor button | Concept IDs + confidence |
| 6 | Step 3 Export | Bundle JSON preview |
| 7 | Generate 10-row preview | Code chips appear |
