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

export function NicheViewSwitcher({
  marketId,
  active,
}: {
  marketId: string;
  active: NicheView;
  onRefresh?: () => void;
  refreshing?: boolean;
  trailingAction?: ReactNode;
}) {
  return (
    <div className="flex w-full min-w-0 items-center justify-start gap-2 lg:justify-center">
      <div className="flex min-w-0 flex-1 gap-5 overflow-x-auto border-b border-slate-800/80 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:gap-6 lg:flex-none">
        {VIEWS.map(view => {
          const selected = view.id === active;
          return (
            <Link
              key={view.id}
              href={view.href(marketId)}
              className={`shrink-0 border-b-2 px-0 pb-2 pt-0 text-sm font-semibold transition lg:pb-3 lg:pt-1 ${
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
    </div>
  );
}
