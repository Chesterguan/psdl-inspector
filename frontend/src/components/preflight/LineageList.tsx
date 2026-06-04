import { Lineage } from './types';

interface Props {
  lineage: Lineage;
}

export default function LineageList({ lineage }: Props) {
  return (
    <div className="border border-border rounded-md p-4">
      <h3 className="font-semibold text-foreground mb-2">Lineage</h3>
      <h4 className="text-muted text-sm">Nodes</h4>
      {lineage.nodes.length === 0 ? (
        <p className="text-muted text-sm">none</p>
      ) : (
        <ul className="text-sm mb-2">
          {lineage.nodes.map((n, i) => (
            <li key={i} className="text-foreground">
              {n.table} · {n.category} · {n.volume}
              {n.est_rows !== null ? ` · ~${n.est_rows} rows` : ''}
            </li>
          ))}
        </ul>
      )}
      <h4 className="text-muted text-sm">Edges</h4>
      {lineage.edges.length === 0 ? (
        <p className="text-muted text-sm">none</p>
      ) : (
        <ul className="text-sm mb-2">
          {lineage.edges.map((e, i) => (
            <li key={i} className="text-foreground">
              {e.source} → {e.target} ({e.kind})
              {e.cardinality_transition ? ` · ${e.cardinality_transition}` : ''}
            </li>
          ))}
        </ul>
      )}
      <h4 className="text-muted text-sm">Filters</h4>
      {lineage.filters.length === 0 ? (
        <p className="text-muted text-sm">none</p>
      ) : (
        <ul className="text-sm">
          {lineage.filters.map((f, i) => (
            <li key={i} className="text-foreground">
              {f}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
