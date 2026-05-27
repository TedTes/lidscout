'use client';

import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel, StatRow } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import {
  AgentColdStartPlan,
  AgentFeedbackAction,
  Competitor,
  Market,
  MonitoredSource,
  Opportunity,
  SignalCluster,
} from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type Tier = 'strong' | 'moderate' | 'weak';
type GapFilter = 'all' | 'saved' | 'dismissed';
type ItemFeedbackAction = Extract<AgentFeedbackAction, 'save' | 'dismiss'>;
type TrainingFeedbackAction = Extract<AgentFeedbackAction, 'more_like_this' | 'less_like_this'>;

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

function fallbackTitleFromId(id: string) {
  return id.split(/[-_]/).filter(Boolean).map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
}

function isItemFeedbackAction(action: AgentFeedbackAction): action is ItemFeedbackAction {
  return action === 'save' || action === 'dismiss';
}

function isTrainingFeedbackAction(action: AgentFeedbackAction): action is TrainingFeedbackAction {
  return action === 'more_like_this' || action === 'less_like_this';
}

// ── Icons ──────────────────────────────────────────────────────────────────────

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

function IconThumbUp() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function IconThumbDown() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    </svg>
  );
}


// ── Main page ──────────────────────────────────────────────────────────────────

export default function NicheWorkspacePage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [coldStart, setColdStart] = useState<AgentColdStartPlan | null>(null);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [sources, setSources] = useState<MonitoredSource[]>([]);
  const [nextScanAt, setNextScanAt] = useState<string | null>(null);
  const [showBrief, setShowBrief] = useState(false);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [gapFilter, setGapFilter] = useState<GapFilter>('all');
  const [itemFeedbackMap, setItemFeedbackMap] = useState<Map<string, ItemFeedbackAction>>(new Map());
  const [trainingFeedbackMap, setTrainingFeedbackMap] = useState<Map<string, TrainingFeedbackAction>>(new Map());

  const load = async () => {
    setStatus('loading');
    setError(null);
    setFeedbackError(null);
    setNiche(null);
    setColdStart(null);
    setCompetitors([]);
    setSources([]);
    setNextScanAt(null);
    setItemFeedbackMap(new Map());
    setTrainingFeedbackMap(new Map());
    try {
      const [market, oppsRes, clustersRes, coldStartRes, feedbackRes, competitorsRes, sourcesRes, scheduleRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getOpportunities({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
        signalApi.getMarketAgentColdStart(marketId).catch(() => null),
        signalApi.getMarketAgentFeedback(marketId).catch(() => null),
        signalApi.getMarketCompetitors(marketId).catch(() => null),
        signalApi.getMarketSources(marketId).catch(() => null),
        signalApi.getPipelineSchedule().catch(() => null),
      ]);
      setNiche(market);
      setOpportunities(oppsRes.opportunities);
      setClusters(clustersRes.clusters);
      setColdStart(coldStartRes);
      setCompetitors(competitorsRes?.competitors ?? []);
      setSources(sourcesRes?.sources ?? []);
      setNextScanAt(scheduleRes?.next_run_at ?? null);
      setShowBrief(coldStartRes !== null && coldStartRes.status === 'setup_needed');

      if (feedbackRes?.feedback) {
        // Take latest action per opportunity (sort asc by created_at, last wins)
        const sorted = [...feedbackRes.feedback].sort((a, b) =>
          (a.created_at ?? '').localeCompare(b.created_at ?? '')
        );
        const itemMap = new Map<string, ItemFeedbackAction>();
        const trainingMap = new Map<string, TrainingFeedbackAction>();
        for (const f of sorted) {
          if (isItemFeedbackAction(f.action)) itemMap.set(f.opportunity_id, f.action);
          if (isTrainingFeedbackAction(f.action)) trainingMap.set(f.opportunity_id, f.action);
        }
        setItemFeedbackMap(itemMap);
        setTrainingFeedbackMap(trainingMap);
      }

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

  const clusterById = useMemo(() => new Map(clusters.map(c => [c.id, c])), [clusters]);

  const savedIds = useMemo(
    () => new Set([...itemFeedbackMap].filter(([, v]) => v === 'save').map(([k]) => k)),
    [itemFeedbackMap]
  );
  const dismissedIds = useMemo(
    () => new Set([...itemFeedbackMap].filter(([, v]) => v === 'dismiss').map(([k]) => k)),
    [itemFeedbackMap]
  );

  const filteredOpportunities = opportunities.filter(o => {
    if (gapFilter === 'saved') return savedIds.has(o.id);
    if (gapFilter === 'dismissed') return dismissedIds.has(o.id);
    return !dismissedIds.has(o.id);
  });

  const strongCount = opportunities.filter(o => o.confidence >= 0.7).length;
  const evidenceCount = opportunities.reduce((sum, o) => sum + o.evidence_count, 0);
  const title = niche?.name ?? (status === 'loading' ? '' : fallbackTitleFromId(marketId));

  const handleItemFeedback = async (opportunityId: string, action: ItemFeedbackAction) => {
    const previousAction = itemFeedbackMap.get(opportunityId);
    setFeedbackError(null);
    setItemFeedbackMap(prev => {
      const next = new Map(prev);
      next.set(opportunityId, action);
      return next;
    });
    try {
      await signalApi.createOpportunityFeedback(opportunityId, { market_id: marketId, action });
    } catch (err) {
      setItemFeedbackMap(prev => {
        const next = new Map(prev);
        if (previousAction) next.set(opportunityId, previousAction);
        else next.delete(opportunityId);
        return next;
      });
      setFeedbackError(err instanceof Error ? err.message : 'Failed to record feedback');
    }
  };

  const handleTrainingFeedback = async (opportunityId: string, action: TrainingFeedbackAction) => {
    const previousAction = trainingFeedbackMap.get(opportunityId);
    setFeedbackError(null);
    setTrainingFeedbackMap(prev => {
      const next = new Map(prev);
      next.set(opportunityId, action);
      return next;
    });
    try {
      await signalApi.createOpportunityFeedback(opportunityId, { market_id: marketId, action });
    } catch (err) {
      setTrainingFeedbackMap(prev => {
        const next = new Map(prev);
        if (previousAction) next.set(opportunityId, previousAction);
        else next.delete(opportunityId);
        return next;
      });
      setFeedbackError(err instanceof Error ? err.message : 'Failed to record feedback');
    }
  };

  const agentIsWorking = competitors.length > 0 && sources.length > 0 && opportunities.length === 0;
  const needsSetup = !agentIsWorking && coldStart?.status === 'setup_needed' && opportunities.length === 0;
  const scanFailed = agentIsWorking && sources.some(s => s.last_error !== null);

  return (
    <DashboardShell
      title={title}
      subtitle={niche?.description ?? 'Ranked product gaps backed by public evidence.'}
      actions={<NicheViewSwitcher marketId={marketId} active="gaps" onRefresh={load} refreshing={status === 'loading'} />}
    >
      {status === 'loading' && <LoadingPanel label="Loading gaps" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">

          {needsSetup ? (
            <ColdStartPanel coldStart={coldStart!} marketId={marketId} />
          ) : agentIsWorking ? (
            <AgentWorkingPanel
              competitors={competitors}
              sources={sources}
              scanFailed={scanFailed}
              nextScanAt={nextScanAt}
              marketId={marketId}
              onViewBrief={() => setShowBrief(v => !v)}
            />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <StatRow compact stats={[
                  { label: 'Gaps identified', value: opportunities.length, accent: opportunities.length > 0 },
                  { label: 'Strong signals', value: strongCount, accent: strongCount > 0 },
                  { label: 'Evidence items', value: evidenceCount },
                ]} />
                <div className="ml-auto flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1">
                    {(['all', 'saved', 'dismissed'] as const).map(filter => (
                      <button
                        key={filter}
                        onClick={() => setGapFilter(filter)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition ${gapFilter === filter ? 'bg-slate-700 text-slate-100 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                      >
                        {filter}
                        {filter === 'saved' && savedIds.size > 0 && (
                          <span className="ml-1 text-slate-600">({savedIds.size})</span>
                        )}
                      </button>
                    ))}
                  </div>
                  {coldStart && (
                    <button
                      onClick={() => setShowBrief(v => !v)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                        showBrief
                          ? 'border-violet-500/30 bg-violet-500/10 text-violet-300'
                          : 'border-slate-700/70 text-slate-500 hover:border-slate-600 hover:text-slate-300'
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${coldStart.status === 'setup_needed' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                      Research brief
                    </button>
                  )}
                </div>
              </div>

              {showBrief && coldStart && (
                <ResearchBriefPanel coldStart={coldStart} marketId={marketId} />
              )}
              {feedbackError && (
                <p className="text-xs text-rose-400">{feedbackError}</p>
              )}

              {filteredOpportunities.length === 0 ? (
                <EmptyPanel
                  title={gapFilter === 'all' ? 'No gaps identified yet' : `No ${gapFilter} gaps`}
                  detail={gapFilter === 'all' ? 'Gaps appear after active sources are scanned.' : undefined}
                />
              ) : (
                <div className="space-y-3">
                  {filteredOpportunities.map((opportunity, index) => (
                    <GapCard
                      key={opportunity.id}
                      rank={index + 1}
                      opportunity={opportunity}
                      marketId={marketId}
                      theme={opportunity.cluster_id ? clusterById.get(opportunity.cluster_id) : undefined}
                      meta={TIER_META[opportunityTier(opportunity.confidence)]}
                      itemAction={itemFeedbackMap.get(opportunity.id) ?? null}
                      trainingAction={trainingFeedbackMap.get(opportunity.id) ?? null}
                      onItemFeedback={action => handleItemFeedback(opportunity.id, action)}
                      onTrainingFeedback={action => handleTrainingFeedback(opportunity.id, action)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

// ── Research Brief Panel ───────────────────────────────────────────────────────

function ResearchBriefPanel({
  coldStart,
  marketId,
}: {
  coldStart: AgentColdStartPlan;
  marketId: string;
}) {
  return (
    <section className="rounded-xl border border-slate-800/60 bg-slate-900/30 px-5 pb-5 pt-4">
      {coldStart.status === 'setup_needed' && (
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-amber-400">Setup needed</p>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-3">
              {coldStart.brief.objective && (
                <BriefField label="Objective" value={coldStart.brief.objective} />
              )}
              {coldStart.brief.target_user && (
                <BriefField label="Target user" value={coldStart.brief.target_user} />
              )}
            </div>
            <div className="space-y-3">
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Sources</p>
                <p className="text-xs text-slate-400">
                  <span className="font-medium text-slate-300">{coldStart.monitored_source_count}</span> monitored
                  {coldStart.active_source_count > 0 && (
                    <> · <span className="font-medium text-slate-300">{coldStart.active_source_count}</span> active</>
                  )}
                  {coldStart.suggested_source_count > 0 && (
                    <> · <Link href={`/markets/${encodeURIComponent(marketId)}/sources`} className="text-violet-400 hover:underline">{coldStart.suggested_source_count} suggested</Link></>
                  )}
                </p>
              </div>
              {coldStart.brief.source_family_priorities.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Source priorities</p>
                  <div className="flex flex-wrap gap-1.5">
                    {coldStart.brief.source_family_priorities.map(fam => (
                      <span key={fam} className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-400">{fam}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
      </div>
    </section>
  );
}

function BriefField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">{label}</p>
      <p className="text-xs leading-relaxed text-slate-400">{value}</p>
    </div>
  );
}

// ── Agent working panel ────────────────────────────────────────────────────────

function AgentWorkingPanel({
  competitors,
  sources,
  scanFailed,
  nextScanAt,
  marketId,
  onViewBrief,
}: {
  competitors: Competitor[];
  sources: MonitoredSource[];
  scanFailed: boolean;
  nextScanAt: string | null;
  marketId: string;
  onViewBrief: () => void;
}) {
  const sourceFamilies = [...new Set(
    sources
      .map(s => (s.source_family ?? (s.options?.source_family as string | undefined)))
      .filter((f): f is string => typeof f === 'string' && f.length > 0)
  )];

  const displayCompanies = competitors.slice(0, 6);
  const extraCount = competitors.length - displayCompanies.length;

  return (
    <div className={`rounded-xl border p-5 ${scanFailed ? 'border-amber-500/20 bg-amber-500/[0.04]' : 'border-violet-500/20 bg-violet-500/[0.03]'}`}>
      <div className="mb-3 flex items-center gap-2">
        {scanFailed ? (
          <>
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.5)]" />
            <h2 className="text-sm font-semibold text-amber-300">Scan encountered errors</h2>
          </>
        ) : (
          <>
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.6)]" />
            <h2 className="text-sm font-semibold text-violet-300">Agent is monitoring</h2>
          </>
        )}
      </div>

      <p className="mb-4 text-xs leading-relaxed text-slate-500">
        {scanFailed
          ? 'One or more sources returned errors on the last scan. Check the Sources tab for details. Signals will appear here once a scan completes successfully.'
          : 'Sources are configured and active. Gaps will appear here after the first scan completes.'}
      </p>

      {displayCompanies.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Monitoring</p>
          <div className="flex flex-wrap gap-1.5">
            {displayCompanies.map(c => (
              <span key={c.id} className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-400">{c.name}</span>
            ))}
            {extraCount > 0 && (
              <span className="rounded-md bg-slate-800/40 px-2 py-0.5 text-[11px] text-slate-600">+{extraCount} more</span>
            )}
          </div>
        </div>
      )}

      {sourceFamilies.length > 0 && (
        <div className="mb-4">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Source channels</p>
          <div className="flex flex-wrap gap-1.5">
            {sourceFamilies.map(f => (
              <span key={f} className="rounded-md border border-slate-800/50 bg-slate-800/40 px-2 py-0.5 text-[11px] capitalize text-slate-500">
                {f.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 border-t border-slate-800/50 pt-3">
        <Link
          href={`/markets/${encodeURIComponent(marketId)}/sources`}
          className="rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-200"
        >
          View sources
        </Link>
        <button
          onClick={onViewBrief}
          className="rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-200"
        >
          View research brief
        </button>
        <span className="text-[11px] text-slate-700">Changes apply to future scans only.</span>
        {nextScanAt && (
          <span className="ml-auto text-[11px] text-slate-700">
            Next scan {new Date(nextScanAt).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Cold-start setup panel ─────────────────────────────────────────────────────

const SETUP_ACTION_LABELS: Record<string, string> = {
  refine_research_brief: 'Refine the research brief',
  add_companies: 'Add companies to this niche',
  add_sources: 'Add monitored sources',
  review_suggested_sources: 'Review suggested sources',
  run_first_scan: 'Ready for first scan',
};

function setupActionLabel(action: string) {
  return SETUP_ACTION_LABELS[action] ?? fallbackTitleFromId(action);
}

function ColdStartPanel({ coldStart, marketId }: { coldStart: AgentColdStartPlan; marketId: string }) {
  return (
    <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-5">
      <div className="mb-2 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]" />
        <h2 className="text-sm font-semibold text-amber-300">Agent needs setup</h2>
      </div>
      <p className="mb-4 text-xs leading-relaxed text-slate-500">
        This niche doesn&apos;t have enough data to surface gaps yet. Complete the steps below to start the research agent.
      </p>
      {coldStart.next_actions.length > 0 && (
        <ul className="mb-4 space-y-1.5">
          {coldStart.next_actions.map((action, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-700" />
              {setupActionLabel(action)}
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        <Link
          href={`/markets/${encodeURIComponent(marketId)}/sources`}
          className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-semibold text-violet-300 transition hover:bg-violet-500/15"
        >
          Add sources
        </Link>
        <Link
          href={`/markets/${encodeURIComponent(marketId)}/sources`}
          className="rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-200"
        >
          Add companies
        </Link>
      </div>
    </div>
  );
}

// ── Gap card ───────────────────────────────────────────────────────────────────

function GapCard({
  rank,
  opportunity,
  marketId,
  theme,
  meta,
  itemAction,
  trainingAction,
  onItemFeedback,
  onTrainingFeedback,
}: {
  rank: number;
  opportunity: Opportunity;
  marketId: string;
  theme?: SignalCluster;
  meta: typeof TIER_META['strong'];
  itemAction: ItemFeedbackAction | null;
  trainingAction: TrainingFeedbackAction | null;
  onItemFeedback: (action: ItemFeedbackAction) => void;
  onTrainingFeedback: (action: TrainingFeedbackAction) => void;
}) {
  const saved = itemAction === 'save';
  const dismissed = itemAction === 'dismiss';

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
                {opportunity.market_company_count != null && (
                  <> of <span className="font-medium text-slate-400">{opportunity.market_company_count}</span></>
                )}{' '}
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

          <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-800/50 pt-3">
            <div className="flex items-center gap-1.5">
              <FeedbackButton
                active={saved}
                onClick={() => onItemFeedback('save')}
                icon={<IconBookmark filled={saved} />}
                label={saved ? 'Saved' : 'Save'}
                activeClass="border-violet-500/30 bg-violet-500/10 text-violet-400"
              />
              <FeedbackButton
                active={dismissed}
                onClick={() => onItemFeedback('dismiss')}
                icon={<IconX />}
                label={dismissed ? 'Dismissed' : 'Dismiss'}
                activeClass="border-slate-600 text-slate-400"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <IconFeedbackButton
                active={trainingAction === 'more_like_this'}
                onClick={() => onTrainingFeedback('more_like_this')}
                icon={<IconThumbUp />}
                activeClass="border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                title="More like this"
              />
              <IconFeedbackButton
                active={trainingAction === 'less_like_this'}
                onClick={() => onTrainingFeedback('less_like_this')}
                icon={<IconThumbDown />}
                activeClass="border-rose-500/30 bg-rose-500/10 text-rose-400"
                title="Less like this"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeedbackButton({
  active,
  onClick,
  icon,
  label,
  activeClass,
  title,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
  activeClass: string;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition ${active ? activeClass : 'border-slate-700/50 text-slate-600 hover:border-slate-600 hover:text-slate-400'}`}
    >
      {icon}
      {label}
    </button>
  );
}

function IconFeedbackButton({
  active,
  onClick,
  icon,
  activeClass,
  title,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  activeClass: string;
  title: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      aria-label={title}
      className={`inline-flex items-center justify-center rounded-md border p-1.5 transition ${active ? activeClass : 'border-slate-700/50 text-slate-600 hover:border-slate-600 hover:text-slate-400'}`}
    >
      {icon}
    </button>
  );
}
