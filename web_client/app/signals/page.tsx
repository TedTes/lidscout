'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import {
  ClusterLink,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
} from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Signal, SignalCluster } from '@/lib/types/signals';

type Status = 'idle' | 'loading' | 'ready' | 'error';

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

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
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filteredSignals = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return signals;

    return signals.filter(signal =>
      [
        signal.pain,
        signal.category,
        signal.user_type,
        signal.job_to_be_done,
        signal.current_workaround,
      ]
        .filter(Boolean)
        .some(value => value!.toLowerCase().includes(normalized))
    );
  }, [signals, query]);

  const clusterBySignalId = useMemo(() => {
    const lookup = new Map<string, SignalCluster>();
    clusters.forEach(cluster => {
      cluster.signal_ids.forEach(signalId => lookup.set(signalId, cluster));
    });
    return lookup;
  }, [clusters]);

  return (
    <DashboardShell
      title="Signals"
      subtitle="Extracted market and product signals from online activity"
      actions={
        <button
          onClick={load}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:border-sky-300 hover:text-sky-700"
        >
          Refresh
        </button>
      }
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Signals" value={signals.length} />
        <Metric label="Clusters" value={clusters.length} />
        <Metric
          label="High urgency"
          value={signals.filter(signal => signal.urgency === 'high').length}
        />
      </div>

      <div className="mt-5 rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Signal list</h2>
          <input
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Filter signals"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 sm:max-w-xs"
          />
        </div>

        <div className="p-4">
          {status === 'loading' && <LoadingPanel label="Loading signals" />}
          {status === 'error' && error && <ErrorPanel message={error} />}
          {status === 'ready' && filteredSignals.length === 0 && (
            <EmptyPanel title="No signals found" detail="Run the pipeline to populate this list." />
          )}
          {filteredSignals.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100 text-sm">
                <thead>
                  <tr className="text-left text-xs font-semibold uppercase text-gray-400">
                    <th className="px-3 py-2">Pain</th>
                    <th className="px-3 py-2">Category</th>
                    <th className="px-3 py-2">Urgency</th>
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2">Confidence</th>
                    <th className="px-3 py-2">Cluster</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredSignals.map(signal => {
                    const cluster = clusterBySignalId.get(signal.id);
                    return (
                      <tr key={signal.id} className="align-top">
                        <td className="max-w-md px-3 py-3 font-medium text-gray-900">
                          {signal.pain}
                          {signal.job_to_be_done && (
                            <p className="mt-1 text-xs font-normal text-gray-500">
                              {signal.job_to_be_done}
                            </p>
                          )}
                        </td>
                        <td className="px-3 py-3 text-gray-600">{signal.category || 'Uncategorized'}</td>
                        <td className="px-3 py-3 capitalize text-gray-700">{signal.urgency}</td>
                        <td className="px-3 py-3 capitalize text-gray-700">{signal.severity}</td>
                        <td className="px-3 py-3">
                          <ScoreBadge value={signal.confidence * 10} />
                        </td>
                        <td className="px-3 py-3">
                          {cluster ? (
                            <ClusterLink id={cluster.id}>{cluster.theme}</ClusterLink>
                          ) : (
                            <span className="text-gray-400">Unclustered</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}
