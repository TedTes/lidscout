'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardShell from '@/components/app/DashboardShell';
import { AddMarketPanel } from '@/components/app/AddMarketPanel';
import { LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market } from '@/lib/types/signals';

function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

export default function NichesPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    signalApi.getMarkets()
      .then(response => {
        if (response.markets[0]) {
          router.replace(`/markets/${encodeURIComponent(response.markets[0].id)}`);
          return;
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [router]);

  const handleAdd = (market: Market) => {
    router.replace(`/markets/${encodeURIComponent(market.id)}`);
  };

  if (loading) {
    return (
      <DashboardShell title="Niches" subtitle="Choose the opportunity space you want to inspect.">
        <LoadingPanel label="Loading niches" />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell title="Niches" subtitle="Add your first niche to start surfacing gaps.">
      {showForm ? (
        <AddMarketPanel onAdd={handleAdd} onCancel={() => setShowForm(false)} />
      ) : (
        <div className="rounded-xl border border-dashed border-slate-800 px-8 py-20 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-slate-600">
            <IconPlus />
          </div>
          <p className="font-medium text-slate-300">Add your first niche</p>
          <p className="mx-auto mt-1 max-w-sm text-sm leading-relaxed text-slate-600">
            Pick a niche, add companies and sources, then LidScout will surface ranked gaps from the evidence.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-500"
          >
            <IconPlus /> Add niche
          </button>
        </div>
      )}
    </DashboardShell>
  );
}
