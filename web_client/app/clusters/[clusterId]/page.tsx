'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import {
  Chip,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
  SectionCard,
  UrgencyBadge,
} from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Signal, SignalCluster } from '@/lib/types/signals';

type Props = { params: { clusterId: string } };
type Status = 'loading' | 'ready' | 'error';

function BackIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

export default function ClusterDetailPage({ params }: Props) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setStatus('loading');
      setError(null);
      try {
        const [signalsData, clustersData] = await Promise.all([
          signalApi.getSignals(),
          signalApi.getClusters(),
        ]);
        setSignals(signalsData.signals);
        setClusters(clustersData.clusters);
        setStatus('ready');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load cluster');
        setStatus('error');
      }
    };
    load();
  }, []);

  const cluster = clusters.find(c => c.id === decodeURIComponent(params.clusterId));

  const relatedSignals = useMemo(() => {
    if (!cluster) return [];
    const ids = new Set(cluster.signal_ids);
    return signals.filter(s => ids.has(s.id));
  }, [cluster, signals]);

  return (
    <DashboardShell
      title={cluster?.theme ?? 'Cluster detail'}
      subtitle={cluster?.summary}
      actions={
        <Link
          href="/signals"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-800/60 px-3 py-2 text-xs font-semibold text-slate-300 shadow-sm transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100"
        >
          <BackIcon />
          All signals
        </Link>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading cluster" />}
      {status === 'error' && error && <ErrorPanel message={error} />}
      {status === 'ready' && !cluster && (
        <EmptyPanel
          title="Cluster not found"
          detail="The cluster may no longer exist in the latest dataset."
        />
      )}

      {cluster && (
        <div className="space-y-5 animate-fade-in">
          {/* Stats row */}
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Mentions" value={cluster.frequency} />
            <Metric label="Signals" value={cluster.signal_ids.length} />
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">
                Avg score
              </p>
              <div className="mt-2.5">
                <ScoreBadge value={cluster.average_score} />
              </div>
            </div>
          </div>

          {/* Top examples */}
          <SectionCard title="Top examples">
            {cluster.top_examples.length === 0 ? (
              <p className="text-sm text-slate-600">No examples saved for this cluster.</p>
            ) : (
              <div className="space-y-2">
                {cluster.top_examples.map((example, i) => (
                  <div
                    key={i}
                    className="flex gap-3 rounded-lg border border-slate-800/60 bg-slate-800/30 px-4 py-3"
                  >
                    <span className="mt-0.5 shrink-0 text-xs font-bold tabular-nums text-slate-700">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <p className="text-sm leading-relaxed text-slate-400">{example}</p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          {/* Related signals */}
          <SectionCard title={`Related signals (${relatedSignals.length})`}>
            {relatedSignals.length === 0 ? (
              <p className="text-sm text-slate-600">No related signals currently available.</p>
            ) : (
              <div className="space-y-2">
                {relatedSignals.map(signal => (
                  <div
                    key={signal.id}
                    className="flex overflow-hidden rounded-lg border border-slate-800/60 transition-colors hover:border-slate-700/80"
                  >
                    {/* Urgency bar */}
                    <div
                      className={`w-0.5 shrink-0 ${
                        signal.urgency === 'high'
                          ? 'bg-rose-500'
                          : signal.urgency === 'medium'
                            ? 'bg-amber-500'
                            : 'bg-slate-700'
                      }`}
                    />
                    <div className="flex-1 px-4 py-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <p className="font-medium leading-snug text-slate-200">{signal.pain}</p>
                        <ScoreBadge value={signal.confidence * 10} />
                      </div>
                      {signal.current_workaround && (
                        <p className="mt-1 text-xs text-slate-500">
                          ↪ {signal.current_workaround}
                        </p>
                      )}
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <UrgencyBadge urgency={signal.urgency} />
                        {signal.category && <Chip label={signal.category} />}
                        {signal.user_type && <Chip label={signal.user_type} />}
                        {signal.willingness_to_pay && (
                          <span className="rounded-md border border-emerald-500/20 bg-emerald-500/[0.07] px-2 py-0.5 text-xs font-medium text-emerald-400">
                            WTP
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}
    </DashboardShell>
  );
}
