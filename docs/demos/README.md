# PSDL Inspector — End-to-End Demo Recording Kit

Two recorded walkthroughs are kept here so anyone can reproduce the canonical
PSDL Inspector flow — including the new MEDS Preview surface — without
guessing at scenario design or recording cadence.

## Reference recording

▶ **[Watch on YouTube](https://youtu.be/j-3UHeCyHDk)** — the published walkthrough that follows the two cue sheets below. Embed:

[![PSDL Inspector — sepsis + T2D cohort walkthrough](https://img.youtube.com/vi/j-3UHeCyHDk/hqdefault.jpg)](https://youtu.be/j-3UHeCyHDk)

> This kit is the recipe; the YouTube video is the canonical bake of it. Anyone re-recording (e.g., for a translated narration or a new spec version) should follow the same beats so the result stays comparable.

## Scenarios

| # | Scenario | Audience | Why it's interesting |
|---|----------|----------|---------------------|
| 1 | [`sepsis-screening/`](sepsis-screening/) | Clinical | qSOFA + lactate with OR-of-AND logic; tests multi-domain anchoring (vitals + labs); MEDS preview shows LOINC + flag codes |
| 2 | [`t2d-nephropathy-cohort/`](t2d-nephropathy-cohort/) | Research / cohort builders | T2DM + diabetic nephropathy + active metformin, 2020–2023; CKD-stage stratification logic; the "ML handoff" demo for cohort export |

Each scenario directory contains:

```
<scenario>/
├── scenario.yaml              # The PSDL definition (validated, ready to load)
├── helper.js                  # Paste into DevTools console — loads YAML + dismisses modals
├── narrator-cue-sheet.md      # Numbered beats with what to say + what to click
├── screenshots/               # Empty until you record (PNG/JPG drop point)
└── artifacts/                 # Saved bundles / MEDS parquet outputs from the run
```

## How to record a demo (per scenario)

### 1. Pre-flight

```bash
# Start the Inspector backend + frontend
cd backend && source .venv/bin/activate
uvicorn app.main:app --port 8200 &

cd ../frontend
npm run dev    # serves on port 9806
```

Confirm http://localhost:9806 loads. Confirm `curl -s http://localhost:8200/api/version` reports `psdl_lang: 0.4.0` (or newer).

### 2. Set up the screen

- Browser window at **1440 × 900** (matches the screenshot aspect the README uses).
- Light theme — easier to read in captures. Toggle from the header if it's dark.
- DevTools **closed** during the recorded portion. You'll only use them for the one-time YAML inject.
- Start your screen recorder (QuickTime "New Screen Recording", Kap, Loom, etc.) framing just the browser viewport, not the whole desktop.

### 3. Inject the scenario (off-camera, before you start the recording proper)

1. Open DevTools (Cmd+Opt+I).
2. Open the **Console** tab.
3. Open `<scenario>/helper.js` in any text editor, copy the whole thing.
4. Paste into the console, press Enter.
5. The script will:
   - Skip the Welcome wizard if present
   - Dismiss the announcement banner
   - Switch to the **Raw YAML** tab
   - Fetch the scenario YAML from disk (via the local file under `public/demos/`)
   - Inject it into the editor with proper React state updates
   - Confirm in the console with `OK — N chars loaded`
6. Close DevTools.

You're now staged exactly where the recording should start.

### 4. Record using the cue sheet

Open `<scenario>/narrator-cue-sheet.md` on a second monitor (or in a small window outside the recording frame). Each beat is numbered and gives you:

- **Action:** the click / scroll to perform
- **Narration:** the sentence to read aloud
- **Wait:** any second-counted pause before the next beat

Suggested cadence: **6–8 minutes total per scenario.**

### 5. Save artifacts

After the wizard ends with a successful export, the helper-script also exposes two functions you can call from the console **after recording stops**:

```js
window.__saveBundle()   // downloads the certified bundle JSON
window.__saveMeds()     // downloads the MEDS preview parquet path info as JSON
```

Move the downloaded files into the scenario's `artifacts/` directory.

### 6. Drop screenshots

If you grabbed stills with Cmd+Shift+4 during the recording, drop the PNGs in
`<scenario>/screenshots/` named `01-input.png`, `02-validate.png`, etc. to
match the cue-sheet beat numbers.

## What the helper.js scripts assume

- Backend at `http://localhost:8200`, frontend at `http://localhost:9806`.
- The scenario YAML is reachable at `http://localhost:9806/demos/<slug>.yaml`
  (this works because the YAMLs are placed in `frontend/public/demos/` so
  Next.js serves them statically). Both demo YAMLs are pre-copied there.
- Inspector version 0.2.x with the MEDS Preview card on the Export step.

If those don't match your machine, edit the constants at the top of `helper.js`.

## Notes for video editors / publishers

- Both scenarios end on the **MEDS Preview card** showing `n_events / n_subjects / path / codes_used`. That's the natural closing shot.
- The Sepsis demo's "wow moment" is the **DAG visualization** in the Preview step — pause there.
- The T2D cohort demo's "wow moment" is the **CKD-stage stratification logic** in the outline tree — zoom in on the severity-colored rules.

---

*Why we ship these even though they're not auto-generated:* PSDL Inspector
is governance middleware. People want to see a scenario go *all the way
through* — author → validate → anchor → bundle → MEDS preview → export —
before they trust the certification. These two demos give that proof.
