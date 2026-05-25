'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, EmptyPanel, ErrorPanel, LoadingPanel, ScoreBadge, UrgencyBadge } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, Signal, SignalCluster } from '@/lib/types/signals';

type Props = { params: { marketId: string; themeId: string } };
type Status = 'loading' | 'ready' | 'error';

export default function NicheThemeDetailPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const themeId = decodeURIComponent(params.themeId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [theme, setTheme] = useState<SignalCluster | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [marketsRes, clustersRes, signalsRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getClusters({ market_id: marketId }),
        signalApi.getSignals({ market_id: marketId }),
      ]);
      const selectedTheme = clustersRes.clusters.find(cluster => cluster.id === themeId) ?? null;
      setNiche(marketsRes.markets.find(market => market.id === marketId) ?? null);
      setTheme(selectedTheme);
      setSignals(signalsRes.signals);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load theme');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId, themeId]);

  const relatedSignals = useMemo(() => {
    if (!theme) return [];
    const ids = new Set(theme.signal_ids);
    return signals.filter(signal => ids.has(signal.id));
  }, [signals, theme]);

  return (
    <DashboardShell
      title={theme?.theme ?? 'Theme'}
      subtitle={`${niche?.name ?? 'This niche'} evidence behind this recurring pain pattern.`}
      actions={<NicheViewSwitcher marketId={marketId} active="themes" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading theme" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && !theme && (
        <EmptyPanel title="Theme not found" detail="This theme may have been removed or regrouped by a newer scan." />
      )}

      {status === 'ready' && theme && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid gap-3 sm:grid-cols-3">
            <Summary label="Findings" value={theme.frequency} />
            <Summary label="Companies" value={theme.company_count} accent={theme.company_count > 1} />
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">Average score</p>
              <div className="mt-2"><ScoreBadge value={theme.average_score} /></div>
            </div>
          </div>

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
            {relatedSignals.length === 0 ? (
              <div className="p-5">
                <EmptyPanel title="No related findings available" />
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {relatedSignals.map(signal => (
                  <article key={signal.id} className="p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="font-medium leading-snug text-slate-100">{signal.pain}</h3>
                        <p className="mt-1 text-sm text-slate-500">{signal.job_to_be_done}</p>
                      </div>
                      <UrgencyBadge urgency={signal.urgency} />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {signal.competitor_name && <Chip label={signal.competitor_name} />}
                      {signal.category && <Chip label={signal.category} />}
                      {signal.user_type && <Chip label={signal.user_type} />}
                    </div>
                    {signal.evidence_text && (
                      <p className="mt-3 rounded-lg bg-slate-950/35 px-3 py-2 text-xs leading-relaxed text-slate-500">{signal.evidence_text}</p>
                    )}
                    {signal.evidence_url && (
                      <a href={signal.evidence_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-xs font-medium text-violet-400 transition hover:text-violet-300">
                        Open evidence source
                      </a>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function Summary({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`rounded-xl border px-5 py-4 ${accent ? 'border-violet-500/20 bg-violet-600/[0.08]' : 'border-slate-800/80 bg-slate-900/50'}`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${accent ? 'text-violet-300' : 'text-slate-100'}`}>{value}</p>
    </div>
  );
}
