import type { ColumnInfo } from './types';

export default function ColumnTable({ columns }: { columns: ColumnInfo[] }) {
  if (columns.length === 0) return <div className="text-muted text-sm italic py-4">No columns match.</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-muted border-b border-border">
        <tr>
          <th className="py-2 pr-4">Column</th>
          <th className="py-2 pr-4">Role</th>
          <th className="py-2 pr-4">Files</th>
          <th className="py-2 pr-4">Schemas</th>
          <th className="py-2 pr-4">Example path</th>
        </tr>
      </thead>
      <tbody>
        {columns.map((c) => (
          <tr key={c.normalized} className="border-b border-border/50">
            <td className="py-2 pr-4 font-mono text-foreground">{c.normalized}</td>
            <td className="py-2 pr-4">
              <span className="px-1.5 py-0.5 rounded bg-accent-purple/10 text-accent-purple text-xs">{c.role}</span>
            </td>
            <td className="py-2 pr-4">{c.file_count.toLocaleString()}</td>
            <td className="py-2 pr-4">{c.schema_count.toLocaleString()}</td>
            <td className="py-2 pr-4 font-mono text-xs text-muted truncate max-w-[260px]" title={c.example_path}>{c.example_path}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
