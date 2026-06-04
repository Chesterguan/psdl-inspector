import { Confidence, RiskLevel, RuntimeCategory } from './types';

interface Props {
  riskLevel: RiskLevel;
  confidence: Confidence;
  runtimeCategory: RuntimeCategory;
}

// The go/no-go verdict tracks feasibility (estimated runtime/cost), not the raw
// table-risk score — a well-scoped query against a high-risk table can still be
// cheap to run. FAST → GO, EXTREME → BLOCK, everything in between → CAUTION.
function verdict(runtime: RuntimeCategory): { label: string; cls: string } {
  if (runtime === 'FAST') return { label: 'GO', cls: 'bg-green-700 text-white' };
  if (runtime === 'EXTREME') return { label: 'BLOCK', cls: 'bg-red-700 text-white' };
  return { label: 'CAUTION', cls: 'bg-accent-warning text-black' };
}

export default function VerdictBanner({
  riskLevel,
  confidence,
  runtimeCategory,
}: Props) {
  const v = verdict(runtimeCategory);
  return (
    <div className={`rounded-md p-4 flex items-center gap-4 ${v.cls}`}>
      <span className="text-2xl font-bold">{v.label}</span>
      <span className="text-sm opacity-90">risk: {riskLevel}</span>
      <span className="ml-auto text-sm bg-background-tertiary text-foreground px-2 py-0.5 rounded">
        confidence: {confidence}
      </span>
      <span className="text-sm bg-background-tertiary text-foreground px-2 py-0.5 rounded">
        runtime: {runtimeCategory}
      </span>
    </div>
  );
}
