'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import {
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
} from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Signal, SignalCluster } from '@/lib/types/signals';

type Props = {
  params: {
    clusterId: string;
  };
};

type Status = 'loading' | 'ready' | 'error';

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

  const cluster = clusters.find(item => item.id === decodeURIComponent(params.clusterId));
  const relatedSignals = useMemo(() => {
    if (!cluster) return [];
    const ids = new Set(cluster.signal_ids);
    return signals.filter(signal => ids.has(signal.id));
  }, [cluster, signals]);

  return (
    <DashboardShell
      title={cluster?.theme || 'Cluster detail'}
      subtitle={cluster?.summary}
      actions={
        <Link
          href="/signals"
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:border-sky-300 hover:text-sky-700"
        >
          Signals
        </Link>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading cluster" />}
      {status === 'error' && error && <ErrorPanel message={error} />}
      {status === 'ready' && !cluster && (
        <EmptyPanel title="Cluster not found" detail="The cluster may no longer exist in the latest dataset." />
      )}
      {cluster && (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Frequency" value={cluster.frequency} />
            <Metric label="Signals" value={cluster.signal_ids.length} />
            <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
              <p className="text-xs font-medium uppercase text-gray-400">Average score</p>
              <div className="mt-2">
                <ScoreBadge value={cluster.average_score} />
              </div>
            </div>
          </div>

          <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900">Top examples</h2>
            {cluster.top_examples.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">No examples saved for this cluster.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {cluster.top_examples.map((example, index) => (
                  <p key={index} className="rounded-md bg-gray-50 px-3 py-2 text-sm leading-6 text-gray-700">
                    {example}
                  </p>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900">Related signals</h2>
            {relatedSignals.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">No related signals are currently available.</p>
            ) : (
              <div className="mt-3 divide-y divide-gray-100">
                {relatedSignals.map(signal => (
                  <div key={signal.id} className="py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-gray-900">{signal.pain}</p>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                        {signal.urgency}
                      </span>
                      {signal.category && (
                        <span className="rounded-full bg-sky-50 px-2 py-0.5 text-xs text-sky-700">
                          {signal.category}
                        </span>
                      )}
                    </div>
                    {signal.current_workaround && (
                      <p className="mt-1 text-sm text-gray-500">{signal.current_workaround}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}
