'use client';

import { useEffect, useState } from 'react';

import SqlInput from './SqlInput';
import VerdictBanner from './VerdictBanner';
import ScaleCard from './ScaleCard';
import LineageList from './LineageList';
import FindingsLists from './FindingsLists';
import { CatalogsResponse, PreflightReport } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

interface Props {
  /** Optional SQL to prefill the editor with (e.g. a starter extraction query). */
  initialSql?: string;
}

/** Offline SQL preflight panel. No page chrome — embeddable in a route page or a
 *  wizard step. */
export default function PreflightView({ initialSql = '' }: Props) {
  const [catalogs, setCatalogs] = useState<CatalogsResponse | null>(null);
  const [catalogsError, setCatalogsError] = useState<string | null>(null);
  const [sql, setSql] = useState(initialSql);
  const [dialect, setDialect] = useState('generic');
  const [catalogSource, setCatalogSource] = useState('omop');
  const [report, setReport] = useState<PreflightReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/preflight/catalogs`)
      .then((r) => r.json())
      .then((c: CatalogsResponse) => {
        setCatalogs(c);
        setCatalogSource(c.default);
        setCatalogsError(null);
      })
      .catch(() => {
        setCatalogs(null);
        setCatalogsError("Couldn't load catalogs — is the backend running?");
      });
  }, []);

  const run = async () => {
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const resp = await fetch(`${API_BASE}/api/preflight/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql, dialect, catalog_source: catalogSource }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.detail || 'Preflight failed.');
      } else {
        setReport(data as PreflightReport);
      }
    } catch {
      setError("Couldn't reach the backend.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      {catalogsError && (
        <div className="border border-accent-warning rounded-md p-3 text-accent-warning text-sm">
          {catalogsError}
        </div>
      )}

      {catalogs && !catalogs.preflight_available && (
        <div className="border border-accent-warning rounded-md p-3 text-accent-warning text-sm">
          Preflight core is not installed on the server — checks are unavailable until it is published/installed.
        </div>
      )}

      <SqlInput
        sql={sql}
        dialect={dialect}
        catalogSource={catalogSource}
        catalogs={catalogs}
        running={running}
        onSqlChange={setSql}
        onDialectChange={setDialect}
        onCatalogChange={setCatalogSource}
        onRun={run}
      />

      {error && (
        <div className="border border-accent-warning rounded-md p-3 text-accent-warning text-sm">
          {error}
        </div>
      )}

      {report && (
        <>
          <VerdictBanner
            riskLevel={report.risk_level}
            confidence={report.confidence}
            runtimeCategory={report.runtime_category}
          />
          <ScaleCard scale={report.scale} />
          <LineageList lineage={report.lineage} />
          <FindingsLists
            summary={report.summary}
            riskReasons={report.risk_reasons}
            bottlenecks={report.bottlenecks}
            optimizations={report.optimizations}
            notes={report.notes}
          />
        </>
      )}
    </div>
  );
}
