"use client";

import { useState } from "react";
import { Database, Loader2 } from "lucide-react";

type MedsAnchor = {
  psdl_signal: string;
  omop_vocabulary: string;
  omop_concept_code: string;
  expected_unit?: string | null;
};

type PreviewResult = {
  n_events: number;
  n_subjects: number;
  path: string;
  codes_used: string[];
};

type BundleAnchor = {
  concept_id: number | null;
  concept_code: string | null;
  vocabulary_id: string | null;
  concept_name: string | null;
  domain_id: string | null;
  standard_unit: string | null;
  match_confidence: "high" | "medium" | "low" | "unanchored";
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

/** Convert a TerminologyAnchors.anchors map into the MedsAnchor[] shape the
 *  preview endpoint expects. Only refs that resolved to a vocabulary +
 *  concept_code are included — unanchored refs would produce code strings
 *  the MEDS spec can't validate. */
function bundleAnchorsToMedsAnchors(
  anchorsMap: Record<string, BundleAnchor>,
): MedsAnchor[] {
  return Object.entries(anchorsMap)
    .filter(([, a]) => a.vocabulary_id && a.concept_code)
    .map(([ref, a]) => ({
      psdl_signal: ref,
      omop_vocabulary: a.vocabulary_id as string,
      omop_concept_code: a.concept_code as string,
      expected_unit: a.standard_unit ?? null,
    }));
}

interface MedsPreviewCardProps {
  /** Raw scenario YAML — the card runs the same anchoring path as
   *  `/api/export/draft` so it works for any parseable scenario, not just
   *  Builder-created ones with pre-populated concept_ids. */
  yaml: string;
  /** Number of signals on the page — used purely for the empty-state hint. */
  signalCount: number;
}

export default function MedsPreviewCard({
  yaml,
  signalCount,
}: MedsPreviewCardProps) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canPreview = yaml.trim().length > 0;

  async function handlePreview() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      // 1) Run anchoring via the draft-bundle path — tolerates validation
      //    warnings and gives us terminology_anchors regardless.
      const draftResp = await fetch(`${API_BASE}/api/export/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: yaml, format: "json" }),
      });
      if (!draftResp.ok) {
        const detail = await draftResp.text();
        throw new Error(`anchoring failed: ${draftResp.status} ${detail}`);
      }
      const draft = await draftResp.json();
      const anchorsMap: Record<string, BundleAnchor> =
        draft.terminology_anchors?.anchors ?? {};
      const anchors = bundleAnchorsToMedsAnchors(anchorsMap);

      if (anchors.length === 0) {
        const totalRefs = draft.terminology_anchors?.total_refs ?? 0;
        const unanchored = draft.terminology_anchors?.unanchored_refs ?? [];
        throw new Error(
          totalRefs === 0
            ? "no refs found in scenario — add signals with `ref:` fields"
            : `none of the ${totalRefs} ref${totalRefs !== 1 ? "s" : ""} could be anchored to OMOP vocabulary (${unanchored.slice(0, 3).join(", ")}${unanchored.length > 3 ? "…" : ""})`,
        );
      }

      // 2) Generate the MEDS preview from the anchored signals.
      const previewResp = await fetch(`${API_BASE}/api/meds/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anchors, n: 10 }),
      });
      if (!previewResp.ok) {
        const detail = await previewResp.text();
        throw new Error(`preview failed: ${previewResp.status} ${detail}`);
      }
      setResult(await previewResp.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-background-secondary rounded-xl p-5 border border-border space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-purple/15 flex items-center justify-center">
            <Database className="w-4 h-4 text-accent-purple" />
          </div>
          <h3 className="text-sm font-semibold text-foreground">Preview MEDS shape</h3>
        </div>
        <button
          type="button"
          onClick={handlePreview}
          disabled={!canPreview || busy}
          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
            canPreview && !busy
              ? "border-accent-purple/40 text-accent-purple hover:bg-accent-purple/10"
              : "border-border text-muted cursor-not-allowed opacity-50"
          }`}
        >
          {busy ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Anchoring…
            </>
          ) : (
            "Generate 10-row preview"
          )}
        </button>
      </div>

      {!canPreview && (
        <p className="text-xs text-muted">
          Load a scenario in the Input step to enable MEDS preview.
        </p>
      )}

      {canPreview && !result && !error && !busy && (
        <p className="text-xs text-muted">
          {signalCount > 0
            ? `${signalCount} signal${signalCount !== 1 ? "s" : ""} in scenario — clicking the button will anchor refs to OMOP and write a 10-row synthetic Parquet.`
            : "Anchors refs to OMOP and writes a 10-row synthetic MEDS Parquet so you can see the shape before any real data is exported."}
        </p>
      )}

      {result && (
        <div className="text-xs space-y-2">
          <div className="flex items-center gap-4 p-3 bg-accent-success/10 rounded-lg border border-accent-success/20 text-accent-success">
            <span>
              <span className="font-semibold">{result.n_events}</span> synthetic events across{" "}
              <span className="font-semibold">{result.n_subjects}</span> synthetic subjects
            </span>
          </div>
          <div className="font-mono text-[10px] text-muted break-all bg-background rounded px-2 py-1.5">
            {result.path}
          </div>
          <div className="flex flex-wrap gap-1 pt-0.5">
            {result.codes_used.map((c) => (
              <code
                key={c}
                className="px-1.5 py-0.5 rounded bg-accent-purple/10 text-accent-purple font-mono text-[10px]"
              >
                {c}
              </code>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="text-xs p-3 bg-accent-danger/10 rounded-lg border border-accent-danger/20 text-accent-danger">
          Error: {error}
        </div>
      )}
    </div>
  );
}
