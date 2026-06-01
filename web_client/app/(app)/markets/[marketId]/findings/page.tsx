'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel, ScoreBadge, UrgencyBadge } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, Signal, SignalCluster } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

export default function NicheFindingsPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, signalsRes, clustersRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getSignals({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
      ]);
      setNiche(market);
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
          {signals.length === 0 ? (
            <EmptyPanel title="No findings yet" detail="Findings appear after the next background scan extracts evidence." />
          ) : (
            <div className="space-y-3">
              {signals.map(signal => {
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
                      {signal.company_name && <Chip label={signal.company_name} />}
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
