'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, Opportunity, SignalCluster } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type Tier = 'strong' | 'moderate' | 'weak';

const TIER_META: Record<Tier, { label: string; dotCls: string; badgeCls: string }> = {
  strong: { label: 'Strong signal', dotCls: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]', badgeCls: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400' },
  moderate: { label: 'Moderate signal', dotCls: 'bg-amber-400', badgeCls: 'border-amber-500/25 bg-amber-500/10 text-amber-400' },
  weak: { label: 'Weak signal', dotCls: 'bg-slate-600', badgeCls: 'border-slate-700/50 bg-slate-800/60 text-slate-500' },
};

function opportunityTier(confidence: number): Tier {
  if (confidence >= 0.7) return 'strong';
  if (confidence >= 0.4) return 'moderate';
  return 'weak';
}

function IconBookmark({ filled }: { filled?: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function loadSet(key: string): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    return new Set(JSON.parse(localStorage.getItem(key) ?? '[]'));
  } catch {
    return new Set();
  }
}

function saveSet(key: string, value: Set<string>) {
  localStorage.setItem(key, JSON.stringify([...value]));
}

function fallbackTitleFromId(id: string) {
  return id
    .split(/[-_]/)
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export default function NicheWorkspacePage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [gapFilter, setGapFilter] = useState<'all' | 'saved' | 'dismissed'>('all');
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setSavedIds(loadSet('lidscout_saved_gaps'));
    setDismissedIds(loadSet('lidscout_dismissed_gaps'));
  }, []);

  const load = async () => {
    setStatus('loading');
    setError(null);
    setNiche(null);
    try {
      const [marketsRes, oppsRes, clustersRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getOpportunities({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
      ]);
      setNiche(marketsRes.markets.find(market => market.id === marketId) ?? null);
      setOpportunities(oppsRes.opportunities);
      setClusters(clustersRes.clusters);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load niche');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const clusterById = useMemo(() => new Map(clusters.map(cluster => [cluster.id, cluster])), [clusters]);
  const filteredOpportunities = opportunities.filter(opportunity => {
    if (gapFilter === 'saved') return savedIds.has(opportunity.id);
    if (gapFilter === 'dismissed') return dismissedIds.has(opportunity.id);
    return !dismissedIds.has(opportunity.id);
  });
  const strongCount = opportunities.filter(opportunity => opportunity.confidence >= 0.7).length;
  const evidenceCount = opportunities.reduce((sum, opportunity) => sum + opportunity.evidence_count, 0);
  const title = niche?.name ?? (status === 'loading' ? '' : fallbackTitleFromId(marketId));

  const toggleSave = (id: string) => {
    setSavedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      saveSet('lidscout_saved_gaps', next);
      return next;
    });
    setDismissedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      saveSet('lidscout_dismissed_gaps', next);
      return next;
    });
  };

  const toggleDismiss = (id: string) => {
    setDismissedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      saveSet('lidscout_dismissed_gaps', next);
      return next;
    });
    setSavedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      saveSet('lidscout_saved_gaps', next);
      return next;
    });
  };

  return (
    <DashboardShell
      title={title}
      subtitle={niche?.description ?? 'Ranked product gaps backed by public evidence.'}
      actions={
        <NicheViewSwitcher marketId={marketId} active="gaps" />
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading gaps" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid gap-3 sm:grid-cols-3">
            <Summary label="Gaps identified" value={opportunities.length} accent={opportunities.length > 0} />
            <Summary label="Strong signals" value={strongCount} accent={strongCount > 0} />
            <Summary label="Evidence items" value={evidenceCount} />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1">
              {(['all', 'saved', 'dismissed'] as const).map(filter => (
                <button
                  key={filter}
                  onClick={() => setGapFilter(filter)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition ${gapFilter === filter ? 'bg-slate-700 text-slate-100 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          {filteredOpportunities.length === 0 ? (
            <EmptyPanel
              title={gapFilter === 'all' ? 'No gaps identified yet' : `No ${gapFilter} gaps`}
              detail={gapFilter === 'all' ? 'Gaps appear after active sources are scanned in the background.' : undefined}
            />
          ) : (
            <div className="space-y-3">
              {filteredOpportunities
                .slice()
                .sort((a, b) => b.evidence_count - a.evidence_count)
                .map((opportunity, index) => (
                  <GapCard
                    key={opportunity.id}
                    rank={index + 1}
                    opportunity={opportunity}
                    marketId={marketId}
                    theme={opportunity.cluster_id ? clusterById.get(opportunity.cluster_id) : undefined}
                    meta={TIER_META[opportunityTier(opportunity.confidence)]}
                    saved={savedIds.has(opportunity.id)}
                    dismissed={dismissedIds.has(opportunity.id)}
                    onSave={() => toggleSave(opportunity.id)}
                    onDismiss={() => toggleDismiss(opportunity.id)}
                  />
                ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

function Summary({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`rounded-xl border px-5 py-4 ${accent ? 'border-violet-500/20 bg-violet-600/[0.08]' : 'border-slate-800/80 bg-slate-900/50'}`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${accent ? 'text-violet-300' : 'text-slate-100'}`}>
        {value}
      </p>
    </div>
  );
}

function GapCard({
  rank,
  opportunity,
  marketId,
  theme,
  meta,
  saved,
  dismissed,
  onSave,
  onDismiss,
}: {
  rank: number;
  opportunity: Opportunity;
  marketId: string;
  theme?: SignalCluster;
  meta: typeof TIER_META['strong'];
  saved: boolean;
  dismissed: boolean;
  onSave: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className={`rounded-xl border bg-slate-900/40 px-5 py-4 transition-colors hover:border-slate-700/80 ${dismissed ? 'border-slate-800/40 opacity-50' : 'border-slate-800/70'}`}>
      <div className="flex items-start gap-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-bold tabular-nums text-slate-500">
          {rank}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
            <h3 className="font-semibold leading-snug text-slate-100">{opportunity.title}</h3>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${meta.badgeCls}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dotCls}`} />
                {meta.label}
              </span>
              <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                {opportunity.evidence_count} evidence
              </span>
              {theme && <ClusterLink id={theme.id} marketId={marketId}>{theme.theme}</ClusterLink>}
            </div>
          </div>

          {opportunity.pain_summary && (
            <p className="mb-3 text-sm leading-relaxed text-slate-400">{opportunity.pain_summary}</p>
          )}

          <div className="grid gap-2 sm:grid-cols-2">
            {opportunity.target_user && (
              <div className="rounded-lg border border-slate-800/50 bg-slate-800/20 px-3 py-2">
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Affected user</p>
                <p className="text-xs text-slate-400">{opportunity.target_user}</p>
              </div>
            )}
            {opportunity.suggested_wedge && (
              <div className="rounded-lg border border-violet-500/15 bg-violet-500/[0.04] px-3 py-2">
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Suggested wedge</p>
                <p className="text-xs text-violet-300">{opportunity.suggested_wedge}</p>
              </div>
            )}
          </div>

          {opportunity.company_count > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-xs text-slate-600">
                Across <span className="font-medium text-slate-400">{opportunity.company_count}</span>
                {opportunity.market_company_count != null && <> of <span className="font-medium text-slate-400">{opportunity.market_company_count}</span></>}{' '}
                {opportunity.company_count === 1 ? 'company' : 'companies'}
              </span>
              {opportunity.company_names.slice(0, 4).map(name => (
                <span key={name} className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">{name}</span>
              ))}
            </div>
          )}

          {opportunity.why_it_matters && (
            <p className="mt-2.5 text-xs leading-relaxed text-slate-500">{opportunity.why_it_matters}</p>
          )}

          <div className="mt-3 flex items-center gap-2 border-t border-slate-800/50 pt-3">
            <button
              onClick={onSave}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition ${saved ? 'border-violet-500/30 bg-violet-500/10 text-violet-400' : 'border-slate-700/50 text-slate-600 hover:border-slate-600 hover:text-slate-400'}`}
            >
              <IconBookmark filled={saved} />
              {saved ? 'Saved' : 'Save'}
            </button>
            <button
              onClick={onDismiss}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition ${dismissed ? 'border-slate-600 text-slate-400' : 'border-slate-700/50 text-slate-700 hover:border-slate-600 hover:text-slate-500'}`}
            >
              <IconX />
              {dismissed ? 'Dismissed' : 'Dismiss'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
