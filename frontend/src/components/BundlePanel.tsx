"use client";

import React from "react";
import { CertifiedBundle } from "@/lib/api";

interface BundlePanelProps {
  bundle: CertifiedBundle | null;
  loading?: boolean;
}

export function BundlePanel({ bundle, loading }: BundlePanelProps) {
  if (loading) {
    return (
      <div className="p-4 text-gray-400">
        Loading bundle information...
      </div>
    );
  }

  if (!bundle) {
    return (
      <div className="p-4 text-gray-400">
        Validate a scenario to see audit information
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-4 space-y-6">
      {/* Certification Status */}
      <section>
        <h3 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Certified Bundle
        </h3>
        <div className={`rounded-lg p-4 space-y-2 border ${
          bundle.validation.valid
            ? "bg-green-900/30 border-green-700"
            : "bg-red-900/30 border-red-700"
        }`}>
          <div className="flex justify-between items-center">
            <span className="text-gray-300">Status:</span>
            <span className={`font-semibold ${
              bundle.validation.valid ? "text-green-400" : "text-red-400"
            }`}>
              {bundle.validation.valid ? "CERTIFIED" : "INVALID"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Bundle Version:</span>
            <span className="font-mono text-sm text-gray-200">{bundle.bundle_version}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Certified At:</span>
            <span className="font-mono text-sm text-gray-200">
              {new Date(bundle.certified_at).toLocaleString()}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-gray-400">Checksum:</span>
            <span className="font-mono text-xs text-green-400 break-all bg-gray-900 p-2 rounded">
              {bundle.checksum}
            </span>
          </div>
        </div>
      </section>

      {/* Validation Results */}
      <section>
        <h3 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Validation Results
        </h3>
        <div className="bg-gray-800 rounded-lg p-4 space-y-2 border border-gray-700">
          <div className="flex justify-between">
            <span className="text-gray-400">psdl-lang Version:</span>
            <span className="font-mono text-sm text-blue-400">
              {bundle.validation.psdl_lang_version}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Inspector Version:</span>
            <span className="font-mono text-sm text-blue-400">
              {bundle.validation.inspector_version}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Errors:</span>
            <span className={`font-mono text-sm ${
              bundle.validation.errors.length === 0 ? "text-green-400" : "text-red-400"
            }`}>
              {bundle.validation.errors.length}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Warnings:</span>
            <span className={`font-mono text-sm ${
              bundle.validation.warnings.length === 0 ? "text-green-400" : "text-yellow-400"
            }`}>
              {bundle.validation.warnings.length}
            </span>
          </div>
        </div>
      </section>

      {/* Scenario Info */}
      <section>
        <h3 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Scenario
        </h3>
        <div className="bg-gray-800 rounded-lg p-4 space-y-2 border border-gray-700">
          <div className="flex justify-between">
            <span className="text-gray-400">Name:</span>
            <span className="font-semibold text-gray-200">{bundle.scenario.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Version:</span>
            <span className="font-mono text-sm text-gray-200">
              {bundle.scenario.version || "N/A"}
            </span>
          </div>
        </div>
      </section>

      {/* Audit Block Section */}
      <section>
        <h3 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Audit Trail
        </h3>
        <div className="bg-blue-900/30 rounded-lg p-4 space-y-4 border border-blue-800">
          {bundle.audit.intent || bundle.audit.rationale || bundle.audit.provenance ? (
            <>
              {bundle.audit.intent && (
                <div>
                  <div className="font-semibold text-blue-300">Intent</div>
                  <div className="text-blue-200">{bundle.audit.intent}</div>
                </div>
              )}
              {bundle.audit.rationale && (
                <div>
                  <div className="font-semibold text-blue-300">Rationale</div>
                  <div className="text-blue-200">{bundle.audit.rationale}</div>
                </div>
              )}
              {bundle.audit.provenance && (
                <div>
                  <div className="font-semibold text-blue-300">Provenance</div>
                  <div className="text-blue-200">{bundle.audit.provenance}</div>
                </div>
              )}
            </>
          ) : (
            <div className="text-blue-300 italic">
              No audit information provided.
              <br />
              <span className="text-sm text-blue-400">
                Add <code className="bg-blue-800 px-1 rounded text-blue-200">intent</code>,{" "}
                <code className="bg-blue-800 px-1 rounded text-blue-200">rationale</code>, and{" "}
                <code className="bg-blue-800 px-1 rounded text-blue-200">provenance</code> when exporting
                for governance compliance.
              </span>
            </div>
          )}
        </div>
      </section>

      {/* Governance Checklist */}
      <section>
        <h3 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          Governance Checklist
        </h3>
        <div className="bg-gray-800 rounded-lg p-4 space-y-2 border border-gray-700">
          <ChecklistItem
            checked={bundle.validation.valid}
            label="Scenario validated successfully"
          />
          <ChecklistItem
            checked={true}
            label="SHA-256 checksum generated"
          />
          <ChecklistItem
            checked={!!bundle.audit.intent}
            label="Intent documented"
          />
          <ChecklistItem
            checked={!!bundle.audit.rationale}
            label="Rationale documented"
          />
          <ChecklistItem
            checked={!!bundle.audit.provenance}
            label="Provenance tracked"
          />
          <ChecklistItem
            checked={bundle.validation.warnings.length === 0}
            label="No warnings"
          />
        </div>
      </section>

      {/* Summary Preview */}
      <section>
        <h3 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h7" />
          </svg>
          Human-Readable Summary
        </h3>
        <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-sm overflow-x-auto whitespace-pre-wrap border border-gray-700">
          {bundle.summary}
        </pre>
      </section>
    </div>
  );
}

function ChecklistItem({
  checked,
  label,
  disabled
}: {
  checked: boolean;
  label: string;
  disabled?: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 ${disabled ? "opacity-50" : ""}`}>
      {checked ? (
        <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      <span className={checked ? "text-gray-100" : "text-gray-400"}>{label}</span>
    </div>
  );
}
