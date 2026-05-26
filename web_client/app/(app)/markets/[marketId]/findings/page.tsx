'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel, ScoreBadge, StatRow, UrgencyBadge } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, Signal, SignalCluster } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type UrgencyFilter = 'all' | 'high' | 'medium' | 'low';

export default function NicheFindingsPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [urgency, setUrgency] = useState<UrgencyFilter>('all');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedQuery(value), 150);
  };

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [marketsRes, signalsRes, clustersRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getSignals({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
      ]);
      setNiche(marketsRes.markets.find(market => market.id === marketId) ?? null);
      setSignals(signalsRes.signals);
      setClusters(clustersRes.clusters);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load findings');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const themeBySignalId = useMemo(() => {
    const map = new Map<string, SignalCluster>();
    clusters.forEach(cluster => cluster.signal_ids.forEach(id => map.set(id, cluster)));
    return map;
  }, [clusters]);

  const filtered = signals.filter(signal => {
    if (urgency !== 'all' && signal.urgency !== urgency) return false;
    if (!debouncedQuery.trim()) return true;
    const haystack = [
      signal.pain,
      signal.job_to_be_done,
      signal.evidence_text,
      signal.category,
      signal.competitor_name,
      signal.user_type,
    ].filter(Boolean).join(' ').toLowerCase();
    return haystack.includes(debouncedQuery.trim().toLowerCase());
  });

  const highUrgency = signals.filter(signal => signal.urgency === 'high').length;

  return (
    <DashboardShell
      title="Findings"
      subtitle={`${niche?.name ?? 'This niche'} raw evidence that feeds themes and gaps.`}
      actions={<NicheViewSwitcher marketId={marketId} active="findings" onRefresh={load} refreshing={status === 'loading'} />}
    >
      {status === 'loading' && <LoadingPanel label="Loading findings" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <div className="flex flex-wrap items-center gap-3">
            <StatRow compact stats={[
              { label: 'Findings', value: signals.length },
              { label: 'High urgency', value: highUrgency, accent: highUrgency > 0 },
              { label: 'Themes linked', value: clusters.length },
            ]} />
            <div className="flex items-center gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1">
              {(['all', 'high', 'medium', 'low'] as const).map(filter => (
                <button
                  key={filter}
                  onClick={() => setUrgency(filter)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition ${urgency === filter ? 'bg-slate-700 text-slate-100 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                >
                  {filter}
                </button>
              ))}
            </div>
            <div className="relative ml-auto">
              <svg className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
              </svg>
              <input
                value={query}
                onChange={event => handleQueryChange(event.target.value)}
                placeholder="Search findings…"
                className="min-w-[180px] rounded-lg border border-slate-700/70 bg-slate-900/60 py-2 pl-8 pr-3 text-sm text-slate-300 outline-none placeholder:text-slate-600 focus:border-violet-500/40"
              />
            </div>
          </div>

          {filtered.length === 0 ? (
            <EmptyPanel title="No findings match this view" detail="Adjust the filters or wait for the next background scan." />
          ) : (
            <div className="space-y-3">
              {filtered.map(signal => {
                const theme = themeBySignalId.get(signal.id);
                return (
                  <article key={signal.id} className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h2 className="font-semibold leading-snug text-slate-100">{signal.pain}</h2>
                        {signal.job_to_be_done && <p className="mt-1 text-sm text-slate-500">{signal.job_to_be_done}</p>}
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <UrgencyBadge urgency={signal.urgency} />
                        <ScoreBadge value={signal.confidence} />
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {theme && <ClusterLink id={theme.id} marketId={marketId}>{theme.theme}</ClusterLink>}
                      {signal.competitor_name && <Chip label={signal.competitor_name} />}
                      {signal.category && <Chip label={signal.category} />}
                      {signal.user_type && <Chip label={signal.user_type} />}
                    </div>

                    {signal.current_workaround && (
                      <p className="mt-3 text-xs text-slate-500">
                        Workaround: <span className="text-slate-400">{signal.current_workaround}</span>
                      </p>
                    )}

                    {signal.evidence_text && (
                      <p className="mt-3 rounded-lg bg-slate-950/35 px-3 py-2 text-xs leading-relaxed text-slate-500">{signal.evidence_text}</p>
                    )}

                    {signal.evidence_url && (
                      <a href={signal.evidence_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-xs font-medium text-violet-400 transition hover:text-violet-300">
                        Open evidence source
                      </a>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

