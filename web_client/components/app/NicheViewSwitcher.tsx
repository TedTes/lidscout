import Link from 'next/link';

type NicheView = 'gaps' | 'themes' | 'findings' | 'reports' | 'sources';

const VIEWS: Array<{ id: NicheView; label: string; href: (marketId: string) => string }> = [
  { id: 'gaps', label: 'Gaps', href: marketId => `/markets/${encodeURIComponent(marketId)}/gaps` },
  { id: 'themes', label: 'Themes', href: marketId => `/markets/${encodeURIComponent(marketId)}/themes` },
  { id: 'findings', label: 'Findings', href: marketId => `/markets/${encodeURIComponent(marketId)}/findings` },
  { id: 'reports', label: 'Report', href: marketId => `/markets/${encodeURIComponent(marketId)}/reports` },
  { id: 'sources', label: 'Sources', href: marketId => `/markets/${encodeURIComponent(marketId)}/sources` },
];

export function NicheViewSwitcher({ marketId, active }: { marketId: string; active: NicheView }) {
  return (
    <div className="flex flex-wrap justify-end gap-1 rounded-full border border-slate-800/80 bg-slate-900/50 p-1">
      {VIEWS.map(view => {
        const selected = view.id === active;
        return (
          <Link
            key={view.id}
            href={view.href(marketId)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              selected
                ? 'bg-violet-500/15 text-violet-300'
                : 'text-slate-500 hover:bg-slate-800/80 hover:text-slate-300'
            }`}
          >
            {view.label}
          </Link>
        );
      })}
    </div>
  );
}
