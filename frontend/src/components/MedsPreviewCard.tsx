"use client";

import { useState } from "react";
import { Database, Loader2 } from "lucide-react";
import type { SignalOutline } from "@/lib/api";

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

/** Derive MEDS anchors from outline signals that have OMOP concept_ids. */
function toMedsAnchors(signals: SignalOutline[]): MedsAnchor[] {
  return signals
    .filter((s) => s.concept_id != null)
    .map((s) => ({
      psdl_signal: s.name,
      omop_vocabulary: "OMOP",
      omop_concept_code: String(s.concept_id),
      expected_unit: s.unit ?? null,
    }));
}

interface MedsPreviewCardProps {
  signals: SignalOutline[];
}

export default function MedsPreviewCard({ signals }: MedsPreviewCardProps) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const anchors = toMedsAnchors(signals);
  const canPreview = anchors.length > 0;

  async function handlePreview() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch(`${API_BASE}/api/meds/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anchors, n: 10 }),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(`${resp.status} ${detail}`);
      }
      setResult(await resp.json());
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
              Generating…
            </>
          ) : (
            "Generate 10-row preview"
          )}
        </button>
      </div>

      {!canPreview && (
        <p className="text-xs text-muted">
          Signals need OMOP concept IDs to enable MEDS preview.{" "}
          {signals.length > 0
            ? `${signals.length} signal${signals.length !== 1 ? "s" : ""} found, none with concept_id.`
            : "No signals found."}
        </p>
      )}

      {canPreview && !result && !error && !busy && (
        <p className="text-xs text-muted">
          {anchors.length} anchored signal{anchors.length !== 1 ? "s" : ""} ready —{" "}
          {anchors.map((a) => a.psdl_signal).join(", ")}.
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
