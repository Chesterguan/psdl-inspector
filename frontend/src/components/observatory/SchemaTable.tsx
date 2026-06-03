import type { SchemaProfile } from './types';

export default function SchemaTable({ schemas }: { schemas: SchemaProfile[] }) {
  if (schemas.length === 0) return <div className="text-muted text-sm italic py-4">No schemas.</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-muted border-b border-border">
        <tr>
          <th className="py-2 pr-4">Table kind</th>
          <th className="py-2 pr-4">Files</th>
          <th className="py-2 pr-4">Rows</th>
          <th className="py-2 pr-4">Columns</th>
          <th className="py-2 pr-4">Roles present</th>
        </tr>
      </thead>
      <tbody>
        {schemas.map((s) => (
          <tr key={s.schema_signature} className="border-b border-border/50">
            <td className="py-2 pr-4 font-medium text-foreground">{s.table_kind.replace(/_/g, ' ')}</td>
            <td className="py-2 pr-4">{s.num_files.toLocaleString()}</td>
            <td className="py-2 pr-4">{s.num_rows.toLocaleString()}</td>
            <td className="py-2 pr-4">{s.columns.length}</td>
            <td className="py-2 pr-4">
              <div className="flex flex-wrap gap-1">
                {s.roles_present.map((r) => (
                  <span key={r} className="px-1.5 py-0.5 rounded bg-accent-cyan/10 text-accent-cyan text-xs">{r}</span>
                ))}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
