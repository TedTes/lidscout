'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { EmptyPanel, ErrorPanel, LoadingPanel, ScoreBadge, StatRow } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, SignalCluster } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

export default function NicheThemesPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [themes, setThemes] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [marketsRes, clustersRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getClusters({ market_id: marketId }),
      ]);
      setNiche(marketsRes.markets.find(market => market.id === marketId) ?? null);
      setThemes(clustersRes.clusters);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load themes');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const findingCount = themes.reduce((sum, theme) => sum + theme.frequency, 0);
  const broadThemes = themes.filter(theme => theme.company_count > 1).length;

  return (
    <DashboardShell
      title="Themes"
      subtitle={`${niche?.name ?? 'This niche'} pain patterns grouped by recurring evidence.`}
      actions={<NicheViewSwitcher marketId={marketId} active="themes" onRefresh={load} refreshing={status === 'loading'} />}
    >
      {status === 'loading' && <LoadingPanel label="Loading themes" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <StatRow stats={[
            { label: 'Themes', value: themes.length },
            { label: 'Findings grouped', value: findingCount },
            { label: 'Multi-company', value: broadThemes, accent: broadThemes > 0 },
          ]} />

          {themes.length === 0 ? (
            <EmptyPanel title="No themes yet" detail="Themes appear after findings are grouped from active sources." />
          ) : (
            <div className="space-y-3">
              {themes
                .slice()
                .sort((a, b) => b.frequency - a.frequency)
                .map(theme => (
                  <Link
                    key={theme.id}
                    href={`/markets/${encodeURIComponent(marketId)}/themes/${encodeURIComponent(theme.id)}`}
                    className="block rounded-xl border border-slate-800/70 bg-slate-900/40 p-5 transition hover:border-slate-700/80 hover:bg-slate-900/60"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h2 className="font-semibold text-slate-100">{theme.theme}</h2>
                        {theme.summary && (
                          <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-slate-500">{theme.summary}</p>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-500">
                          {theme.frequency} findings
                        </span>
                        <ScoreBadge value={theme.average_score} />
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className="text-xs text-slate-600">
                        Across <span className="font-medium text-slate-400">{theme.company_count}</span>
                        {theme.market_company_count != null && <> of <span className="font-medium text-slate-400">{theme.market_company_count}</span></>}{' '}
                        {theme.company_count === 1 ? 'company' : 'companies'}
                      </span>
                      {theme.company_names.slice(0, 5).map(name => (
                        <span key={name} className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">{name}</span>
                      ))}
                    </div>

                    {theme.top_examples.length > 0 && (
                      <div className="mt-4 space-y-2 border-t border-slate-800/50 pt-4">
                        {theme.top_examples.slice(0, 2).map(example => (
                          <p key={example} className="rounded-lg bg-slate-950/35 px-3 py-2 text-xs leading-relaxed text-slate-500">
                            {example}
                          </p>
                        ))}
                      </div>
                    )}
                  </Link>
                ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

