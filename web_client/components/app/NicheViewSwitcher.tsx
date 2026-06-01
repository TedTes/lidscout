'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';

type NicheView = 'gaps' | 'themes' | 'findings' | 'reports' | 'sources' | 'activity';

const VIEWS: Array<{ id: NicheView; label: string; href: (marketId: string) => string }> = [
  { id: 'gaps', label: 'Gaps', href: marketId => `/markets/${encodeURIComponent(marketId)}/gaps` },
  { id: 'themes', label: 'Themes', href: marketId => `/markets/${encodeURIComponent(marketId)}/themes` },
  { id: 'findings', label: 'Findings', href: marketId => `/markets/${encodeURIComponent(marketId)}/findings` },
  { id: 'reports', label: 'Reports', href: marketId => `/markets/${encodeURIComponent(marketId)}/reports` },
  { id: 'sources', label: 'Sources', href: marketId => `/markets/${encodeURIComponent(marketId)}/sources` },
  { id: 'activity', label: 'Activity', href: marketId => `/markets/${encodeURIComponent(marketId)}/activity` },
];

function IconRefresh({ spinning }: { spinning?: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={spinning ? 'animate-spin' : undefined}
    >
      <path d="M21 12a9 9 0 0 1-15 6.7" />
      <path d="M3 12a9 9 0 0 1 15-6.7" />
      <path d="M18 3v5h-5" />
      <path d="M6 21v-5h5" />
    </svg>
  );
}

export function NicheViewSwitcher({
  marketId,
  active,
  onRefresh,
  refreshing,
  trailingAction,
}: {
  marketId: string;
  active: NicheView;
  onRefresh?: () => void;
  refreshing?: boolean;
  trailingAction?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-start gap-3 lg:justify-end">
      <div className="min-w-0 flex gap-6 overflow-x-auto border-b border-slate-800/80 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {VIEWS.map(view => {
          const selected = view.id === active;
          return (
            <Link
              key={view.id}
              href={view.href(marketId)}
              className={`border-b-2 px-0 pb-3 pt-1 text-sm font-semibold transition ${
                selected
                  ? 'border-violet-500 text-slate-100'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              {view.label}
            </Link>
          );
        })}
      </div>
      {trailingAction}
      {!trailingAction && onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-800/80 bg-slate-900/50 text-slate-500 transition hover:bg-slate-800/80 hover:text-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="Refresh"
          title="Refresh"
        >
          <IconRefresh spinning={refreshing} />
        </button>
      )}
    </div>
  );
}
