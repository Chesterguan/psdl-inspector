'use client';

import CatalogView from '@/components/observatory/CatalogView';

export default function CatalogPage() {
  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-foreground">Institutional Data Catalog</h1>
        <a href="/" className="text-sm text-accent hover:underline">← Back to Inspector</a>
      </div>
      <CatalogView />
    </main>
  );
}
