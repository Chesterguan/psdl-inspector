import type { Provenance } from './types';

export default function ProvenanceBar({ provenance, stale }: { provenance?: Provenance | null; stale?: boolean }) {
  if (!provenance) return null;
  const date = provenance.scanned_at ? new Date(provenance.scanned_at).toLocaleDateString() : 'unknown';
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
      <span>Last scanned <span className="text-foreground font-medium">{date}</span></span>
      <span>· {provenance.file_count ?? '?'} files</span>
      <span>· {provenance.schema_count ?? '?'} schemas</span>
      {provenance.scan_error_count ? (
        <span className="text-accent-warning">· {provenance.scan_error_count} unreadable</span>
      ) : null}
      {stale && (
        <span className="px-2 py-0.5 rounded bg-accent-warning/15 text-accent-warning text-xs font-medium">
          ⚠ catalog may be stale
        </span>
      )}
    </div>
  );
}
