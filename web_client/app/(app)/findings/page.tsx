'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardShell from '@/components/app/DashboardShell';
import {
  Chip,
  ClusterLink,
  CompanyFilterBanner,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  UrgencyBadge,
} from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Signal, SignalCluster } from '@/lib/types/signals';

type Status = 'idle' | 'loading' | 'ready' | 'error';

function urgencyBarColor(urgency: Signal['urgency']) {
  return { high: 'bg-rose-500', medium: 'bg-amber-500', low: 'bg-slate-700' }[urgency];
}

function FilterIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

export default function FindingsPage() {
  const searchParams = useSearchParams();
  const companyId = searchParams.get('company') ?? undefined;

  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const load = async () => {
    setStatus('loading');
    setError(null);
    const filter = companyId ? { competitor_id: companyId } : undefined;
    try {
      const [signalsData, clustersData] = await Promise.all([
        signalApi.getSignals(filter),
        signalApi.getClusters(filter),
      ]);
      setSignals(signalsData.signals);
      setClusters(clustersData.clusters);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load findings');
      setStatus('error');
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [companyId]);

  const clusterBySignalId = useMemo(() => {
    const map = new Map<string, SignalCluster>();
    clusters.forEach(cluster => {
      cluster.signal_ids.forEach(id => map.set(id, cluster));
    });
    return map;
  }, [clusters]);

  const filteredSignals = useMemo(() => {
    let result = signals;
    if (urgencyFilter !== 'all') result = result.filter(s => s.urgency === urgencyFilter);
    const q = query.trim().toLowerCase();
    if (q) {
      result = result.filter(s =>
        [s.pain, s.category, s.user_type, s.job_to_be_done, s.current_workaround, s.evidence_text]
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
      title="Findings"
      subtitle="Evidence extracted from monitored sources — raw input behind Gaps and Themes"
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
      {companyId && <CompanyFilterBanner companyId={companyId} />}

      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Findings" value={signals.length} />
        <Metric label="High urgency" value={highCount} accent={highCount > 0} />
        <Metric label="Themes" value={clusters.length} />
      </div>

      <div className="mt-5 rounded-xl border border-slate-800/80 bg-slate-900/40">
        {/* Toolbar */}
        <div className="flex flex-col gap-3 border-b border-slate-800/80 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-200">Finding list</h2>
            {status === 'ready' && (
              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                {filteredSignals.length}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
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

            <div className="relative">
              <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600">
                <FilterIcon />
              </span>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Filter findings…"
                className="w-full rounded-lg border border-slate-700/80 bg-slate-800/60 py-2 pl-8 pr-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10 sm:w-52"
              />
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-3">
          {status === 'loading' && <LoadingPanel label="Loading findings" />}
          {status === 'error' && error && <ErrorPanel message={error} />}
          {status === 'ready' && filteredSignals.length === 0 && (
            <EmptyPanel
              title="No findings found"
              detail="Findings appear after active sources are scanned, or clear your filters."
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
                    <div className={`w-1 shrink-0 ${urgencyBarColor(signal.urgency)}`} />

                    <div className="flex-1 px-4 py-3.5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium leading-snug text-slate-200">{signal.pain}</p>
                          {signal.job_to_be_done && (
                            <p className="mt-1 text-xs leading-relaxed text-slate-500">
                              {signal.job_to_be_done}
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                          {!companyId && signal.competitor_id && (
                            <span className="rounded-md bg-slate-800/60 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                              {signal.competitor_id.split('-').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                            </span>
                          )}
                          {cluster && (
                            <ClusterLink id={cluster.id}>{cluster.theme}</ClusterLink>
                          )}
                        </div>
                      </div>

                      {/* Evidence text */}
                      {signal.evidence_text && (
                        <p className="mt-2 rounded-md border border-slate-800/60 bg-slate-800/30 px-3 py-2 text-xs leading-relaxed text-slate-500 italic">
                          &ldquo;{signal.evidence_text}&rdquo;
                        </p>
                      )}

                      {/* Tags + source */}
                      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                        <UrgencyBadge urgency={signal.urgency} />
                        {signal.category && <Chip label={signal.category} />}
                        {signal.user_type && <Chip label={signal.user_type} />}
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
                        {signal.evidence_url && (
                          <a
                            href={signal.evidence_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ml-auto inline-flex items-center gap-1 rounded-md bg-slate-800/50 px-2 py-0.5 text-xs text-slate-600 transition hover:text-slate-400"
                          >
                            <LinkIcon />
                            Source
                          </a>
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

      {wtpCount > 0 && status === 'ready' && (
        <div className="mt-4 flex items-center gap-3 rounded-xl border border-emerald-500/15 bg-emerald-500/[0.04] px-4 py-3">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_7px_rgba(52,211,153,0.8)]" />
          <p className="text-xs text-slate-400">
            <span className="font-semibold text-emerald-400">{wtpCount}</span>
            {wtpCount === 1 ? ' finding indicates' : ' findings indicate'} willingness to pay
          </p>
        </div>
      )}
    </DashboardShell>
  );
}
