'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel, Metric } from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Opportunity, SignalCluster } from '@/lib/types/signals';

type Status = 'loading' | 'ready' | 'error';

type SignalStrength = { label: string; cls: string; dotCls: string };

function signalStrength(confidence: number): SignalStrength {
  if (confidence >= 0.7)
    return {
      label: 'Strong signal',
      cls: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400',
      dotCls: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]',
    };
  if (confidence >= 0.4)
    return {
      label: 'Moderate signal',
      cls: 'border-amber-500/25 bg-amber-500/10 text-amber-400',
      dotCls: 'bg-amber-400',
    };
  return {
    label: 'Weak signal',
    cls: 'border-slate-700/50 bg-slate-800/60 text-slate-500',
    dotCls: 'bg-slate-600',
  };
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

export default function GapsPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [oppsRes, clustersRes] = await Promise.all([
        signalApi.getOpportunities(),
        signalApi.getClusters(),
      ]);
      setOpportunities(oppsRes.opportunities);
      setClusters(clustersRes.clusters);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load gaps');
      setStatus('error');
    }
  };

  useEffect(() => { load(); }, []);

  const clusterById = useMemo(() => {
    const m = new Map<string, SignalCluster>();
    clusters.forEach(c => m.set(c.id, c));
    return m;
  }, [clusters]);

  const strongCount = opportunities.filter(o => o.confidence >= 0.7).length;
  const totalEvidence = opportunities.reduce((sum, o) => sum + o.evidence_count, 0);

  return (
    <DashboardShell
      title="Gaps"
      subtitle="Product gaps identified from competitor complaints and user feedback"
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
      {status === 'loading' && <LoadingPanel label="Loading gaps" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Gaps identified" value={opportunities.length} />
            <Metric label="Strong signals" value={strongCount} accent={strongCount > 0} />
            <Metric label="Evidence items" value={totalEvidence} />
          </div>

          {opportunities.length === 0 ? (
            <EmptyPanel
              title="No gaps identified yet"
              detail="Gaps appear after active sources are scanned in the background."
            />
          ) : (
            <div className="space-y-3">
              {opportunities.map((opp, i) => (
                <GapCard
                  key={opp.id}
                  rank={i + 1}
                  opportunity={opp}
                  strength={signalStrength(opp.confidence)}
                  theme={opp.cluster_id ? clusterById.get(opp.cluster_id) : undefined}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

function GapCard({
  rank,
  opportunity,
  strength,
  theme,
}: {
  rank: number;
  opportunity: Opportunity;
  strength: SignalStrength;
  theme?: SignalCluster;
}) {
  return (
    <div className="rounded-xl border border-slate-800/70 bg-slate-900/40 px-5 py-4 transition-colors hover:border-slate-700/80">
      <div className="flex items-start gap-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-bold tabular-nums text-slate-500">
          {rank}
        </div>

        <div className="min-w-0 flex-1">
          {/* Header row */}
          <div className="mb-2.5 flex flex-wrap items-start justify-between gap-3">
            <h3 className="font-semibold leading-snug text-slate-100">{opportunity.title}</h3>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${strength.cls}`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${strength.dotCls}`} />
                {strength.label}
              </span>
              <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                {opportunity.evidence_count} evidence
              </span>
              {theme && (
                <ClusterLink id={theme.id}>{theme.theme}</ClusterLink>
              )}
            </div>
          </div>

          {/* Pain summary */}
          {opportunity.pain_summary && (
            <p className="mb-3 text-sm leading-relaxed text-slate-400">
              {opportunity.pain_summary}
            </p>
          )}

          {/* Detail cells */}
          <div className="grid gap-2 sm:grid-cols-2">
            {opportunity.target_user && (
              <div className="rounded-lg border border-slate-800/50 bg-slate-800/20 px-3 py-2">
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">
                  Affected user
                </p>
                <p className="text-xs text-slate-400">{opportunity.target_user}</p>
              </div>
            )}
            {opportunity.suggested_wedge && (
              <div className="rounded-lg border border-violet-500/15 bg-violet-500/[0.04] px-3 py-2">
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">
                  Suggested wedge
                </p>
                <p className="text-xs text-violet-300">{opportunity.suggested_wedge}</p>
              </div>
            )}
          </div>

          {opportunity.why_it_matters && (
            <p className="mt-2.5 text-xs leading-relaxed text-slate-600">
              {opportunity.why_it_matters}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
