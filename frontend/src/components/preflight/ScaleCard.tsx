import { ScaleEstimate } from './types';

interface Props {
  scale: ScaleEstimate;
}

export default function ScaleCard({ scale }: Props) {
  const rows: [string, number | null][] = [
    ['patients', scale.patients],
    ['encounters', scale.encounters],
    ['events', scale.events],
    ['intermediate_records', scale.intermediate_records],
    ['output_records', scale.output_records],
  ];
  const present = rows.filter(([, v]) => v !== null && v !== undefined);
  return (
    <div className="border border-border rounded-md p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-foreground">Scale estimate</h3>
        <span className="text-xs bg-background-tertiary text-muted px-2 py-0.5 rounded">
          confidence: {scale.confidence}
        </span>
      </div>
      {present.length === 0 ? (
        <p className="text-muted text-sm">No scale estimate available.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 text-sm">
          {present.map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-muted">{k}</span>
              <span className="text-foreground">{v}</span>
            </div>
          ))}
        </div>
      )}
      {scale.per_stage.length > 0 && (
        <div className="mt-3 text-sm">
          <h4 className="text-muted mb-1">Per stage</h4>
          {scale.per_stage.map((s, i) => (
            <div key={i} className="flex justify-between">
              <span className="text-foreground">{s.name}</span>
              <span className="text-muted">{s.est_rows}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
