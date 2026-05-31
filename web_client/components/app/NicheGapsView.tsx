'use client';

import type { ReactNode } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel, StatRow } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import {
  AgentActivity,
  AgentColdStartPlan,
  AgentFeedbackAction,
  NicheCompany,
  Market,
  MonitoredSource,
  Opportunity,
  SignalCluster,
} from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type EvidenceStrength = 'early' | 'emerging' | 'validated';
type GapFilter = 'all' | 'saved' | 'dismissed';
type ItemFeedbackAction = Extract<AgentFeedbackAction, 'save' | 'dismiss'>;
type TrainingFeedbackAction = Extract<AgentFeedbackAction, 'more_like_this' | 'less_like_this'>;

const STRENGTH_META: Record<EvidenceStrength, { label: string; dotCls: string; badgeCls: string }> = {
  validated: { label: 'Validated gap', dotCls: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]', badgeCls: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400' },
  emerging: { label: 'Emerging gap', dotCls: 'bg-amber-400', badgeCls: 'border-amber-500/25 bg-amber-500/10 text-amber-400' },
  early: { label: 'Early signal', dotCls: 'bg-slate-500', badgeCls: 'border-slate-700/60 bg-slate-800/60 text-slate-400' },
};

function evidenceStrength(opportunity: Opportunity): EvidenceStrength {
  return opportunity.evidence_strength ?? 'early';
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
  const [competitors, setCompetitors] = useState<NicheCompany[]>([]);
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
    setPipelineStatus(null);
    setProgressActivity([]);
    try {
      const [market, oppsRes, clustersRes, coldStartRes, feedbackRes, competitorsRes, sourcesRes, scheduleRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getOpportunities({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
        signalApi.getMarketAgentColdStart(marketId).catch(() => null),
        signalApi.getMarketAgentFeedback(marketId).catch(() => null),
        signalApi.getMarketCompanies(marketId).catch(() => null),
        signalApi.getMarketSources(marketId).catch(() => null),
        signalApi.getPipelineSchedule().catch(() => null),
      ]);
      setNiche(market);
      setOpportunities(oppsRes.opportunities);
      setClusters(clustersRes.clusters);
      setColdStart(coldStartRes);
      setCompetitors(competitorsRes?.companies ?? []);
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

  const [pipelineStatus, setPipelineStatus] = useState<string | null>(null);
  const [progressActivity, setProgressActivity] = useState<AgentActivity[]>([]);
  const prevPipelineStatusRef = useRef<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activityIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Silently refresh only opportunities and clusters — no loading flash, no state reset
  const refreshData = async () => {
    try {
      const [oppsRes, clustersRes] = await Promise.all([
        signalApi.getOpportunities({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
      ]);
      setOpportunities(oppsRes.opportunities);
      setClusters(clustersRes.clusters);
    } catch {
      // ignore background errors
    }
  };

  // Poll pipeline status; trigger data refresh on running → done transition
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await signalApi.getMarketPipelineStatus(marketId);
        if (cancelled) return;
        const prev = prevPipelineStatusRef.current;
        prevPipelineStatusRef.current = res.status;
        setPipelineStatus(res.status);
        if (prev === 'running' && res.status === 'done') {
          refreshData();
          setProgressActivity([]);
        }
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 404) clearInterval(intervalRef.current ?? undefined);
      }
    };
    poll();
    intervalRef.current = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(intervalRef.current ?? undefined);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  // Poll activity events every 5s while pipeline is running
  useEffect(() => {
    if (pipelineStatus !== 'running') {
      clearInterval(activityIntervalRef.current ?? undefined);
      return;
    }
    let cancelled = false;
    const pollActivity = async () => {
      try {
        const res = await signalApi.getMarketAgentActivity(marketId);
        if (!cancelled) setProgressActivity(res.activity);
      } catch { /* ignore */ }
    };
    pollActivity();
    activityIntervalRef.current = setInterval(pollActivity, 5000);
    return () => {
      cancelled = true;
      clearInterval(activityIntervalRef.current ?? undefined);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelineStatus, marketId]);

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

  const validatedCount = opportunities.filter(o => evidenceStrength(o) === 'validated').length;
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

  const needsSetup = coldStart?.status === 'setup_needed' && opportunities.length === 0;

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

          {pipelineStatus === 'running' && opportunities.length === 0 && (
            <PipelineProgressStrip activity={progressActivity} />
          )}

          {needsSetup ? (
            <ColdStartPanel coldStart={coldStart!} marketId={marketId} />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <StatRow compact stats={[
                  { label: 'Candidates surfaced', value: opportunities.length, accent: opportunities.length > 0 },
                  { label: 'Validated gaps', value: validatedCount, accent: validatedCount > 0 },
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
                  title={gapFilter === 'all' ? 'No candidates surfaced yet' : `No ${gapFilter} candidates`}
                  detail={gapFilter === 'all' ? 'Opportunity candidates appear after active sources are scanned.' : undefined}
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
                      meta={STRENGTH_META[evidenceStrength(opportunity)]}
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

// ── Pipeline Progress Strip ────────────────────────────────────────────────────

type ProgressStep = {
  key: string;
  label: string;
  detail: string | null;
  done: boolean;
};

function currentRunEvents(activity: AgentActivity[]): AgentActivity[] {
  // Activity is newest-first. Slice down to the most recent run_started.
  const startIdx = activity.findIndex(a => a.event_type === 'run_started');
  return startIdx >= 0 ? activity.slice(0, startIdx + 1) : activity;
}

function PipelineProgressStrip({ activity }: { activity: AgentActivity[] }) {
  const run = currentRunEvents(activity);
  const ev = (type: string) => run.find(a => a.event_type === type);

  const sources = ev('sources_scanned');
  const filtered = ev('posts_filtered');
  const extracted = ev('signals_extracted');
  const clustered = ev('clusters_formed');
  const gaps = ev('gaps_synthesized');

  const steps: ProgressStep[] = [
    {
      key: 'sources',
      label: 'Scanning sources',
      done: !!sources,
      detail: sources
        ? `${sources.metadata?.success_count ?? sources.metadata?.source_count} sources · ${sources.metadata?.post_count} posts`
        : null,
    },
    {
      key: 'filter',
      label: 'Reviewing posts',
      done: !!filtered,
      detail: filtered
        ? `${filtered.metadata?.relevant_count} relevant of ${
            ((filtered.metadata?.relevant_count as number) ?? 0) +
            ((filtered.metadata?.filtered_count as number) ?? 0)
          }`
        : null,
    },
    {
      key: 'signals',
      label: 'Extracting signals',
      done: !!extracted,
      detail: extracted ? `${extracted.metadata?.signal_count} found` : null,
    },
    {
      key: 'gaps',
      label: 'Identifying gaps',
      done: !!gaps,
      detail: gaps ? `${gaps.metadata?.gap_count} new gap${(gaps.metadata?.gap_count as number) !== 1 ? 's' : ''}` : null,
    },
  ];

  const activeIdx = steps.findLastIndex(s => s.done) + 1;

  return (
    <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.04] px-5 py-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.7)]" />
        <p className="text-xs font-semibold text-violet-300">Research agent running…</p>
      </div>
      <div className="flex items-center gap-1.5">
        {steps.map((step, i) => {
          const isActive = i === activeIdx;
          const isDone = step.done;
          return (
            <div key={step.key} className="flex min-w-0 flex-1 items-center gap-1.5">
              <div className={`flex min-w-0 flex-1 flex-col rounded-lg border px-3 py-2 transition-colors ${
                isDone
                  ? 'border-violet-500/25 bg-violet-500/[0.07]'
                  : isActive
                  ? 'border-slate-700/60 bg-slate-800/40'
                  : 'border-slate-800/40 bg-transparent'
              }`}>
                <div className="flex items-center gap-1.5">
                  {isDone ? (
                    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-violet-400">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : isActive ? (
                    <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-slate-500" />
                  ) : (
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-slate-800" />
                  )}
                  <span className={`truncate text-[11px] font-medium ${isDone ? 'text-violet-300' : isActive ? 'text-slate-400' : 'text-slate-700'}`}>
                    {step.label}
                  </span>
                </div>
                {(isDone && step.detail) && (
                  <p className="mt-0.5 truncate pl-3 text-[10px] text-slate-500">{step.detail}</p>
                )}
                {isActive && !step.detail && (
                  <p className="mt-0.5 animate-pulse pl-3 text-[10px] text-slate-700">…</p>
                )}
              </div>
              {i < steps.length - 1 && (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`shrink-0 ${isDone ? 'text-violet-500/40' : 'text-slate-800'}`}>
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              )}
            </div>
          );
        })}
      </div>
    </div>
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
  meta: typeof STRENGTH_META['early'];
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
                {opportunity.evidence_count} quote{opportunity.evidence_count === 1 ? '' : 's'}
              </span>
              {theme && <ClusterLink id={theme.id} marketId={marketId}>{theme.theme}</ClusterLink>}
            </div>
          </div>

          {opportunity.pain_summary && (
            <div className="mb-3">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Observed pain</p>
              <p className="text-sm leading-relaxed text-slate-400">{opportunity.pain_summary}</p>
            </div>
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
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Possible wedge</p>
                <p className="text-xs text-violet-300">{opportunity.suggested_wedge}</p>
              </div>
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-xs text-slate-600">
              Evidence trail:
              {' '}<span className="font-medium text-slate-400">{opportunity.evidence_count}</span> quote{opportunity.evidence_count === 1 ? '' : 's'}
              {' '}· <span className="font-medium text-slate-400">{opportunity.evidence_source_count ?? 0}</span> source{opportunity.evidence_source_count === 1 ? '' : 's'}
              {opportunity.company_count > 0 && (
                <>
                  {' '}· <span className="font-medium text-slate-400">{opportunity.company_count}</span>
                  {opportunity.market_company_count != null && (
                    <>/{opportunity.market_company_count}</>
                  )}{' '}
                  compan{opportunity.company_count === 1 ? 'y' : 'ies'}
                </>
              )}
            </span>
            {opportunity.company_names.slice(0, 4).map(name => (
              <span key={name} className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">{name}</span>
            ))}
          </div>

          {opportunity.evidence_strength === 'early' && (
            <div className="mt-3 rounded-lg border border-slate-800/70 bg-slate-950/30 px-3 py-2">
              <p className="text-xs leading-relaxed text-slate-500">
                Treat this as a lead to verify. The agent found a narrow signal, but it needs more evidence before it should drive roadmap decisions.
              </p>
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
