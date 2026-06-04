import {
  Bottleneck,
  Optimization,
  StudySummary,
} from './types';

interface Props {
  summary: StudySummary;
  riskReasons: string[];
  bottlenecks: Bottleneck[];
  optimizations: Optimization[];
  notes: string[];
}

export default function FindingsLists({
  summary,
  riskReasons,
  bottlenecks,
  optimizations,
  notes,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="border border-border rounded-md p-4">
        <h3 className="font-semibold text-foreground mb-2">Risk reasons</h3>
        {riskReasons.length === 0 ? (
          <p className="text-muted text-sm">No risk reasons flagged.</p>
        ) : (
          <ul className="list-disc list-inside text-sm text-foreground">
            {riskReasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="border border-border rounded-md p-4">
        <h3 className="font-semibold text-foreground mb-2">Bottlenecks</h3>
        {bottlenecks.length === 0 ? (
          <p className="text-muted text-sm">none</p>
        ) : (
          <ul className="text-sm text-foreground space-y-1">
            {bottlenecks.map((b, i) => (
              <li key={i}>
                <span className="font-medium">{b.component}</span> —{' '}
                {b.reason} ({b.contribution_pct}%)
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border border-border rounded-md p-4">
        <h3 className="font-semibold text-foreground mb-2">Recommendations</h3>
        {optimizations.length === 0 ? (
          <p className="text-muted text-sm">none</p>
        ) : (
          <ul className="text-sm text-foreground space-y-1">
            {optimizations.map((o, i) => (
              <li key={i}>
                <span className="font-medium">{o.action}</span> — {o.rationale}
                {o.expected_benefit ? ` (${o.expected_benefit})` : ''}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border border-border rounded-md p-4">
        <h3 className="font-semibold text-foreground mb-2">Summary &amp; notes</h3>
        <p className="text-sm text-muted">
          target: {summary.execution_target}
          {summary.query_shape ? ` · shape: ${summary.query_shape}` : ''}
        </p>
        {summary.tables.length > 0 && (
          <p className="text-sm text-muted">
            tables: {summary.tables.join(', ')}
          </p>
        )}
        {summary.domains.length > 0 && (
          <p className="text-sm text-muted">
            domains: {summary.domains.join(', ')}
          </p>
        )}
        {notes.length > 0 && (
          <ul className="list-disc list-inside text-sm text-foreground mt-2">
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
