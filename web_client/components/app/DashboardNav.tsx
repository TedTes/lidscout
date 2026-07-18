'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { AddNicheFlow } from '@/components/app/AddNicheFlow';
import AccountMenu from '@/components/app/AccountMenu';
import { signalApi } from '@/lib/api';
import { PRODUCT_NAME, PRODUCT_TAGLINE } from '@/lib/positioning';
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

// ── Niche category icon ────────────────────────────────────────────────────────

// Domain-detected categories (name-keyword based)
type DetectedCategory =
  | 'podcast' | 'education' | 'ecommerce' | 'software' | 'health'
  | 'analytics' | 'real-estate' | 'finance' | 'content' | 'jobs' | 'local';

// Hash-pool categories (id-based, for custom markets that don't match a domain)
type FallbackCategory =
  | 'target' | 'layers' | 'navigation' | 'cpu' | 'star' | 'zap'
  | 'leaf' | 'flame' | 'globe' | 'gift' | 'activity' | 'diamond';

type MarketCategory = DetectedCategory | FallbackCategory;

// Stable index from any string (market id)
function hashIndex(str: string, len: number): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  return Math.abs(h) % len;
}

const FALLBACK_POOL: FallbackCategory[] = [
  'target', 'layers', 'navigation', 'cpu', 'star', 'zap',
  'leaf', 'flame', 'globe', 'gift', 'activity', 'diamond',
];

function detectCategory(name: string): DetectedCategory | null {
  const s = name.toLowerCase();
  if (/podcast|audio|music|radio|voice|speak|listen/.test(s))            return 'podcast';
  if (/educat|learn|course|teach|tutor|school|training/.test(s))         return 'education';
  if (/ecommerce|e-commerce|shop|sell|store|retail|marketplace/.test(s)) return 'ecommerce';
  if (/software|saas|app|developer|code|api|platform|tool|plugin/.test(s)) return 'software';
  if (/health|fitness|wellness|mental|medic|yoga|diet|gym/.test(s))      return 'health';
  if (/data|analytic|dashboard|metric|report|insight|track/.test(s))     return 'analytics';
  if (/real.?estate|property|home|hous|rent|mortgage/.test(s))           return 'real-estate';
  if (/financ|invest|crypto|trading|bank|money|wealth|bookkeep|accounting/.test(s)) return 'finance';
  if (/content|creator|video|photo|media|blog|newsletter|social/.test(s)) return 'content';
  if (/job|hire|recruit|career|talent|staffing|employ/.test(s))          return 'jobs';
  if (/local|restaurant|food|community|event|neighbor|city/.test(s))     return 'local';
  return null;
}

function resolveCategory(marketId: string, marketName: string): MarketCategory {
  return detectCategory(marketName) ?? FALLBACK_POOL[hashIndex(marketId, FALLBACK_POOL.length)];
}

const CATEGORY_GRADIENT: Record<MarketCategory, string> = {
  // Domain-detected
  podcast:      'from-violet-600 to-purple-800',
  education:    'from-amber-500 to-yellow-700',
  ecommerce:    'from-emerald-500 to-teal-700',
  software:     'from-sky-500 to-blue-700',
  health:       'from-rose-500 to-pink-700',
  analytics:    'from-indigo-500 to-violet-700',
  'real-estate':'from-orange-500 to-amber-700',
  finance:      'from-emerald-600 to-green-800',
  content:      'from-orange-500 to-red-600',
  jobs:         'from-teal-500 to-cyan-700',
  local:        'from-yellow-500 to-amber-600',
  // Hash-pool fallbacks
  target:       'from-violet-700 to-purple-900',
  layers:       'from-blue-600 to-blue-900',
  navigation:   'from-teal-600 to-teal-900',
  cpu:          'from-indigo-600 to-slate-800',
  star:         'from-rose-600 to-rose-900',
  zap:          'from-yellow-500 to-orange-700',
  leaf:         'from-green-600 to-green-900',
  flame:        'from-red-600 to-red-900',
  globe:        'from-sky-600 to-blue-800',
  gift:         'from-fuchsia-600 to-pink-800',
  activity:     'from-cyan-500 to-cyan-800',
  diamond:      'from-purple-600 to-purple-900',
};

function CategoryIcon({ category, size }: { category: MarketCategory; size?: number }) {
  const s = size ?? 11;
  const base = { width: s, height: s, viewBox: '0 0 24 24', fill: 'none', stroke: 'white', strokeWidth: 2.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (category) {
    // ── Domain-detected ────────────────────────────────────────────────────────
    case 'podcast': return (
      <svg {...base}>
        <path d="M12 2a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
        <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
        <line x1="12" y1="19" x2="12" y2="22" />
      </svg>
    );
    case 'education': return (
      <svg {...base}>
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c3 3 9 3 12 0v-5" />
      </svg>
    );
    case 'ecommerce': return (
      <svg {...base}>
        <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <path d="M16 10a4 4 0 01-8 0" />
      </svg>
    );
    case 'software': return (
      <svg {...base}>
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    );
    case 'health': return (
      <svg {...base}>
        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 000-7.78z" />
      </svg>
    );
    case 'analytics': return (
      <svg {...base}>
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    );
    case 'real-estate': return (
      <svg {...base}>
        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    );
    case 'finance': return (
      <svg {...base}>
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        <polyline points="17 6 23 6 23 12" />
      </svg>
    );
    case 'content': return (
      <svg {...base}>
        <polygon points="23 7 16 12 23 17 23 7" />
        <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
      </svg>
    );
    case 'jobs': return (
      <svg {...base}>
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16" />
      </svg>
    );
    case 'local': return (
      <svg {...base}>
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    );
    // ── Hash-pool fallbacks ────────────────────────────────────────────────────
    case 'target': return (
      <svg {...base}>
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="4" />
        <line x1="22" y1="12" x2="18" y2="12" />
        <line x1="6" y1="12" x2="2" y2="12" />
        <line x1="12" y1="6" x2="12" y2="2" />
        <line x1="12" y1="22" x2="12" y2="18" />
      </svg>
    );
    case 'layers': return (
      <svg {...base}>
        <polygon points="12 2 2 7 12 12 22 7 12 2" />
        <polyline points="2 17 12 22 22 17" />
        <polyline points="2 12 12 17 22 12" />
      </svg>
    );
    case 'navigation': return (
      <svg {...base}>
        <polygon points="3 11 22 2 13 21 11 13 3 11" />
      </svg>
    );
    case 'cpu': return (
      <svg {...base}>
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <rect x="9" y="9" width="6" height="6" />
        <line x1="9" y1="1" x2="9" y2="4" />
        <line x1="15" y1="1" x2="15" y2="4" />
        <line x1="9" y1="20" x2="9" y2="23" />
        <line x1="15" y1="20" x2="15" y2="23" />
      </svg>
    );
    case 'star': return (
      <svg {...base}>
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    );
    case 'zap': return (
      <svg {...base}>
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    );
    case 'leaf': return (
      <svg {...base}>
        <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z" />
        <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
      </svg>
    );
    case 'flame': return (
      <svg {...base}>
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 3z" />
      </svg>
    );
    case 'globe': return (
      <svg {...base}>
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    );
    case 'gift': return (
      <svg {...base}>
        <polyline points="20 12 20 22 4 22 4 12" />
        <rect x="2" y="7" width="20" height="5" />
        <line x1="12" y1="22" x2="12" y2="7" />
        <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z" />
        <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />
      </svg>
    );
    case 'activity': return (
      <svg {...base}>
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    );
    case 'diamond': return (
      <svg {...base}>
        <path d="M2.7 10.3a2.41 2.41 0 0 0 0 3.41l7.59 7.59a2.41 2.41 0 0 0 3.41 0l7.59-7.59a2.41 2.41 0 0 0 0-3.41L13.7 2.71a2.41 2.41 0 0 0-3.41 0z" />
      </svg>
    );
  }
}

function NicheIcon({ marketId, marketName, active, compact }: { marketId: string; marketName: string; active?: boolean; compact?: boolean }) {
  const category = resolveCategory(marketId, marketName);
  const size = compact ? 'h-[18px] w-[18px] rounded-[4px]' : 'h-[22px] w-[22px] rounded-[5px]';
  return (
    <span
      className={`flex shrink-0 items-center justify-center bg-gradient-to-br ${CATEGORY_GRADIENT[category]} shadow-[0_1px_4px_rgba(0,0,0,0.5)] transition-all ${size} ${
        active
          ? 'ring-2 ring-violet-400/55 ring-offset-[1.5px] ring-offset-[#07091a]'
          : 'opacity-60 group-hover:opacity-85'
      }`}
    >
      <CategoryIcon category={category} size={compact ? 9 : 11} />
    </span>
  );
}

function activeNicheFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/markets\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function nicheHref(nicheId: string) {
  return `/markets/${encodeURIComponent(nicheId)}/gaps`;
}

function formatUntil(isoString: string | null): string | null {
  if (!isoString) return null;
  const ms = new Date(isoString).getTime() - Date.now();
  if (ms <= 0) return 'soon';
  const hours = Math.floor(ms / 3600000);
  if (hours > 0) return `${hours}h`;
  const minutes = Math.floor((ms % 3600000) / 60000);
  return `${Math.max(minutes, 1)}m`;
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
  onDelete,
}: {
  markets: Market[];
  activeId: string | null;
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
      <div className="w-full rounded-lg border border-dashed border-slate-800 px-3 py-3 text-left text-xs text-slate-600">
        No watchlists yet - add one
      </div>
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
              title={market.name}
              className={`flex gap-2.5 rounded-lg px-3 py-2.5 pr-8 text-sm font-medium transition ${
                active
                  ? 'items-start bg-violet-600/[0.13] text-violet-300'
                  : 'items-start text-slate-500 hover:bg-white/[0.04] hover:text-slate-300'
              }`}
            >
              <NicheIcon marketId={market.id} marketName={market.name} active={active} />
              <span className="min-w-0 flex-1 leading-snug line-clamp-2">{market.display_label ?? market.name}</span>
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
    <div ref={ref} className="relative min-w-0 flex-1 px-1 sm:px-3">
      <button
        onClick={() => setOpen(value => !value)}
        className="flex w-full items-center gap-2 rounded-lg border border-slate-800/70 bg-slate-900/55 px-3 py-2.5 text-left text-xs shadow-sm shadow-black/10 transition hover:border-slate-700/60 hover:bg-slate-800/50"
      >
        {active
          ? <NicheIcon marketId={active.id} marketName={active.name} active compact />
          : <span className="h-[18px] w-[18px] shrink-0 rounded-[4px] bg-slate-800" />
        }
        <span className="min-w-0 flex-1 truncate font-semibold text-slate-200">
          {active ? active.name : 'No watchlists'}
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
              className={`group flex items-center gap-2 px-3 py-1.5 text-xs transition hover:bg-white/[0.04] ${market.id === activeId ? 'text-violet-300' : 'text-slate-500 hover:text-slate-300'}`}
            >
              <NicheIcon marketId={market.id} marketName={market.name} active={market.id === activeId} compact />
              <span className="min-w-0 flex-1 truncate">{market.name}</span>
            </Link>
          ))}
          <div className="mx-3 my-1 h-px bg-white/[0.05]" />
          <button
            onClick={() => { setOpen(false); onAddNiche(); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-violet-500 transition hover:bg-white/[0.04] hover:text-violet-400"
          >
            <IconPlus /> Create watchlist
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
  const [nextRunAt, setNextRunAt] = useState<string | null>(null);

  useEffect(() => {
    signalApi.getMarkets()
      .then(response => setMarkets(response.markets))
      .catch(() => setMarkets([]));
    signalApi.getPipelineSchedule()
      .then(response => setNextRunAt(response.next_run_at))
      .catch(() => setNextRunAt(null));
  }, []); // mount-only — state kept in sync by handleNicheCreated / handleDeleteNiche

  useEffect(() => {
    if (activeId && markets.length > 0 && !markets.find(m => m.id === activeId)) {
      signalApi.getMarkets({ force: true })
        .then(response => setMarkets(response.markets))
        .catch(() => {});
    }
  }, [activeId, markets]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowAddNiche(true);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

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
  const nextRunLabel = formatUntil(nextRunAt);

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[260px] flex-col border-r border-white/[0.06] bg-[#07091a] lg:flex">
        <Link href="/markets" className="flex h-[62px] items-center gap-3 px-5 transition hover:opacity-80">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white shadow-lg shadow-violet-950">
            <IconRadar />
          </div>
          <div>
            <p className="text-[13px] font-bold tracking-tight text-slate-100">{PRODUCT_NAME}</p>
            <p className="text-[10px] leading-tight text-slate-600">{PRODUCT_TAGLINE}</p>
          </div>
        </Link>

        <div className="mx-4 h-px bg-white/[0.06]" />

        <nav className="mt-4 flex min-h-0 flex-1 flex-col px-3">
          <div className="mb-2 flex items-center justify-between px-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-700">
              Watchlists
            </p>
            <button
              onClick={() => setShowAddNiche(true)}
              className="rounded p-1 text-slate-400 transition hover:bg-white/[0.06] hover:text-slate-200"
              aria-label="Create watchlist"
            >
              <IconPlus />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto pr-1 [scrollbar-width:thin] [scrollbar-color:rgba(71,85,105,0.45)_transparent]">
            <NicheList markets={markets} activeId={activeId} onDelete={handleDeleteNiche} />
          </div>
          <div className="mt-2 h-px shrink-0 bg-white/[0.06]" />
          <button
            onClick={() => setShowAddNiche(true)}
            className="mt-2 flex w-full shrink-0 items-center gap-2 rounded-lg border border-dashed border-slate-800 px-3 py-2.5 text-left text-sm font-medium text-blue-400 transition hover:border-slate-700 hover:bg-white/[0.03] hover:text-blue-300"
          >
            <IconPlus />
            <span className="min-w-0 flex-1 truncate">Create watchlist</span>
            <span className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-slate-500">⌘K</span>
          </button>
        </nav>

        <div className="mx-4 mb-4 mt-3 border-t border-white/[0.06] pt-3">
          <div className="space-y-2 px-2 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>API online</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-slate-700" />
              <span>Agent next{nextRunLabel ? ` in ${nextRunLabel}` : ''}</span>
            </div>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-12 min-w-0 items-center justify-between gap-2 border-b border-white/[0.06] bg-[#07091a]/95 px-3 backdrop-blur-md sm:px-4 lg:hidden">
        <Link href="/markets" className="flex shrink-0 items-center gap-2.5 transition hover:opacity-80">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-600 text-white">
            <IconRadar />
          </div>
          <span className="hidden text-sm font-bold tracking-tight text-slate-100 min-[390px]:inline">{PRODUCT_NAME}</span>
        </Link>
        <MobileNicheMenu markets={markets} activeId={activeId} onAddNiche={() => setShowAddNiche(true)} />
        <AccountMenu compact />
      </header>

      <AddNicheFlow
        isOpen={showAddNiche}
        onClose={() => setShowAddNiche(false)}
        onCreated={handleNicheCreated}
        existingMarkets={markets}
      />
    </>
  );
}
