'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { AddNicheDrawer } from '@/components/app/AddNicheDrawer';
import { signalApi } from '@/lib/api';
import { Market } from '@/lib/types/signals';

function IconRadar() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14" />
    </svg>
  );
}

function IconPlus() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconCaret() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function activeNicheFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/markets\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function nicheHref(nicheId: string) {
  return `/markets/${encodeURIComponent(nicheId)}/gaps`;
}

function IconTrash() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  );
}

function NicheList({
  markets,
  activeId,
  onAddNiche,
  onDelete,
}: {
  markets: Market[];
  activeId: string | null;
  onAddNiche: () => void;
  onDelete: (id: string) => Promise<void>;
}) {
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
      setConfirmId(null);
    }
  };

  if (markets.length === 0) {
    return (
      <button
        onClick={onAddNiche}
        className="w-full rounded-lg border border-dashed border-slate-800 px-3 py-3 text-left text-xs text-slate-600 transition hover:border-slate-700 hover:text-slate-500"
      >
        No niches yet — add one
      </button>
    );
  }

  return (
    <div className="space-y-1">
      {markets.map(market => {
        const active = market.id === activeId;

        if (confirmId === market.id) {
          return (
            <div key={market.id} className="rounded-lg border border-rose-500/25 bg-rose-500/[0.06] px-3 py-2">
              <p className="mb-2 truncate text-xs font-medium text-slate-400">{market.name}</p>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleDelete(market.id)}
                  disabled={deletingId === market.id}
                  className="rounded px-2 py-1 text-[11px] font-semibold text-rose-400 transition hover:bg-rose-500/10 disabled:opacity-50"
                >
                  {deletingId === market.id ? 'Deleting…' : 'Delete'}
                </button>
                <button
                  onClick={() => setConfirmId(null)}
                  className="rounded px-2 py-1 text-[11px] text-slate-600 transition hover:text-slate-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          );
        }

        return (
          <div key={market.id} className="group relative">
            <Link
              href={nicheHref(market.id)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2.5 pr-8 text-sm font-medium transition ${
                active
                  ? 'bg-violet-600/[0.13] text-violet-300'
                  : 'text-slate-500 hover:bg-white/[0.04] hover:text-slate-300'
              }`}
            >
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${active ? 'bg-violet-400 shadow-[0_0_8px_rgba(167,139,250,0.9)]' : 'bg-slate-700 group-hover:bg-slate-500'}`} />
              <span className="min-w-0 flex-1 truncate">{market.name}</span>
            </Link>
            <button
              onClick={e => { e.preventDefault(); setConfirmId(market.id); }}
              aria-label={`Delete ${market.name}`}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-700 opacity-0 transition hover:bg-white/[0.04] hover:text-rose-400 group-hover:opacity-100"
            >
              <IconTrash />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function MobileNicheMenu({
  markets,
  activeId,
  onAddNiche,
}: {
  markets: Market[];
  activeId: string | null;
  onAddNiche: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const active = markets.find(market => market.id === activeId) ?? markets[0] ?? null;

  useEffect(() => {
    if (!open) return;
    const handler = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} className="relative min-w-0 flex-1 px-3">
      <button
        onClick={() => setOpen(value => !value)}
        className="flex w-full items-center gap-2 rounded-lg border border-slate-800/60 bg-slate-900/40 px-3 py-2 text-left text-xs transition hover:border-slate-700/60 hover:bg-slate-800/40"
      >
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${active ? 'bg-violet-500' : 'bg-slate-700'}`} />
        <span className="min-w-0 flex-1 truncate font-medium text-slate-400">
          {active ? active.name : 'No niches'}
        </span>
        <span className={`shrink-0 text-slate-700 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}>
          <IconCaret />
        </span>
      </button>

      {open && (
        <div className="absolute left-3 right-3 top-full z-50 mt-1 overflow-hidden rounded-lg border border-slate-700/60 bg-[#0b0e24] py-1 shadow-xl shadow-black/50">
          {markets.map(market => (
            <Link
              key={market.id}
              href={nicheHref(market.id)}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs transition hover:bg-white/[0.04] ${market.id === activeId ? 'text-violet-300' : 'text-slate-500 hover:text-slate-300'}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${market.id === activeId ? 'bg-violet-400' : 'bg-slate-700'}`} />
              <span className="min-w-0 flex-1 truncate">{market.name}</span>
            </Link>
          ))}
          <div className="mx-3 my-1 h-px bg-white/[0.05]" />
          <button
            onClick={() => { setOpen(false); onAddNiche(); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-violet-500 transition hover:bg-white/[0.04] hover:text-violet-400"
          >
            <IconPlus /> Add niche
          </button>
        </div>
      )}
    </div>
  );
}

export default function DashboardNav() {
  const pathname = usePathname();
  const router = useRouter();
  const activeId = activeNicheFromPath(pathname);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [showAddNiche, setShowAddNiche] = useState(false);

  useEffect(() => {
    signalApi.getMarkets()
      .then(response => setMarkets(response.markets))
      .catch(() => setMarkets([]));
  }, [pathname]);

  const handleNicheCreated = (market: Market) => {
    setMarkets(prev => [...prev, market]);
    setShowAddNiche(false);
    router.push(`/markets/${encodeURIComponent(market.id)}/gaps`);
  };

  const handleDeleteNiche = async (id: string) => {
    await signalApi.deleteMarket(id);
    setMarkets(prev => prev.filter(m => m.id !== id));
    if (activeId === id) router.push('/markets');
  };

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[220px] flex-col border-r border-white/[0.06] bg-[#07091a] lg:flex">
        <Link href="/markets" className="flex h-[62px] items-center gap-3 px-5 transition hover:opacity-80">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white shadow-lg shadow-violet-950">
            <IconRadar />
          </div>
          <div>
            <p className="text-[13px] font-bold tracking-tight text-slate-100">LidScout</p>
            <p className="text-[10px] leading-tight text-slate-600">Niche opportunity intelligence</p>
          </div>
        </Link>

        <div className="mx-4 h-px bg-white/[0.06]" />

        <nav className="mt-4 flex min-h-0 flex-1 flex-col px-3">
          <div className="mb-2 flex items-center justify-between px-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-700">
              Niches
            </p>
            <button
              onClick={() => setShowAddNiche(true)}
              className="rounded p-1 text-slate-700 transition hover:bg-white/[0.04] hover:text-slate-400"
              aria-label="Add niche"
            >
              <IconPlus />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto pr-1">
            <NicheList markets={markets} activeId={activeId} onAddNiche={() => setShowAddNiche(true)} onDelete={handleDeleteNiche} />
          </div>
        </nav>

        <div className="px-3 pb-5 pt-4">
          <div className="rounded-lg border border-white/[0.05] bg-slate-900/60 px-3 py-2.5">
            <div className="flex items-center gap-2.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_7px_rgba(52,211,153,0.8)]" />
              <span className="text-xs font-medium text-slate-600">API online</span>
            </div>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-white/[0.06] bg-[#07091a]/95 px-4 backdrop-blur-md lg:hidden">
        <Link href="/markets" className="flex items-center gap-2.5 transition hover:opacity-80">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-600 text-white">
            <IconRadar />
          </div>
          <span className="text-sm font-bold tracking-tight text-slate-100">LidScout</span>
        </Link>
        <MobileNicheMenu markets={markets} activeId={activeId} onAddNiche={() => setShowAddNiche(true)} />
        <button
          onClick={() => setShowAddNiche(true)}
          className="rounded-md border border-slate-800/70 bg-slate-900/50 p-2 text-slate-500 transition hover:text-slate-300"
          aria-label="Add niche"
        >
          <IconPlus />
        </button>
      </header>

      <AddNicheDrawer
        isOpen={showAddNiche}
        onClose={() => setShowAddNiche(false)}
        onCreated={handleNicheCreated}
      />
    </>
  );
}
