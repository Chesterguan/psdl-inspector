'use client';

import { useState } from 'react';
import { Database, Gauge } from 'lucide-react';
import CatalogView from '@/components/observatory/CatalogView';
import PreflightView from '@/components/preflight/PreflightView';

/** Wizard step 4: "Prepare for execution".
 *  Your scenario is certified — now explore the institutional data and preflight
 *  the extraction query before it touches the warehouse. */
export default function PrepareStep() {
  const [tab, setTab] = useState<'catalog' | 'preflight'>('catalog');

  const pill = (active: boolean) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded text-sm transition-colors ${
      active ? 'bg-accent text-white' : 'bg-background-tertiary text-muted hover:text-foreground'
    }`;

  return (
    <div className="bg-background-secondary border border-border rounded-lg p-6">
      <p className="text-muted text-sm mb-4">
        Your scenario is certified. Prepare to run it: browse the institutional data
        catalog to see what&apos;s available, then preflight your extraction query to
        catch a runaway scan <span className="text-foreground font-medium">before</span> it hits the warehouse.
      </p>

      <div className="flex gap-2 mb-5">
        <button onClick={() => setTab('catalog')} className={pill(tab === 'catalog')}>
          <Database className="w-4 h-4" /> Data Catalog
        </button>
        <button onClick={() => setTab('preflight')} className={pill(tab === 'preflight')}>
          <Gauge className="w-4 h-4" /> Preflight query
        </button>
      </div>

      {tab === 'catalog' ? <CatalogView /> : <PreflightView />}
    </div>
  );
}
