/* PSDL Inspector — Sepsis Screening Demo Loader
 * ─────────────────────────────────────────────────
 * Paste this whole file into the Inspector DevTools console (Cmd+Opt+I → Console),
 * then press Enter. It will:
 *   1. Skip the Welcome wizard if it's open
 *   2. Dismiss the announcement banner
 *   3. Click the "Raw YAML" tab
 *   4. Fetch scenario.yaml from frontend/public/demos/sepsis.yaml
 *   5. Inject it into the editor with proper React state updates
 * After it logs "OK — N chars loaded", close DevTools and start recording.
 */

(async () => {
  const YAML_URL = "/demos/sepsis.yaml";

  // 1) Skip welcome modal if present
  const modal = document.querySelector(".fixed.inset-0");
  if (modal) {
    const skipBtn = Array.from(modal.querySelectorAll("button"))
      .find((b) => b.innerText.trim() === "Skip");
    if (skipBtn) {
      skipBtn.click();
      console.log("[demo] welcome modal skipped");
      await new Promise((r) => setTimeout(r, 200));
    }
  }

  // 2) Dismiss announcement banner
  document
    .querySelectorAll('[aria-label="Dismiss"]')
    .forEach((b) => b.click());

  // 3) Click the "Raw YAML" tab so the textarea is present
  const yamlTab = Array.from(document.querySelectorAll("button"))
    .find((b) => b.innerText.trim() === "Raw YAML");
  if (yamlTab) {
    yamlTab.click();
    await new Promise((r) => setTimeout(r, 300));
    console.log("[demo] Raw YAML tab activated");
  } else {
    console.warn("[demo] could not find Raw YAML tab — make sure you're on step 1 Input");
  }

  // 4) Fetch the scenario
  let yaml;
  try {
    const resp = await fetch(YAML_URL);
    if (!resp.ok) throw new Error("status " + resp.status);
    yaml = await resp.text();
  } catch (e) {
    console.error(
      `[demo] could not fetch ${YAML_URL}. Make sure the file exists at frontend/public/demos/sepsis.yaml. Error: ${e.message}`
    );
    return;
  }

  // 5) Inject into the React-controlled textarea
  const ta = document.querySelector("textarea.yaml-editor, textarea");
  if (!ta) {
    console.error("[demo] no textarea found on the page — are you on the Input step?");
    return;
  }
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype,
    "value"
  ).set;
  setter.call(ta, yaml);
  ta.dispatchEvent(new Event("input", { bubbles: true }));
  ta.dispatchEvent(new Event("change", { bubbles: true }));

  console.log(`[demo] OK — ${ta.value.length} chars loaded into the editor`);
  console.log(
    "[demo] You're ready to record. Click 'Validate Scenario', then walk through the wizard."
  );

  // Expose helpers for post-recording artifact capture
  window.__saveBundle = async () => {
    const resp = await fetch("http://localhost:8200/api/export/bundle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: ta.value }),
    });
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sepsis-bundle.json";
    a.click();
    URL.revokeObjectURL(url);
    console.log("[demo] bundle download triggered");
  };

  window.__saveMeds = async () => {
    // Re-run the preview to capture the most recent path
    const anchorsResp = await fetch("http://localhost:8200/api/outline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: ta.value }),
    });
    const outline = await anchorsResp.json();
    const signals = (outline.signals || []).filter((s) => s.concept_id);
    const anchors = signals.map((s) => ({
      psdl_signal: s.name,
      omop_vocabulary: "OMOP",
      omop_concept_code: String(s.concept_id),
      expected_unit: s.unit || null,
    }));
    if (!anchors.length) {
      console.warn(
        "[demo] no anchored signals found — run anchoring (Preview step) before saving the MEDS shard"
      );
      return;
    }
    const resp = await fetch("http://localhost:8200/api/meds/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anchors, n: 10 }),
    });
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sepsis-meds-preview.json";
    a.click();
    URL.revokeObjectURL(url);
    console.log("[demo] MEDS preview metadata downloaded:", data);
  };
})();
