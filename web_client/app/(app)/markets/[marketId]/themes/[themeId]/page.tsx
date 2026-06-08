'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, EmptyPanel, ErrorPanel, LoadingPanel, UrgencyBadge } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { AccumulatedTheme, EvidenceItem, Market } from '@/lib/types/signals';

type Props = { params: { marketId: string; themeId: string } };
type Status = 'loading' | 'ready' | 'error';

export default function NicheThemeDetailPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const themeId = decodeURIComponent(params.themeId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [theme, setTheme] = useState<AccumulatedTheme | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [marketsRes, themesRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getThemes({ market_id: marketId }),
      ]);
      const selectedTheme = themesRes.themes.find(item => item.id === themeId) ?? null;
      setNiche(marketsRes.markets.find(market => market.id === marketId) ?? null);
      setTheme(selectedTheme);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pattern');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId, themeId]);

  const evidenceItems = useMemo(() => theme?.evidence_items ?? [], [theme]);

  return (
    <DashboardShell
      title={theme?.theme ?? 'Pattern'}
      subtitle={`${niche?.name ?? 'This niche'} evidence behind this recurring pattern.`}
      actions={<NicheViewSwitcher marketId={marketId} active="evidence" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading pattern" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && !theme && (
        <EmptyPanel title="Pattern not found" detail="This pattern may have been removed or regrouped by a newer scan." />
      )}

      {status === 'ready' && theme && (
        <div className="space-y-5 animate-fade-in">
          <Link
            href={`/markets/${encodeURIComponent(marketId)}/evidence?view=patterns`}
            className="inline-flex items-center gap-1.5 text-xs text-slate-600 transition hover:text-slate-400"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
            Evidence
          </Link>

          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
            {theme.summary && <p className="text-sm leading-relaxed text-slate-400">{theme.summary}</p>}
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-600">
                Across <span className="font-medium text-slate-400">{theme.company_count}</span>
                {theme.market_company_count != null && <> of <span className="font-medium text-slate-400">{theme.market_company_count}</span></>}{' '}
                {theme.company_count === 1 ? 'company' : 'companies'}
              </span>
              {theme.company_names.map(name => (
                <Chip key={name} label={name} />
              ))}
            </div>
          </section>

          {theme.top_examples.length > 0 && (
            <section className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
              <h2 className="mb-3 text-sm font-semibold text-slate-300">Examples</h2>
              <div className="space-y-2">
                {theme.top_examples.map(example => (
                  <p key={example} className="rounded-lg bg-slate-950/35 px-3 py-2 text-sm leading-relaxed text-slate-500">
                    {example}
                  </p>
                ))}
              </div>
            </section>
          )}

          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="border-b border-slate-800/70 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-300">Related findings</h2>
            </div>
            {evidenceItems.length === 0 ? (
              <div className="p-5">
                <EmptyPanel title="No related findings available" />
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {evidenceItems.map(item => (
                  <EvidenceFinding key={item.id} item={item} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function EvidenceFinding({ item }: { item: EvidenceItem }) {
  return (
    <article className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-medium leading-snug text-slate-100">{item.pain}</h3>
          {item.source_label && (
            <p className="mt-1 text-sm text-slate-500">{item.source_label}</p>
          )}
        </div>
        {item.urgency && <UrgencyBadge urgency={item.urgency} />}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {item.company_name && <Chip label={item.company_name} />}
        {item.category && <Chip label={item.category} />}
        {item.source_family && <Chip label={item.source_family.replace(/_/g, ' ')} />}
      </div>
      {item.quote && (
        <p className="mt-3 rounded-lg bg-slate-950/35 px-3 py-2 text-xs leading-relaxed text-slate-500">
          &ldquo;{item.quote}&rdquo;
        </p>
      )}
      {item.url && (
        <a href={item.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-xs font-medium text-violet-400 transition hover:text-violet-300">
          Open evidence source
        </a>
      )}
    </article>
  );
}
