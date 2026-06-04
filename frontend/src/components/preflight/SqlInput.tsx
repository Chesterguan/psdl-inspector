import { CatalogsResponse } from './types';

const DIALECTS = ['generic', 'duckdb', 'postgres', 'tsql'];

interface Props {
  sql: string;
  dialect: string;
  catalogSource: string;
  catalogs: CatalogsResponse | null;
  running: boolean;
  onSqlChange: (v: string) => void;
  onDialectChange: (v: string) => void;
  onCatalogChange: (v: string) => void;
  onRun: () => void;
}

export default function SqlInput({
  sql,
  dialect,
  catalogSource,
  catalogs,
  running,
  onSqlChange,
  onDialectChange,
  onCatalogChange,
  onRun,
}: Props) {
  const bundled = catalogs?.bundled ?? [];
  return (
    <div className="border border-border rounded-md p-4 bg-background-tertiary">
      <textarea
        className="w-full h-40 font-mono text-sm p-2 bg-background text-foreground border border-border rounded"
        placeholder="SELECT person_id FROM person"
        value={sql}
        onChange={(e) => onSqlChange(e.target.value)}
      />
      <div className="flex items-center gap-3 mt-3">
        <label className="text-sm text-muted">
          Dialect
          <select
            className="ml-2 bg-background text-foreground border border-border rounded px-2 py-1"
            value={dialect}
            onChange={(e) => onDialectChange(e.target.value)}
          >
            {DIALECTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-muted">
          Catalog
          <select
            className="ml-2 bg-background text-foreground border border-border rounded px-2 py-1"
            value={catalogSource}
            onChange={(e) => onCatalogChange(e.target.value)}
          >
            {bundled.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button
          className="ml-auto bg-accent text-foreground px-4 py-1.5 rounded disabled:opacity-50"
          disabled={running || !sql.trim()}
          onClick={onRun}
        >
          {running ? 'Running…' : 'Run preflight'}
        </button>
      </div>
    </div>
  );
}
