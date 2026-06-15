'use client';

import type { ReactNode } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import ResearchThread from '@/components/app/ResearchThread';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel, relativeTime } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { readableSourceUrl } from '@/lib/sourceUrls';
import {
  AgentActivity,
  AgentColdStartPlan,
  EvidenceItem,
  PipelineLiveFeedResponse,
  AgentFeedbackAction,
  AccumulatedTheme,
  NicheCompany,
  Market,
  MonitoredSource,
  Opportunity,
} from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type EvidenceStrength = 'early' | 'moderate' | 'strong' | 'emerging' | 'validated';
type ItemFeedbackAction = Extract<AgentFeedbackAction, 'save' | 'dismiss'>;
type TrainingFeedbackAction = Extract<AgentFeedbackAction, 'more_like_this' | 'less_like_this'>;
type RecencyFilter = 7 | 30 | 90 | null;
type FeedbackFilter = 'all' | 'saved' | 'dismissed';

const STRENGTH_META: Record<EvidenceStrength, { label: string; dotCls: string; badgeCls: string }> = {
  strong:    { label: 'Strong signal',    dotCls: 'bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.85)]',   badgeCls: 'border-emerald-400/35 bg-emerald-400/15 text-emerald-200' },
  moderate:  { label: 'Moderate signal',  dotCls: 'bg-amber-300 shadow-[0_0_7px_rgba(251,191,36,0.6)]',      badgeCls: 'border-amber-400/35 bg-amber-400/15 text-amber-200' },
  validated: { label: 'Validated gap',    dotCls: 'bg-emerald-300 shadow-[0_0_8px_rgba(52,211,153,0.85)]',   badgeCls: 'border-emerald-400/35 bg-emerald-400/15 text-emerald-200' },
  emerging:  { label: 'Emerging gap',     dotCls: 'bg-amber-300 shadow-[0_0_7px_rgba(251,191,36,0.6)]',      badgeCls: 'border-amber-400/35 bg-amber-400/15 text-amber-200' },
  early:     { label: 'Early signal',     dotCls: 'bg-blue-300 shadow-[0_0_7px_rgba(96,165,250,0.55)]',      badgeCls: 'border-blue-400/35 bg-blue-400/12 text-blue-200' },
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
  return { time: 'Time sink', money: 'Cost pressure', effort: 'Manual effort', capability: 'Missing capability', fit: 'Poor fit' }[type] ?? null;
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
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
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
  const [themes, setThemes] = useState<AccumulatedTheme[]>([]);
  const [scanSources, setScanSources] = useState<MonitoredSource[]>([]);
  const [coldStart, setColdStart] = useState<AgentColdStartPlan | null>(null);
  const [, setCompetitors] = useState<NicheCompany[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [itemFeedbackMap, setItemFeedbackMap] = useState<Map<string, ItemFeedbackAction>>(new Map());
  const [trainingFeedbackMap, setTrainingFeedbackMap] = useState<Map<string, TrainingFeedbackAction>>(new Map());
  const [recencyFilter, setRecencyFilter] = useState<RecencyFilter>(null);
  const [feedbackFilter, setFeedbackFilter] = useState<FeedbackFilter>('all');
  const [scanTriggering, setScanTriggering] = useState(false);
  const [scanQueued, setScanQueued] = useState(false);

  const fetchOpportunities = async (days: RecencyFilter) => {
    try {
      const res = await signalApi.getOpportunities({
        market_id: marketId,
        recency_days: days ?? undefined,
      });
      setOpportunities(res.opportunities);
    } catch { /* ignore background errors */ }
  };

  const load = async () => {
    setStatus('loading');
    setError(null);
    setFeedbackError(null);
    setNiche(null);
    setColdStart(null);
    setCompetitors([]);
    setScanSources([]);
    setItemFeedbackMap(new Map());
    setTrainingFeedbackMap(new Map());
    setPipelineStatus(null);
    setProgressActivity([]);
    try {
      const [market, oppsRes, themesRes, coldStartRes, feedbackRes, competitorsRes, sourcesRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getOpportunities({ market_id: marketId }),
        signalApi.getThemes({ market_id: marketId }),
        signalApi.getMarketAgentColdStart(marketId).catch(() => null),
        signalApi.getMarketAgentFeedback(marketId).catch(() => null),
        signalApi.getMarketCompanies(marketId).catch(() => null),
        signalApi.getMarketSources(marketId).catch(() => null),
      ]);
      setNiche(market);
      setOpportunities(oppsRes.opportunities);
      setThemes(themesRes.themes);
      setColdStart(coldStartRes);
      setCompetitors(competitorsRes?.companies ?? []);
      setScanSources(sourcesRes?.sources ?? []);

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

  useEffect(() => {
    if (status !== 'ready') return;
    fetchOpportunities(recencyFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recencyFilter]);

  const [pipelineStatus, setPipelineStatus] = useState<string | null>(null);
  const [lastEventAt, setLastEventAt] = useState<string | null>(null);
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
  const currentProgressActivity = useMemo(
    () => currentRunEvents(progressActivity),
    [progressActivity]
  );
  const isRunningFirstScan = pipelineStatus === 'running' && opportunities.length === 0;

  const refreshData = async () => {
    try {
      const [oppsRes, themesRes] = await Promise.all([
        signalApi.getOpportunities({ market_id: marketId, recency_days: recencyFilter ?? undefined }),
        signalApi.getThemes({ market_id: marketId }),
      ]);
      setOpportunities(oppsRes.opportunities);
      setThemes(themesRes.themes);
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
        if (res.last_event_at) setLastEventAt(res.last_event_at);
        if (res.status === 'running' || res.status === 'done') setScanQueued(false);
        if (prev === 'running' && res.status === 'done') {
          refreshData();
          setProgressActivity([]);
        }
      } catch (err: unknown) {
        const s = (err as { response?: { status?: number } })?.response?.status;
        if (s === 404) clearInterval(intervalRef.current ?? undefined);
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
    if (pipelineStatus !== 'running' && !scanQueued) {
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
  }, [pipelineStatus, scanQueued, marketId]);

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

  const themeById = useMemo(() => new Map(themes.map(theme => [theme.id, theme])), [themes]);

  const savedIds = useMemo(
    () => new Set([...itemFeedbackMap].filter(([, v]) => v === 'save').map(([k]) => k)),
    [itemFeedbackMap]
  );
  const dismissedIds = useMemo(
    () => new Set([...itemFeedbackMap].filter(([, v]) => v === 'dismiss').map(([k]) => k)),
    [itemFeedbackMap]
  );

  const visibleOpportunities = useMemo(() => {
    if (feedbackFilter === 'saved') return opportunities.filter(o => savedIds.has(o.id));
    if (feedbackFilter === 'dismissed') return opportunities.filter(o => dismissedIds.has(o.id));
    return opportunities.filter(o => !dismissedIds.has(o.id));
  }, [opportunities, feedbackFilter, savedIds, dismissedIds]);

  const title = niche?.name ?? (status === 'loading' ? '' : fallbackTitleFromId(marketId));
  const searchableSources = useMemo(
    () => scanSources.filter(source => source.enabled && source.scan_eligible !== false),
    [scanSources]
  );

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

  const handleRunScan = async () => {
    if (scanTriggering) return;
    setScanTriggering(true);
    try {
      const result = await signalApi.triggerMarketPipeline(marketId);
      if (['queued', 'already_queued', 'already_running'].includes(result.status)) {
        setScanQueued(true);
      } else {
        refreshData();
      }
    } catch { /* ignore */ }
    setScanTriggering(false);
  };

  const needsSetup = coldStart?.status === 'setup_needed' && opportunities.length === 0;

  return (
    <DashboardShell
      title={title}
      actions={<NicheViewSwitcher marketId={marketId} active="gaps" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading opportunities" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="animate-fade-in">
          {needsSetup ? (
            <ColdStartPanel coldStart={coldStart!} marketId={marketId} />
          ) : isRunningFirstScan || (scanQueued && opportunities.length === 0) || (scanTriggering && opportunities.length === 0) ? (
            <div className="flex min-h-[420px] items-center justify-center py-6 sm:min-h-[520px]">
              <CenteredScanProgress
                progressActivity={currentProgressActivity}
                liveFeed={liveFeed}
                runStartedAt={runStartedEvent?.created_at}
                marketId={marketId}
                sources={searchableSources}
              />
            </div>
          ) : opportunities.length === 0 ? (
            /* ── Empty idle state: centered run scan ── */
            <div className="flex min-h-[420px] flex-col items-center justify-center gap-6 py-6 sm:min-h-[520px]">
              <div className="text-center">
                <p className="text-base font-semibold text-slate-300">No candidates surfaced yet</p>
                <p className="mt-1 text-sm text-slate-500">Run a scan to start finding opportunities.</p>
              </div>
              <button
                onClick={handleRunScan}
                className="rounded-xl border border-violet-500/30 bg-violet-500/15 px-8 py-3 text-sm font-semibold text-violet-300 transition hover:bg-violet-500/20"
              >
                Run scan
              </button>
            </div>
          ) : (
            /* ── Has data: opportunities + right panel ── */
            <div className="grid gap-5 xl:grid-cols-[1fr_272px] xl:items-start">

              {/* ── Opportunities list ── */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <OpportunitiesStatsBar
                    count={visibleOpportunities.length}
                    lastEventAt={lastEventAt}
                    isRunning={pipelineStatus === 'running'}
                  />
                  {pipelineStatus !== 'running' && (
                    scanTriggering ? (
                      <button disabled className="rounded-lg border border-slate-700/50 px-3 py-1.5 text-xs font-semibold text-slate-500">
                        Starting…
                      </button>
                    ) : scanQueued ? (
                      <button disabled className="flex items-center gap-1.5 rounded-lg border border-violet-500/20 bg-violet-500/[0.06] px-3 py-1.5 text-xs font-semibold text-violet-400/60">
                        <span className="h-1 w-1 animate-pulse rounded-full bg-violet-400" />
                        Queued
                      </button>
                    ) : (
                      <button
                        onClick={handleRunScan}
                        className="rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-semibold text-slate-400 transition hover:border-violet-500/30 hover:bg-violet-500/10 hover:text-violet-300"
                      >
                        Run scan
                      </button>
                    )
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1 rounded-lg border border-slate-800/70 bg-slate-900/40 p-1">
                    {(['all', 'saved', 'dismissed'] as FeedbackFilter[]).map(f => (
                      <button
                        key={f}
                        onClick={() => setFeedbackFilter(f)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition ${
                          feedbackFilter === f
                            ? 'bg-slate-700/80 text-slate-200'
                            : 'text-slate-500 hover:text-slate-300'
                        }`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-1 rounded-lg border border-slate-800/70 bg-slate-900/40 p-1">
                    {([null, 7, 30, 90] as RecencyFilter[]).map(d => (
                      <button
                        key={d ?? 'all'}
                        onClick={() => setRecencyFilter(d)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                          recencyFilter === d
                            ? 'bg-slate-700/80 text-slate-200'
                            : 'text-slate-500 hover:text-slate-300'
                        }`}
                      >
                        {d == null ? 'All time' : `${d}d`}
                      </button>
                    ))}
                  </div>
                </div>

                {feedbackError && <p className="text-xs text-rose-400">{feedbackError}</p>}

                {visibleOpportunities.map((opportunity, index) => (
                  <GapCard
                    key={opportunity.id}
                    rank={index + 1}
                    opportunity={opportunity}
                    marketId={marketId}
                    theme={
                      opportunity.source_theme_id
                        ? themeById.get(opportunity.source_theme_id)
                        : opportunity.cluster_id
                        ? themeById.get(opportunity.cluster_id)
                        : undefined
                    }
                    meta={STRENGTH_META[evidenceStrength(opportunity)]}
                    itemAction={itemFeedbackMap.get(opportunity.id) ?? null}
                    trainingAction={trainingFeedbackMap.get(opportunity.id) ?? null}
                    onItemFeedback={action => handleItemFeedback(opportunity.id, action)}
                    onTrainingFeedback={action => handleTrainingFeedback(opportunity.id, action)}
                  />
                ))}
              </div>

              {/* ── Right: agent inbox + scan progress ── */}
              <div className="space-y-4">
                <ResearchThread marketId={marketId} />
                {pipelineStatus === 'running' && (
                  <LiveAgentPanel
                    pipelineStatus={pipelineStatus}
                    progressActivity={currentProgressActivity}
                    liveFeed={liveFeed}
                    runStartedAt={runStartedEvent?.created_at}
                    lastEventAt={lastEventAt}
                    marketId={marketId}
                    sources={searchableSources}
                    onRunScan={handleRunScan}
                    scanTriggering={scanTriggering}
                    scanQueued={scanQueued}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

// ── Run grouping helper ────────────────────────────────────────────────────────

function currentRunEvents(activity: AgentActivity[]): AgentActivity[] {
  const startIdx = activity.findIndex(a => a.event_type === 'run_started');
  return startIdx >= 0 ? activity.slice(0, startIdx + 1) : activity;
}

// ── Cold-start setup panel ─────────────────────────────────────────────────────

const SETUP_ACTION_LABELS: Record<string, string> = {
  refine_research_brief: 'Refine the research brief',
  add_companies: 'Add companies to this niche',
  add_sources: 'Improve research coverage',
  review_suggested_sources: 'Review research coverage',
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
        <Link href={`/markets/${encodeURIComponent(marketId)}/sources`} className="rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-200">
          Research coverage
        </Link>
      </div>
    </div>
  );
}

// ── Opportunities stats bar ────────────────────────────────────────────────────

function OpportunitiesStatsBar({ count, lastEventAt, isRunning }: { count: number; lastEventAt: string | null; isRunning: boolean }) {
  const lastScan = relativeTime(lastEventAt);
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span className="font-semibold text-slate-300">
        {count} {count === 1 ? 'Opportunity' : 'Opportunities'}
      </span>
      {isRunning ? (
        <span className="flex items-center gap-1.5 text-violet-400">
          · <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" /> Scanning now
        </span>
      ) : lastScan ? (
        <span>· Last scan: {lastScan}</span>
      ) : null}
    </div>
  );
}

// ── Centered scan progress (empty page + running) ─────────────────────────────

const SCAN_STEPS: Array<{ eventType: string; label: string }> = [
  { eventType: 'sources_scanned',   label: 'Scanning sources' },
  { eventType: 'posts_filtered',    label: 'Reviewing posts' },
  { eventType: 'signals_extracted', label: 'Extracting evidence' },
  { eventType: 'gaps_synthesized',  label: 'Identifying opportunities' },
];

function CenteredScanProgress({
  progressActivity,
  liveFeed,
  runStartedAt,
  marketId,
  sources,
}: {
  progressActivity: AgentActivity[];
  liveFeed: PipelineLiveFeedResponse;
  runStartedAt: string | null | undefined;
  marketId: string;
  sources: MonitoredSource[];
}) {
  const stepEvents = SCAN_STEPS.map(s => ({
    ...s,
    event: progressActivity.find(a => a.event_type === s.eventType),
  }));
  const completedCount = stepEvents.filter(s => s.event).length;
  const progressPct = Math.round((completedCount / SCAN_STEPS.length) * 100);
  const activeIdx = stepEvents.findIndex(s => !s.event);

  const currentItemLabel = liveFeed.current_item
    ? (liveFeed.current_item.metadata?.title as string) || liveFeed.current_item.detail || null
    : null;

  return (
    <div className="mx-auto w-full max-w-md rounded-xl border border-violet-500/20 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="h-2 w-2 animate-pulse rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.6)]" />
          <span className="text-sm font-semibold text-slate-200">Scan in progress</span>
        </div>
        <span className="text-sm font-bold tabular-nums text-violet-300">{progressPct}%</span>
      </div>

      <div className="mb-1 flex items-center justify-between text-[11px] text-slate-600">
        {runStartedAt && <span>Started {relativeTime(runStartedAt)}</span>}
        <span className="ml-auto">{completedCount} of {SCAN_STEPS.length} steps</span>
      </div>
      <div className="mb-5 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-violet-500 transition-all duration-700"
          style={{ width: `${Math.max(progressPct, 4)}%` }}
        />
      </div>

      <div className="space-y-3">
        {stepEvents.map((step, i) => {
          const isDone = !!step.event;
          const isActive = i === activeIdx;
          return (
            <div key={step.eventType} className="flex items-center gap-3">
              {isDone ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-emerald-400">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : isActive ? (
                <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.5)]" />
              ) : (
                <span className="h-2 w-2 shrink-0 rounded-full bg-slate-800" />
              )}
              <span className={`flex-1 text-sm ${isDone ? 'text-slate-300' : isActive ? 'text-slate-400' : 'text-slate-700'}`}>
                {step.label}
              </span>
              {isDone && step.event?.created_at && (
                <span className="text-[11px] text-slate-600">{relativeTime(step.event.created_at)}</span>
              )}
            </div>
          );
        })}
      </div>

      {currentItemLabel && (
        <p className="mt-4 truncate text-xs text-slate-600">
          Processing: <span className="text-slate-500">{currentItemLabel}</span>
        </p>
      )}

      <ScanSourceList sources={sources} />

    </div>
  );
}

// ── Live agent panel (shown when opportunities exist) ──────────────────────────

function LiveAgentPanel({
  pipelineStatus,
  progressActivity,
  liveFeed,
  runStartedAt,
  lastEventAt,
  marketId,
  sources,
  onRunScan,
  scanTriggering = false,
  scanQueued = false,
}: {
  pipelineStatus: string | null;
  progressActivity: AgentActivity[];
  liveFeed: PipelineLiveFeedResponse;
  runStartedAt: string | null | undefined;
  lastEventAt: string | null;
  marketId: string;
  sources: MonitoredSource[];
  onRunScan: () => void;
  scanTriggering?: boolean;
  scanQueued?: boolean;
}) {
  const isRunning = pipelineStatus === 'running';

  const stepEvents = SCAN_STEPS.map(s => ({
    ...s,
    event: progressActivity.find(a => a.event_type === s.eventType),
  }));
  const completedCount = stepEvents.filter(s => s.event).length;
  const progressPct = isRunning ? Math.round((completedCount / SCAN_STEPS.length) * 100) : 0;

  const activeStepIndex = isRunning
    ? stepEvents.findIndex(s => !s.event)
    : -1;

  const currentItemLabel = liveFeed.current_item
    ? (liveFeed.current_item.metadata?.title as string) || liveFeed.current_item.detail || null
    : null;

  const lastScan = relativeTime(lastEventAt);

  return (
    <div className="sticky top-4 overflow-hidden rounded-xl border border-slate-800/70 bg-slate-900/50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.5)]" />
          )}
          <span className="text-sm font-semibold text-slate-200">
            {isRunning ? 'Scan in progress' : 'Last scan'}
          </span>
        </div>
        {isRunning
          ? <span className="text-xs font-bold tabular-nums text-violet-300">{progressPct}%</span>
          : lastScan && <span className="text-[11px] text-slate-600">{lastScan}</span>
        }
      </div>

      {/* Progress bar (running only) */}
      {isRunning && (
        <div className="border-b border-white/[0.04] px-4 pb-3 pt-2.5">
          <div className="mb-1.5 flex items-center justify-between text-[11px]">
            <span className="text-slate-500">
              {runStartedAt ? `Started ${relativeTime(runStartedAt)}` : 'Running…'}
            </span>
            <span className="text-slate-600">{completedCount} of {SCAN_STEPS.length} steps</span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-violet-500 transition-all duration-700"
              style={{ width: `${Math.max(progressPct, 4)}%` }}
            />
          </div>
        </div>
      )}

      {/* Step list */}
      <div className="divide-y divide-white/[0.04] px-4">
        {stepEvents.map((step, i) => {
          const isDone = !!step.event;
          const isActive = i === activeStepIndex;
          const isFuture = !isDone && !isActive;
          return (
            <div key={step.eventType} className="flex items-center gap-2.5 py-2.5">
              {isDone ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-emerald-400">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : isActive ? (
                <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.5)]" />
              ) : (
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-slate-800" />
              )}
              <span className={`min-w-0 flex-1 truncate text-xs ${isDone ? 'text-slate-300' : isActive ? 'text-slate-400' : 'text-slate-700'}`}>
                {step.label}
              </span>
              {isDone && step.event?.created_at && (
                <span className="shrink-0 text-[10px] text-slate-700">{relativeTime(step.event.created_at)}</span>
              )}
              {isFuture && isRunning && (
                <span className="shrink-0 text-[10px] text-slate-800">–</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Current item being processed */}
      {isRunning && currentItemLabel && (
        <div className="border-t border-white/[0.04] px-4 py-2.5">
          <p className="truncate text-[11px] text-slate-600">
            Processing: <span className="text-slate-500">{currentItemLabel}</span>
          </p>
        </div>
      )}

      {isRunning && (
        <div className="border-t border-white/[0.04] px-4 py-3">
          <ScanSourceList sources={sources} compact />
        </div>
      )}

      {/* Footer */}
      <div className="space-y-2 border-t border-white/[0.06] px-4 py-3">
        {isRunning ? (
          <button disabled className="w-full cursor-default rounded-lg border border-slate-700/50 py-2 text-sm font-semibold text-slate-500">
            Scanning…
          </button>
        ) : scanTriggering ? (
          <button disabled className="w-full cursor-default rounded-lg border border-violet-500/20 bg-violet-500/[0.06] py-2 text-sm font-semibold text-violet-400/60">
            Starting…
          </button>
        ) : scanQueued ? (
          <button disabled className="flex w-full items-center justify-center gap-2 cursor-default rounded-lg border border-violet-500/20 bg-violet-500/[0.06] py-2 text-sm font-semibold text-violet-400/60">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />
            Queued
          </button>
        ) : (
          <button
            onClick={onRunScan}
            className="w-full rounded-lg border border-violet-500/25 bg-violet-500/10 py-2 text-sm font-semibold text-violet-300 transition hover:bg-violet-500/15"
          >
            Run scan
          </button>
        )}
      </div>
    </div>
  );
}

function ScanSourceList({ sources, compact = false }: { sources: MonitoredSource[]; compact?: boolean }) {
  const visible = sources.slice(0, compact ? 4 : 6);

  if (sources.length === 0) {
    return (
      <div className={`${compact ? '' : 'mt-4'} rounded-lg border border-slate-800/60 bg-slate-950/25 px-3 py-2`}>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">Searching</p>
        <p className="mt-1 text-xs text-slate-500">No enabled scan-ready source URLs are available.</p>
      </div>
    );
  }

  return (
    <div className={`${compact ? '' : 'mt-4'} rounded-lg border border-slate-800/60 bg-slate-950/25 px-3 py-2`}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">Searching</p>
        <span className="text-[10px] text-slate-700">
          {plural(sources.length, 'URL')}
        </span>
      </div>
      <div className="space-y-1">
        {visible.map(source => (
          <a
            key={source.id}
            href={source.locator}
            target="_blank"
            rel="noreferrer noopener"
            className="block truncate rounded px-1 py-0.5 text-[11px] text-slate-500 transition hover:bg-slate-900 hover:text-violet-300"
            title={source.locator}
          >
            {source.locator}
          </a>
        ))}
      </div>
      {sources.length > visible.length && (
        <p className="mt-1.5 text-[10px] text-slate-700">
          +{sources.length - visible.length} more source {sources.length - visible.length === 1 ? 'URL' : 'URLs'}
        </p>
      )}
    </div>
  );
}

// ── Evidence helpers ──────────────────────────────────────────────────────────

const FAMILY_LABELS: Record<string, string> = {
  technical_forum:  'Technical forums',
  technical_forums: 'Technical forums',
  social:           'Social',
  reviews:          'Reviews',
  owned_site:       'Owned',
  other:            'Other',
};

function familyLabel(family: string): string {
  return FAMILY_LABELS[family] ?? family.replace(/_/g, ' ');
}

function EvidenceItemRow({ item }: { item: EvidenceItem }) {
  const meta = [
    item.source_label,
    item.source_family && !item.source_label ? familyLabel(item.source_family) : null,
    item.company_name,
  ].filter(Boolean).join(' · ');
  const sourceUrl = readableSourceUrl(item.url, item.post_id);

  return (
    <div className="rounded-lg bg-slate-950/40 p-3">
      {(item.quote || item.pain) && (
        <p className="text-xs leading-relaxed text-slate-400 line-clamp-3">
          &ldquo;{item.quote || item.pain}&rdquo;
        </p>
      )}
      <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-600">
        {meta && <span className="font-medium text-slate-500">{meta}</span>}
        {item.detected_at && <span className="shrink-0">{relativeTime(item.detected_at)}</span>}
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="ml-auto shrink-0 font-medium text-violet-400/70 transition hover:text-violet-400"
            onClick={e => e.stopPropagation()}
          >
            Open ↗
          </a>
        )}
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
  theme?: AccumulatedTheme;
  meta: typeof STRENGTH_META['early'];
  itemAction: ItemFeedbackAction | null;
  trainingAction: TrainingFeedbackAction | null;
  onItemFeedback: (action: ItemFeedbackAction) => void;
  onTrainingFeedback: (action: TrainingFeedbackAction) => void;
}) {
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [askSent, setAskSent] = useState(false);

  const saved = itemAction === 'save';
  const dismissed = itemAction === 'dismiss';
  const confidence = opportunity.confidence ? Math.round(opportunity.confidence * 100) : null;
  const needLabel = unmetNeedLabel(opportunity.unmet_need_type);

  const bullets: string[] = [
    opportunity.pain_summary,
    opportunity.why_it_matters,
    opportunity.suggested_wedge,
  ].filter(Boolean) as string[];

  const evidenceHref = `/markets/${encodeURIComponent(marketId)}/evidence?view=findings`;

  // Source attribution: prefer specific labels from evidence_items, fall back to family breakdown
  const sourceAttribution: string[] = opportunity.evidence_items?.length
    ? [...new Set(opportunity.evidence_items.map(e => e.source_label).filter(Boolean))] as string[]
    : opportunity.source_family_breakdown?.length
    ? opportunity.source_family_breakdown.map(b => familyLabel(b.source_family))
    : [];

  const hasEvidenceItems = (opportunity.evidence_items?.length ?? 0) > 0;

  async function handleAskDeeper() {
    if (askSent) return;
    try {
      await signalApi.createMarketAgentFollowUp(marketId, {
        question: `Tell me more about: ${opportunity.title}`,
      });
      setAskSent(true);
      setTimeout(() => setAskSent(false), 3000);
    } catch { /* silent */ }
  }

  return (
    <article className={`overflow-hidden rounded-xl border bg-slate-900/40 shadow-[0_8px_32px_rgba(0,0,0,0.15)] transition hover:border-slate-700/70 ${dismissed ? 'border-slate-800/40 opacity-40' : 'border-slate-800/80'}`}>

      {/* ── Card header (always visible, clickable to expand reasoning) ── */}
      <div
        className="flex cursor-pointer items-center gap-3 px-4 py-3 transition hover:bg-white/[0.015]"
        onClick={() => setReasoningOpen(v => !v)}
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-slate-700/60 bg-slate-950/70 text-xs font-bold tabular-nums text-slate-400">
          {rank}
        </span>
        <p className="min-w-0 flex-1 truncate text-[15px] font-semibold leading-snug tracking-tight text-slate-100 sm:text-base">
          {opportunity.title}
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-semibold ${meta.badgeCls}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${meta.dotCls}`} />
            {meta.label}
            {confidence != null && confidence > 0 && (
              <span className="opacity-60">· {confidence}%</span>
            )}
          </span>
          <svg
            width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
            className={`shrink-0 text-slate-600 transition-transform duration-200 ${reasoningOpen ? '-rotate-180' : ''}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>

      {/* ── Agent Reasoning (expandable) ── */}
      {reasoningOpen && (
        <div className="border-t border-white/[0.04] px-4 pb-3 pt-2.5">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Agent Reasoning</p>
          <div className="space-y-2">
            {bullets.slice(0, 3).map((b, i) => (
              <div key={i} className="flex items-start gap-2">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0 text-emerald-400">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <p className="text-xs leading-relaxed text-slate-400 line-clamp-2">{b}</p>
              </div>
            ))}
          </div>
          {opportunity.verification_note && (
            <div className="mt-2.5 flex items-start gap-1.5 rounded-md bg-slate-800/50 px-2.5 py-2">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mt-0.5 shrink-0 text-slate-500">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <p className="text-[11px] leading-relaxed text-slate-500">{opportunity.verification_note}</p>
            </div>
          )}
          {(needLabel || theme) && (
            <div className="mt-2.5 flex flex-wrap items-center gap-2">
              {needLabel && (
                <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] font-medium text-slate-400">{needLabel}</span>
              )}
              {theme && <ClusterLink id={theme.id} marketId={marketId}>{theme.theme}</ClusterLink>}
            </div>
          )}
        </div>
      )}

      {/* ── Footer: evidence toggle + source chips + actions ── */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-2 border-t border-white/[0.04] px-4 py-2.5">
        <button
          onClick={() => setEvidenceOpen(v => !v)}
          className="inline-flex items-center gap-1 rounded-md border border-blue-500/20 bg-blue-500/[0.07] px-2.5 py-1 text-[11px] font-semibold text-blue-300 transition hover:bg-blue-500/10"
        >
          View {plural(opportunity.evidence_count, 'quote')}
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-150 ${evidenceOpen ? '-rotate-180' : ''}`}>
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {sourceAttribution.slice(0, 3).map(label => (
          <span key={label} className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-slate-500">{label}</span>
        ))}

        <div className="ml-auto flex items-center gap-1.5">
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
            label="Dismiss"
            activeClass="border-slate-600 text-slate-400"
          />
          <button
            onClick={handleAskDeeper}
            className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-semibold transition ${
              askSent
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : 'border-violet-500/20 bg-violet-500/[0.06] text-violet-300 hover:bg-violet-500/12'
            }`}
          >
            {askSent ? 'Sent ✓' : 'Ask deeper'}
          </button>
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

      {/* ── Evidence drawer ── */}
      {evidenceOpen && (
        <div className="border-t border-white/[0.04] px-4 py-3">
          {hasEvidenceItems ? (
            <div className="space-y-2">
              {opportunity.evidence_items!.slice(0, 6).map(item => (
                <EvidenceItemRow key={item.id} item={item} />
              ))}
              {opportunity.evidence_items!.length > 6 && (
                <Link
                  href={evidenceHref}
                  className="block pt-1 text-center text-[11px] text-slate-600 transition hover:text-slate-400"
                >
                  +{opportunity.evidence_items!.length - 6} more in Evidence tab →
                </Link>
              )}
            </div>
          ) : (
            <Link
              href={evidenceHref}
              className="block text-center text-[11px] text-slate-600 transition hover:text-slate-400"
            >
              View all evidence in Evidence tab →
            </Link>
          )}
        </div>
      )}
    </article>
  );
}

function FeedbackButton({
  active, onClick, icon, label, activeClass, title,
}: {
  active: boolean; onClick: () => void; icon: ReactNode; label: string; activeClass: string; title?: string;
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
  active, onClick, icon, activeClass, title,
}: {
  active: boolean; onClick: () => void; icon: ReactNode; activeClass: string; title: string;
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
