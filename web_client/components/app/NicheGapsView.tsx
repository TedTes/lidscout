'use client';

import type { ReactNode } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import {
  AgentActivity,
  AgentColdStartPlan,
  PipelineLiveFeedResponse,
  AgentFeedbackAction,
  NicheCompany,
  Market,
  MonitoredSource,
  Opportunity,
  SignalCluster,
} from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type EvidenceStrength = 'early' | 'moderate' | 'strong' | 'emerging' | 'validated';
type GapFilter = 'all' | 'saved' | 'dismissed';
type ItemFeedbackAction = Extract<AgentFeedbackAction, 'save' | 'dismiss'>;
type TrainingFeedbackAction = Extract<AgentFeedbackAction, 'more_like_this' | 'less_like_this'>;

const STRENGTH_META: Record<EvidenceStrength, { label: string; dotCls: string; badgeCls: string }> = {
  strong: { label: 'Strong signal', dotCls: 'bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.85)]', badgeCls: 'border-emerald-400/35 bg-emerald-400/15 text-emerald-200' },
  moderate: { label: 'Moderate signal', dotCls: 'bg-amber-300 shadow-[0_0_7px_rgba(251,191,36,0.6)]', badgeCls: 'border-amber-400/35 bg-amber-400/15 text-amber-200' },
  validated: { label: 'Validated gap', dotCls: 'bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.85)]', badgeCls: 'border-emerald-400/35 bg-emerald-400/15 text-emerald-200' },
  emerging: { label: 'Emerging gap', dotCls: 'bg-amber-300 shadow-[0_0_7px_rgba(251,191,36,0.6)]', badgeCls: 'border-amber-400/35 bg-amber-400/15 text-amber-200' },
  early: { label: 'Early signal', dotCls: 'bg-blue-300 shadow-[0_0_7px_rgba(96,165,250,0.55)]', badgeCls: 'border-blue-400/35 bg-blue-400/12 text-blue-200' },
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

function plural(n: number, singular: string, pluralForm = `${singular}s`) {
  return `${n} ${n === 1 ? singular : pluralForm}`;
}

function unmetNeedLabel(type: Opportunity['unmet_need_type']) {
  if (!type) return null;
  return {
    time: 'Time sink',
    money: 'Cost pressure',
    effort: 'Manual effort',
    capability: 'Missing capability',
    fit: 'Poor fit',
  }[type] ?? null;
}

function formatElapsed(isoString: string | null | undefined): string | null {
  if (!isoString) return null;
  const minutes = Math.floor((Date.now() - new Date(isoString).getTime()) / 60000);
  if (minutes < 1) return 'just now';
  return plural(minutes, 'min') + ' ago';
}

function formatUntil(isoString: string | null): string | null {
  if (!isoString) return null;
  const ms = new Date(isoString).getTime() - Date.now();
  if (ms <= 0) return 'soon';
  const hours = Math.floor(ms / 3600000);
  if (hours > 0) return `${hours}h`;
  return `${Math.floor((ms % 3600000) / 60000)}m`;
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
  const [, setCompetitors] = useState<NicheCompany[]>([]);
  const [, setSources] = useState<MonitoredSource[]>([]);
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
  const [liveFeed, setLiveFeed] = useState<PipelineLiveFeedResponse>({ current_item: null, recent_decisions: [] });
  const prevPipelineStatusRef = useRef<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activityIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const liveFeedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const runStartedEvent = useMemo(
    () => currentRunEvents(progressActivity).find(a => a.event_type === 'run_started'),
    [progressActivity]
  );
  const isRunningFirstScan = pipelineStatus === 'running' && opportunities.length === 0;

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

  useEffect(() => {
    if (pipelineStatus !== 'running') {
      clearInterval(liveFeedIntervalRef.current ?? undefined);
      if (pipelineStatus === 'done') setLiveFeed({ current_item: null, recent_decisions: [] });
      return;
    }
    let cancelled = false;
    const pollLiveFeed = async () => {
      try {
        const res = await signalApi.getMarketPipelineLiveFeed(marketId);
        if (!cancelled) setLiveFeed(res);
      } catch { /* ignore */ }
    };
    pollLiveFeed();
    liveFeedIntervalRef.current = setInterval(pollLiveFeed, 2000);
    return () => {
      cancelled = true;
      clearInterval(liveFeedIntervalRef.current ?? undefined);
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

  const strongCount = opportunities.filter(o => {
    const strength = evidenceStrength(o);
    return strength === 'strong' || strength === 'validated';
  }).length;
  const evidenceCount = opportunities.reduce((sum, o) => sum + o.evidence_count, 0);
  const title = niche?.name ?? (status === 'loading' ? '' : fallbackTitleFromId(marketId));
  const subtitle = niche?.description
    || coldStart?.brief?.objective
    || (niche?.target_user ? `For ${niche.target_user}` : null)
    || 'Ranked product gaps backed by public evidence.';

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
      subtitle={subtitle}
      actions={
        <div className="grid w-full gap-3 lg:grid-cols-[minmax(140px,1fr)_auto_minmax(48px,1fr)] lg:items-start">
          <div className="flex min-h-9 items-center">
            <AgentStatusPill
              pipelineStatus={pipelineStatus}
              runStartedAt={runStartedEvent?.created_at}
              nextScanAt={nextScanAt}
            />
          </div>
          <NicheViewSwitcher marketId={marketId} active="gaps" onRefresh={load} refreshing={status === 'loading'} />
          <div className="hidden lg:block" />
        </div>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading gaps" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">

          {pipelineStatus === 'running' && opportunities.length === 0 && (
            <>
              <PipelineProgressStrip
                activity={progressActivity}
                runStartedAt={runStartedEvent?.created_at}
                currentItem={liveFeed.current_item}
              />
              {liveFeed.recent_decisions.length > 0 && (
                <RecentDecisionsFeed decisions={liveFeed.recent_decisions} />
              )}
            </>
          )}

          {needsSetup ? (
            <ColdStartPanel coldStart={coldStart!} marketId={marketId} />
          ) : (
            <>
              {isRunningFirstScan ? (
                <p className="text-xs text-slate-600">Awaiting first candidates from this scan</p>
              ) : (
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <GapMetric label="Candidates surfaced" value={opportunities.length} active={opportunities.length > 0} />
                    <GapMetric label="Strong signals" value={strongCount} active={strongCount > 0} />
                    <GapMetric label="Evidence items" value={evidenceCount} />
                  </div>
                  <div className="ml-auto flex flex-wrap items-center gap-3">
                    <div className="flex items-center divide-x divide-slate-700/80 text-sm font-semibold">
                      {(['all', 'saved', 'dismissed'] as const).map(filter => (
                        <button
                          key={filter}
                          onClick={() => setGapFilter(filter)}
                          className={`px-2 capitalize transition first:pl-0 last:pr-0 ${gapFilter === filter ? 'text-slate-100' : 'text-slate-500 hover:text-slate-300'}`}
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
                            ? 'border-slate-600/70 bg-slate-800/50 text-slate-200'
                            : 'border-slate-700/70 bg-slate-900/30 text-slate-500 hover:border-slate-600 hover:text-slate-300'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${coldStart.status === 'setup_needed' ? 'bg-amber-400' : 'bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.75)]'}`} />
                        Research brief
                      </button>
                    )}
                  </div>
                </div>
              )}

              {showBrief && coldStart && !isRunningFirstScan && (
                <ResearchBriefPanel coldStart={coldStart} marketId={marketId} />
              )}
              {feedbackError && (
                <p className="text-xs text-rose-400">{feedbackError}</p>
              )}

              {filteredOpportunities.length === 0 ? (
                isRunningFirstScan ? (
                  <p className="mt-2 text-xs text-slate-600">
                    Candidates will appear here when the agent finishes grouping evidence.
                  </p>
                ) : (
                  <EmptyPanel
                    title={gapFilter === 'all' ? 'No candidates surfaced yet' : `No ${gapFilter} candidates`}
                    detail={gapFilter === 'all' ? 'Opportunity candidates appear after active sources are scanned.' : undefined}
                  />
                )
              ) : (
                <div className="space-y-4">
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

// ── Agent Status Pill ──────────────────────────────────────────────────────────

function AgentStatusPill({
  pipelineStatus,
  runStartedAt,
  nextScanAt,
}: {
  pipelineStatus: string | null;
  runStartedAt: string | null | undefined;
  nextScanAt: string | null;
}) {
  if (!pipelineStatus || pipelineStatus === 'pending') return null;

  if (pipelineStatus === 'running') {
    const elapsed = formatElapsed(runStartedAt);
    return (
      <div className="flex items-center gap-1.5 rounded-full border border-violet-500/20 bg-violet-500/[0.06] px-3 py-1.5 text-xs text-violet-300 whitespace-nowrap">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.6)]" />
        <span>Agent running{elapsed ? ` · ${elapsed}` : ''}</span>
      </div>
    );
  }

  if (pipelineStatus === 'failed') {
    return (
      <div className="flex items-center gap-1.5 rounded-full border border-rose-500/20 bg-rose-500/[0.06] px-3 py-1.5 text-xs text-rose-400 whitespace-nowrap">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
        <span>Last scan had errors</span>
      </div>
    );
  }

  const until = formatUntil(nextScanAt);
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-slate-800/60 bg-slate-900/30 px-3 py-1.5 text-xs text-slate-600 whitespace-nowrap">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />
      <span>Agent idle{until ? ` · next in ${until}` : ''}</span>
    </div>
  );
}

// ── Pipeline Progress Strip ────────────────────────────────────────────────────

function currentRunEvents(activity: AgentActivity[]): AgentActivity[] {
  const startIdx = activity.findIndex(a => a.event_type === 'run_started');
  return startIdx >= 0 ? activity.slice(0, startIdx + 1) : activity;
}

function PipelineProgressStrip({
  activity,
  runStartedAt,
  currentItem,
}: {
  activity: AgentActivity[];
  runStartedAt?: string | null;
  currentItem?: AgentActivity | null;
}) {
  const [sourcesExpanded, setSourcesExpanded] = useState(false);
  const run = currentRunEvents(activity);
  const ev = (type: string) => run.find(a => a.event_type === type);

  const sourcesEv = ev('sources_scanned');
  const filteredEv = ev('posts_filtered');
  const extractedEv = ev('signals_extracted');
  const gapsEv = ev('gaps_synthesized');

  const sourceCount = (sourcesEv?.metadata?.success_count ?? sourcesEv?.metadata?.source_count) as number | undefined;
  const postCount = sourcesEv?.metadata?.post_count as number | undefined;
  const relevantCount = filteredEv?.metadata?.relevant_count as number | undefined;
  const filteredCount = filteredEv?.metadata?.filtered_count as number | undefined;
  const signalCount = extractedEv?.metadata?.signal_count as number | undefined;
  const gapCount = gapsEv?.metadata?.gap_count as number | undefined;

  type Step = {
    key: string;
    label: string;
    done: boolean;
    completedDetail: string | null;
    activeText: string;
    futureText: string;
  };

  const steps: Step[] = [
    {
      key: 'sources',
      label: 'Scanning sources',
      done: !!sourcesEv,
      completedDetail: sourceCount != null && postCount != null
        ? `${plural(sourceCount, 'source')} · ${plural(postCount, 'post')}`
        : null,
      activeText: 'Fetching posts from active sources',
      futureText: 'Waiting for sources',
    },
    {
      key: 'filter',
      label: 'Reviewing posts',
      done: !!filteredEv,
      completedDetail: relevantCount != null && filteredCount != null
        ? `${plural(relevantCount, 'relevant')} · ${plural(filteredCount, 'filtered')}`
        : null,
      activeText: 'Checking posts against the research brief',
      futureText: 'Waiting for post review',
    },
    {
      key: 'signals',
      label: 'Extracting findings',
      done: !!extractedEv,
      completedDetail: signalCount != null ? `${plural(signalCount, 'finding')} extracted` : null,
      activeText: 'Extracting structured pain signals',
      futureText: 'Waiting for findings',
    },
    {
      key: 'gaps',
      label: 'Identifying candidates',
      done: !!gapsEv,
      completedDetail: gapCount != null ? `${plural(gapCount, 'candidate')} surfaced` : null,
      activeText: 'Grouping evidence into candidate gaps',
      futureText: 'Waiting for themes',
    },
  ];

  const activeIdx = steps.findLastIndex(s => s.done) + 1;
  const fallbackText = activeIdx < steps.length ? steps[activeIdx].activeText : null;
  const currentlyText = currentItem
    ? `${currentItem.metadata?.title as string || 'post'} · ${currentItem.metadata?.source_label as string || ''}`
    : fallbackText;
  const elapsed = formatElapsed(runStartedAt);

  return (
    <div className="space-y-3 rounded-xl border border-violet-500/20 bg-violet-500/[0.04] px-5 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.7)]" />
          <p className="text-xs font-semibold text-violet-300">Research agent running…</p>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-600">
          {elapsed && <span>Started {elapsed}</span>}
          <span className="text-slate-800">·</span>
          <span>Typical scan: 8–15 min</span>
        </div>
      </div>

      <div className="flex items-start gap-1.5">
        {steps.map((step, i) => {
          const isActive = i === activeIdx;
          const isDone = step.done;
          const isFuture = i > activeIdx;
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
                  {isDone && step.key === 'sources' && (
                    <button
                      onClick={() => setSourcesExpanded(v => !v)}
                      className="ml-auto shrink-0 text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
                    >
                      {sourcesExpanded ? '▲' : '▼'}
                    </button>
                  )}
                </div>
                {isDone && step.completedDetail && (
                  <p className="mt-0.5 truncate pl-3 text-[10px] text-slate-500">{step.completedDetail}</p>
                )}
                {isDone && step.key === 'sources' && sourcesExpanded && (() => {
                  const sourceList = sourcesEv?.metadata?.sources as Array<{
                    source_label: string; post_count: number;
                    posts: Array<{ title: string; url: string | null; post_date: string | null }>;
                  }> | undefined;
                  if (!sourceList?.length) {
                    return <p className="mt-1 pl-3 text-[10px] text-slate-600">Source-level counts were not recorded for this run.</p>;
                  }
                  return (
                    <div className="mt-1.5 space-y-2 pl-3">
                      {sourceList.map((src, si) => (
                        <div key={si}>
                          <p className="text-[10px] font-semibold text-slate-500">{src.source_label} · {plural(src.post_count, 'post')}</p>
                          <ul className="mt-0.5 space-y-0.5">
                            {src.posts.slice(0, 8).map((p, pi) => (
                              <li key={pi} className="truncate text-[10px] text-slate-600">
                                {p.url
                                  ? <a href={p.url} target="_blank" rel="noopener noreferrer" className="hover:text-slate-400 hover:underline">{p.title || p.url}</a>
                                  : <span>{p.title || '(untitled)'}</span>}
                              </li>
                            ))}
                            {src.posts.length > 8 && (
                              <li className="text-[10px] text-slate-700">+{src.posts.length - 8} more</li>
                            )}
                          </ul>
                        </div>
                      ))}
                    </div>
                  );
                })()}
                {isFuture && (
                  <p className="mt-0.5 truncate pl-3 text-[10px] text-slate-700">{step.futureText}</p>
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

      {currentlyText && (
        <p className="text-[11px] text-slate-600">Currently: {currentlyText}</p>
      )}
    </div>
  );
}

// ── Recent Decisions Mini-Feed ─────────────────────────────────────────────────

const REJECTION_LABELS: Record<string, string> = {
  empty: 'no content',
  wrong_subject: 'off-topic',
  tutorial_or_template: 'tutorial',
  promotional: 'promotional',
  news: 'news',
  job_posting: 'job posting',
  no_pain_signal: 'no pain signal',
  other: 'filtered',
};

function RecentDecisionsFeed({ decisions }: { decisions: AgentActivity[] }) {
  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-900/20 px-4 py-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
        Recent decisions
      </p>
      <div className="space-y-1.5">
        {decisions.map(d => {
          const accepted = d.event_type === 'post_accepted';
          const title = (d.metadata?.title as string) || d.title.replace(/^(Kept|Filtered):\s*/i, '');
          const source = d.metadata?.source_label as string | undefined;
          const reason = d.metadata?.reason as string | undefined;
          return (
            <div key={d.id} className="flex items-start gap-2 text-[11px]">
              <span className={`mt-px shrink-0 font-semibold ${accepted ? 'text-emerald-500' : 'text-slate-600'}`}>
                {accepted ? '✓' : '✗'}
              </span>
              <span className={`truncate ${accepted ? 'text-slate-400' : 'text-slate-600'}`}>
                <span className="font-medium">{accepted ? 'Kept' : 'Filtered'}</span>
                {' · '}
                <span className="italic">&ldquo;{title}&rdquo;</span>
                {source && <span className="text-slate-600"> · {source}</span>}
                {!accepted && reason && (
                  <span className="ml-1 rounded bg-slate-800/60 px-1 py-px text-[10px] text-slate-600">
                    {REJECTION_LABELS[reason] ?? reason}
                  </span>
                )}
              </span>
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

function GapMetric({ label, value, active }: { label: string; value: number; active?: boolean }) {
  return (
    <div className={`rounded-md border px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${
      active
        ? 'border-slate-700/80 bg-slate-900/50 text-slate-400'
        : 'border-slate-800/70 bg-transparent text-slate-600'
    }`}>
      <span className={`mr-2 text-sm leading-none tabular-nums ${active ? 'text-slate-200' : 'text-slate-500'}`}>{value}</span>
      {label}
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
  const needLabel = unmetNeedLabel(opportunity.unmet_need_type);
  const sourceCount = opportunity.evidence_source_count ?? 0;
  const companyBreadth = opportunity.company_count > 0
    ? `${opportunity.company_count}${opportunity.market_company_count != null ? ` of ${opportunity.market_company_count}` : ''} ${opportunity.company_count === 1 ? 'company' : 'companies'}`
    : null;

  return (
    <article className={`overflow-hidden rounded-xl border bg-slate-900/35 shadow-[0_18px_60px_rgba(0,0,0,0.18)] transition-colors hover:border-slate-700/80 ${dismissed ? 'border-slate-800/40 opacity-50' : 'border-slate-800/90'}`}>
      <div className="border-b border-white/[0.06] bg-white/[0.035] px-5 py-4">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-slate-700/70 bg-slate-900/80 text-lg font-semibold tabular-nums text-slate-200">
            {rank}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex max-w-4xl flex-wrap items-center gap-x-3 gap-y-2">
              <h3 className="text-lg font-semibold leading-snug text-slate-50">{opportunity.title}</h3>
              <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold ${meta.badgeCls}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dotCls}`} />
                {meta.label}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium text-slate-500">
                {plural(opportunity.evidence_count, 'quote')} · {plural(sourceCount, 'source')}
              </span>
              {needLabel && (
                <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] font-medium text-slate-400">{needLabel}</span>
              )}
              {theme && <ClusterLink id={theme.id} marketId={marketId}>{theme.theme}</ClusterLink>}
              {companyBreadth && (
                <span className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">Across {companyBreadth}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="px-5 py-4">
        {opportunity.pain_summary && (
          <section>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Observed pain</p>
            <p className="max-w-4xl text-sm leading-relaxed text-slate-300">{opportunity.pain_summary}</p>
          </section>
        )}

        <div className="my-3 h-px bg-white/[0.07]" />

        <div className="grid gap-4 md:grid-cols-2">
          {opportunity.target_user && (
            <section className="md:border-r md:border-white/[0.07] md:pr-4">
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Affected user</p>
              <p className="text-sm leading-relaxed text-slate-200">{opportunity.target_user}</p>
            </section>
          )}
          {opportunity.suggested_wedge && (
            <section>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Possible wedge</p>
              <p className="text-sm leading-relaxed text-violet-200">{opportunity.suggested_wedge}</p>
            </section>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-slate-800/80 bg-slate-950/30 px-3 py-2.5">
          <span className="text-sm text-slate-400">
            Evidence trail:
            {' '}<span className="font-semibold text-slate-200">{plural(opportunity.evidence_count, 'quote')}</span>
            {' '}· <span className="font-semibold text-slate-200">{plural(sourceCount, 'source')}</span>
          </span>
          <Link
            href={theme ? `/markets/${encodeURIComponent(marketId)}/themes/${encodeURIComponent(theme.id)}` : `/markets/${encodeURIComponent(marketId)}/findings`}
            className="rounded-md border border-blue-500/25 bg-blue-500/10 px-2 py-1 text-[11px] font-semibold text-blue-200 transition hover:bg-blue-500/15"
          >
            View evidence
          </Link>
          {opportunity.company_names.slice(0, 4).map(name => (
            <span key={name} className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-400">{name}</span>
          ))}
          {opportunity.company_names.length > 4 && (
            <span className="text-[11px] text-slate-600">+{opportunity.company_names.length - 4}</span>
          )}
        </div>

        {opportunity.why_it_matters && (
          <p className="mt-3 text-xs leading-relaxed text-slate-500">{opportunity.why_it_matters}</p>
        )}

        {evidenceStrength(opportunity) === 'early' && (
          <div className="mt-3 rounded-lg border border-blue-400/20 bg-blue-400/[0.05] px-3 py-2">
            <p className="text-xs leading-relaxed text-blue-100/75">
              Verification note: early lead. The agent found a narrow signal and needs more evidence before this should drive roadmap decisions.
            </p>
          </div>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.06] px-5 py-3">
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
      </footer>
    </article>
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
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-semibold transition ${active ? activeClass : 'border-slate-700/70 bg-slate-900/60 text-slate-400 hover:border-slate-600 hover:bg-slate-800/70 hover:text-slate-200'}`}
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
      className={`inline-flex items-center justify-center rounded-md border p-1.5 transition ${active ? activeClass : 'border-slate-700/70 bg-slate-900/60 text-slate-400 hover:border-slate-600 hover:bg-slate-800/70 hover:text-slate-200'}`}
    >
      {icon}
    </button>
  );
}
