'use client';

import { useEffect, useMemo, useState } from 'react';
import ProvenanceBar from './ProvenanceBar';
import SchemaTable from './SchemaTable';
import ColumnTable from './ColumnTable';
import type { Catalog, CatalogStatus } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

/** Read-only Observatory data-catalog browser. No page chrome — embeddable in a
 *  route page or a wizard step. */
export default function CatalogView() {
  const [status, setStatus] = useState<CatalogStatus | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [tab, setTab] = useState<'schemas' | 'columns'>('schemas');
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  useEffect(() => {
    Promise.allSettled([
      fetch(`${API_BASE}/api/observatory/status`).then((r) => r.json()).then(setStatus),
      fetch(`${API_BASE}/api/observatory/catalog`).then((r) => r.json()).then(setCatalog),
    ]).finally(() => setLoaded(true));
  }, []);

  const columns = catalog?.columns ?? [];
  const schemas = catalog?.schemas ?? [];
  const roles = useMemo(() => Array.from(new Set(columns.map((c) => c.role))).sort(), [columns]);

  const filteredColumns = useMemo(() => columns.filter(
    (c) => (!query || c.normalized.toLowerCase().includes(query.toLowerCase())) && (!roleFilter || c.role === roleFilter),
  ), [columns, query, roleFilter]);

  const filteredSchemas = useMemo(() => {
    const q = query.toLowerCase();
    return schemas.filter(
      (s) => !q || s.table_kind.toLowerCase().includes(q) || s.columns.some((c) => c.toLowerCase().includes(q)),
    );
  }, [schemas, query]);

  return (
    <div>
      {!loaded && <div className="text-muted text-sm py-8">Loading…</div>}
      {loaded && status === null && (
        <div className="text-accent-warning text-sm py-8">Couldn&apos;t reach the backend.</div>
      )}

      {status && !status.configured && (
        <div className="text-muted text-sm py-8">Data catalog not set up — ask your data team to publish one.</div>
      )}
      {status && status.configured && !status.available && (
        <div className="text-muted text-sm py-8">{status.reason || 'No catalog published yet.'}</div>
      )}

      {status?.available && (
        <>
          <ProvenanceBar provenance={status.provenance} stale={status.stale} />

          <div className="flex flex-wrap items-center gap-3 mt-6 mb-3">
            <div className="flex gap-1">
              <button onClick={() => setTab('schemas')} className={`px-3 py-1.5 rounded text-sm ${tab === 'schemas' ? 'bg-accent text-white' : 'bg-background-tertiary text-muted'}`}>Schemas</button>
              <button onClick={() => setTab('columns')} className={`px-3 py-1.5 rounded text-sm ${tab === 'columns' ? 'bg-accent text-white' : 'bg-background-tertiary text-muted'}`}>Columns</button>
            </div>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search…" className="px-3 py-1.5 rounded bg-background-tertiary text-sm text-foreground border border-border" />
            {tab === 'columns' && (
              <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="px-3 py-1.5 rounded bg-background-tertiary text-sm text-foreground border border-border">
                <option value="">all roles</option>
                {roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            )}
          </div>

          <div className="overflow-x-auto">
            {tab === 'schemas' ? <SchemaTable schemas={filteredSchemas} /> : <ColumnTable columns={filteredColumns} />}
          </div>
        </>
      )}
    </div>
  );
}
