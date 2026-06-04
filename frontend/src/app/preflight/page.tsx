'use client';

import PreflightView from '@/components/preflight/PreflightView';

export default function PreflightPage() {
  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-foreground">SQL Preflight</h1>
        <a href="/" className="text-accent text-sm">← Back to Inspector</a>
      </div>
      <div className="max-w-4xl mx-auto">
        <PreflightView />
      </div>
    </div>
  );
}
