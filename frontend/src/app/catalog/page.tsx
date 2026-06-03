'use client';

import { useEffect, useMemo, useState } from 'react';
import ProvenanceBar from '@/components/observatory/ProvenanceBar';
import SchemaTable from '@/components/observatory/SchemaTable';
import ColumnTable from '@/components/observatory/ColumnTable';
import type { Catalog, CatalogStatus } from '@/components/observatory/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

export default function CatalogPage() {
  const [status, setStatus] = useState<CatalogStatus | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [tab, setTab] = useState<'schemas' | 'columns'>('schemas');
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/observatory/status`).then((r) => r.json()).then(setStatus).catch(() => setStatus(null));
    fetch(`${API_BASE}/api/observatory/catalog`).then((r) => r.json()).then(setCatalog).catch(() => setCatalog(null));
  }, []);

  const columns = catalog?.columns ?? [];
  const schemas = catalog?.schemas ?? [];
  const roles = useMemo(() => Array.from(new Set(columns.map((c) => c.role))).sort(), [columns]);

  const filteredColumns = useMemo(() => columns.filter(
    (c) => (!query || c.normalized.toLowerCase().includes(query.toLowerCase())) && (!roleFilter || c.role === roleFilter),
  ), [columns, query, roleFilter]);

  const filteredSchemas = useMemo(() => schemas.filter(
    (s) => !query || s.table_kind.includes(query.toLowerCase()) || s.columns.some((c) => c.includes(query.toLowerCase())),
  ), [schemas, query]);

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-foreground">Institutional Data Catalog</h1>
        <a href="/" className="text-sm text-accent hover:underline">← Back to Inspector</a>
      </div>

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
    </main>
  );
}
