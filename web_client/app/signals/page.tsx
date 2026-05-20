'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import {
  Chip,
  ClusterLink,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
  UrgencyBadge,
} from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Signal, SignalCluster } from '@/lib/types/signals';

type Status = 'idle' | 'loading' | 'ready' | 'error';

function urgencyBarColor(urgency: Signal['urgency']) {
  return {
    high: 'bg-rose-500',
    medium: 'bg-amber-500',
    low: 'bg-slate-700',
  }[urgency];
}

function FilterIcon() {
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
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

function RefreshIcon() {
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
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');

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
      setError(err instanceof Error ? err.message : 'Failed to load signals');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
  }, []);

  const clusterBySignalId = useMemo(() => {
    const map = new Map<string, SignalCluster>();
    clusters.forEach(cluster => {
      cluster.signal_ids.forEach(id => map.set(id, cluster));
    });
    return map;
  }, [clusters]);

  const filteredSignals = useMemo(() => {
    let result = signals;
    if (urgencyFilter !== 'all') {
      result = result.filter(s => s.urgency === urgencyFilter);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      result = result.filter(s =>
        [s.pain, s.category, s.user_type, s.job_to_be_done, s.current_workaround]
          .filter(Boolean)
          .some(v => v!.toLowerCase().includes(q)),
      );
    }
    return result;
  }, [signals, query, urgencyFilter]);

  const highCount = signals.filter(s => s.urgency === 'high').length;
  const wtpCount = signals.filter(s => s.willingness_to_pay).length;

  return (
    <DashboardShell
      title="Signals"
      subtitle="Extracted market and pain signals from online activity"
      actions={
        <button
          onClick={load}
          disabled={status === 'loading'}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-800/60 px-3 py-2 text-xs font-semibold text-slate-300 shadow-sm transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100 disabled:opacity-50"
        >
          <RefreshIcon />
          Refresh
        </button>
      }
    >
      {/* Metrics row */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Total signals" value={signals.length} />
        <Metric label="High urgency" value={highCount} accent={highCount > 0} />
        <Metric label="Clusters" value={clusters.length} />
      </div>

      {/* Signal list */}
      <div className="mt-5 rounded-xl border border-slate-800/80 bg-slate-900/40">
        {/* Toolbar */}
        <div className="flex flex-col gap-3 border-b border-slate-800/80 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-200">Signal list</h2>
            {status === 'ready' && (
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                {filteredSignals.length}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Urgency filter chips */}
            <div className="flex items-center gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1">
              {(['all', 'high', 'medium', 'low'] as const).map(level => (
                <button
                  key={level}
                  onClick={() => setUrgencyFilter(level)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition ${
                    urgencyFilter === level
                      ? 'bg-slate-700 text-slate-100 shadow-sm'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {level === 'all' ? 'All' : level}
                </button>
              ))}
            </div>

            {/* Search */}
            <div className="relative">
              <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600">
                <FilterIcon />
              </span>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Filter signals…"
                className="w-full rounded-lg border border-slate-700/80 bg-slate-800/60 py-2 pl-8 pr-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10 sm:w-52"
              />
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-3">
          {status === 'loading' && <LoadingPanel label="Loading signals" />}
          {status === 'error' && error && <ErrorPanel message={error} />}
          {status === 'ready' && filteredSignals.length === 0 && (
            <EmptyPanel
              title="No signals found"
              detail="Run the pipeline to populate this list, or clear your filters."
            />
          )}

          {filteredSignals.length > 0 && (
            <div className="space-y-2">
              {filteredSignals.map(signal => {
                const cluster = clusterBySignalId.get(signal.id);
                return (
                  <div
                    key={signal.id}
                    className="group flex overflow-hidden rounded-xl border border-slate-800/70 transition-colors hover:border-slate-700/80 hover:bg-white/[0.01]"
                  >
                    {/* Urgency left bar */}
                    <div className={`w-1 shrink-0 ${urgencyBarColor(signal.urgency)}`} />

                    {/* Content */}
                    <div className="flex-1 px-4 py-3.5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium leading-snug text-slate-200">
                            {signal.pain}
                          </p>
                          {signal.job_to_be_done && (
                            <p className="mt-1 text-xs leading-relaxed text-slate-500">
                              {signal.job_to_be_done}
                            </p>
                          )}
                        </div>

                        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                          <ScoreBadge value={signal.confidence * 10} />
                          {cluster && (
                            <ClusterLink id={cluster.id}>{cluster.theme}</ClusterLink>
                          )}
                        </div>
                      </div>

                      {/* Tags row */}
                      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                        <UrgencyBadge urgency={signal.urgency} />
                        {signal.category && <Chip label={signal.category} />}
                        {signal.user_type && (
                          <Chip label={signal.user_type} />
                        )}
                        {signal.current_workaround && (
                          <span className="rounded-md bg-slate-800/50 px-2 py-0.5 text-xs text-slate-600">
                            ↪ {signal.current_workaround}
                          </span>
                        )}
                        {signal.willingness_to_pay && (
                          <span className="rounded-md border border-emerald-500/20 bg-emerald-500/[0.07] px-2 py-0.5 text-xs font-medium text-emerald-400">
                            WTP
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* WTP callout */}
      {wtpCount > 0 && status === 'ready' && (
        <div className="mt-4 flex items-center gap-3 rounded-xl border border-emerald-500/15 bg-emerald-500/[0.04] px-4 py-3">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_7px_rgba(52,211,153,0.8)]" />
          <p className="text-xs text-slate-400">
            <span className="font-semibold text-emerald-400">{wtpCount}</span>
            {wtpCount === 1 ? ' signal indicates' : ' signals indicate'} willingness to pay
          </p>
        </div>
      )}
    </DashboardShell>
  );
}
