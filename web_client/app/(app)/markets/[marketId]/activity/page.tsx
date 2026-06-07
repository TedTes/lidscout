'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { EmptyPanel, ErrorPanel, LoadingPanel, relativeTime } from '@/components/ui/DashboardPrimitives';
import AgentInbox from '@/components/app/AgentInbox';
import { signalApi } from '@/lib/api';
import { AgentActivity, Market } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

// ── Run grouping ───────────────────────────────────────────────────────────────

const RUN_MEMBER_TYPES = new Set([
  'run_started', 'sources_scanned', 'posts_filtered', 'signals_extracted',
  'clusters_formed', 'gaps_synthesized', 'run_completed', 'source_failed',
]);

type RunGroup = {
  id: string;
  startedAt: string | null;
  completedAt: string | null;
  status: 'running' | 'done' | 'failed';
  sourceCount: number | null;
  postCount: number | null;
  signalCount: number | null;
  gapCount: number | null;
  events: AgentActivity[];
};

function groupIntoRuns(activity: AgentActivity[]): { runs: RunGroup[]; standalone: AgentActivity[] } {
  const sorted = [...activity].sort((a, b) =>
    (a.created_at ?? '').localeCompare(b.created_at ?? '')
  );

  const runs: RunGroup[] = [];
  const standalone: AgentActivity[] = [];
  let current: RunGroup | null = null;

  for (const ev of sorted) {
    if (ev.event_type === 'run_started') {
      if (current) runs.push(current);
      current = {
        id: ev.id,
        startedAt: ev.created_at,
        completedAt: null,
        status: 'running',
        sourceCount: null,
        postCount: null,
        signalCount: null,
        gapCount: null,
        events: [ev],
      };
    } else if (current && RUN_MEMBER_TYPES.has(ev.event_type)) {
      current.events.push(ev);
      if (ev.event_type === 'sources_scanned') {
        current.sourceCount = (ev.metadata?.success_count ?? ev.metadata?.source_count) as number ?? null;
        current.postCount = ev.metadata?.post_count as number ?? null;
      } else if (ev.event_type === 'signals_extracted') {
        current.signalCount = ev.metadata?.signal_count as number ?? null;
      } else if (ev.event_type === 'gaps_synthesized') {
        current.gapCount = ev.metadata?.gap_count as number ?? null;
      } else if (ev.event_type === 'run_completed') {
        current.completedAt = ev.created_at;
        current.status = 'done';
      }
    } else {
      standalone.push(ev);
    }
  }
  if (current) runs.push(current);

  runs.reverse();
  standalone.reverse();

  // Older runs that never reached run_completed are considered failed
  runs.forEach((run, i) => {
    if (run.status === 'running' && i > 0) run.status = 'failed';
  });

  return { runs, standalone };
}

// ── Run card ──────────────────────────────────────────────────────────────────

const RUN_EVENT_META: Record<string, { label: string; dotCls: string; textCls: string }> = {
  run_started:       { label: 'Started',            dotCls: 'bg-violet-400',  textCls: 'text-violet-400' },
  sources_scanned:   { label: 'Sources scanned',    dotCls: 'bg-sky-400',     textCls: 'text-sky-400' },
  posts_filtered:    { label: 'Posts reviewed',     dotCls: 'bg-slate-500',   textCls: 'text-slate-500' },
  signals_extracted: { label: 'Findings extracted', dotCls: 'bg-amber-400',   textCls: 'text-amber-400' },
  clusters_formed:   { label: 'Patterns formed',    dotCls: 'bg-indigo-400',  textCls: 'text-indigo-400' },
  gaps_synthesized:  { label: 'Opportunities found', dotCls: 'bg-emerald-400', textCls: 'text-emerald-400' },
  run_completed:     { label: 'Completed',           dotCls: 'bg-emerald-400', textCls: 'text-emerald-400' },
  source_failed:     { label: 'Source error',        dotCls: 'bg-rose-400',    textCls: 'text-rose-400' },
};

function runEventMeta(t: string) {
  return RUN_EVENT_META[t] ?? { label: t.replace(/_/g, ' '), dotCls: 'bg-slate-700', textCls: 'text-slate-600' };
}

function statLine(run: RunGroup): string | null {
  const parts: string[] = [];
  if (run.sourceCount != null) parts.push(`${run.sourceCount} source${run.sourceCount !== 1 ? 's' : ''}`);
  if (run.postCount != null) parts.push(`${run.postCount} post${run.postCount !== 1 ? 's' : ''}`);
  if (run.signalCount != null) parts.push(`${run.signalCount} finding${run.signalCount !== 1 ? 's' : ''}`);
  if (run.gapCount != null) parts.push(`${run.gapCount} gap${run.gapCount !== 1 ? 's' : ''}`);
  return parts.length > 0 ? parts.join(' · ') : null;
}

function RunCard({ run }: { run: RunGroup }) {
  const [expanded, setExpanded] = useState(false);
  const time = relativeTime(run.startedAt);
  const stats = statLine(run);

  const statusDot =
    run.status === 'done'
      ? 'bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.45)]'
      : run.status === 'failed'
      ? 'bg-rose-400 shadow-[0_0_5px_rgba(251,113,133,0.45)]'
      : 'animate-pulse bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.5)]';

  const statusLabel =
    run.status === 'done' ? 'Done' : run.status === 'failed' ? 'Failed' : 'Running';

  return (
    <div className="overflow-hidden rounded-xl border border-slate-800/70 bg-slate-900/30">
      <div className="flex items-center justify-between px-5 py-3.5">
        <div className="flex items-center gap-3">
          <span className={`h-2 w-2 shrink-0 rounded-full ${statusDot}`} />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-200">{statusLabel}</span>
              {time && <span className="text-[11px] text-slate-600">· {time}</span>}
            </div>
            {stats && <p className="mt-0.5 text-xs text-slate-500">{stats}</p>}
          </div>
        </div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="text-[11px] text-slate-600 transition hover:text-slate-400"
        >
          {expanded ? 'Hide ▲' : 'Details ▼'}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-white/[0.05] px-5 pb-3 pt-2">
          {run.events.map((ev, i) => {
            const meta = runEventMeta(ev.event_type);
            const t = relativeTime(ev.created_at);
            return (
              <div key={ev.id} className="flex gap-4 py-2">
                <div className="relative flex flex-col items-center">
                  <span className={`mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full ${meta.dotCls}`} />
                  {i < run.events.length - 1 && (
                    <span className="mt-1.5 w-px flex-1 bg-slate-800/60" />
                  )}
                </div>
                <div className="min-w-0 flex-1 pb-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className={`text-[10px] font-semibold uppercase tracking-wider ${meta.textCls}`}>{meta.label}</p>
                    {t && <span className="text-[10px] text-slate-700">{t}</span>}
                  </div>
                  {ev.detail && <p className="mt-0.5 text-xs text-slate-500">{ev.detail}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Standalone events ─────────────────────────────────────────────────────────

const STANDALONE_META: Record<string, { label: string; dotCls: string; textCls: string }> = {
  alert_created:      { label: 'Alert created',      dotCls: 'bg-amber-400 shadow-[0_0_5px_rgba(251,191,36,0.5)]',  textCls: 'text-amber-400' },
  source_failed:      { label: 'Source error',        dotCls: 'bg-rose-400 shadow-[0_0_5px_rgba(251,113,133,0.5)]',  textCls: 'text-rose-400' },
  feedback_recorded:  { label: 'Feedback recorded',   dotCls: 'bg-violet-400/60',                                    textCls: 'text-violet-500' },
  preferences_updated:{ label: 'Preferences updated', dotCls: 'bg-slate-500',                                         textCls: 'text-slate-500' },
};

function standaloneMeta(eventType: string) {
  return STANDALONE_META[eventType] ?? { label: eventType.replace(/_/g, ' '), dotCls: 'bg-slate-700', textCls: 'text-slate-600' };
}

function StandaloneItem({ item, isLast }: { item: AgentActivity; isLast?: boolean }) {
  const meta = standaloneMeta(item.event_type);
  const time = relativeTime(item.created_at);
  return (
    <div className="flex gap-4 py-3">
      <div className="relative flex flex-col items-center">
        <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${meta.dotCls}`} />
        {!isLast && <span className="mt-1.5 w-px flex-1 bg-slate-800/60" />}
      </div>
      <div className="min-w-0 flex-1 pb-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className={`text-[10px] font-semibold uppercase tracking-wider ${meta.textCls}`}>{meta.label}</p>
          {time && <span className="text-[11px] text-slate-700">{time}</span>}
        </div>
        <p className="mt-0.5 text-sm font-medium text-slate-300">{item.title}</p>
        {item.detail && <p className="mt-1 text-xs leading-relaxed text-slate-500">{item.detail}</p>}
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function NicheActivityPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [activity, setActivity] = useState<AgentActivity[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, activityRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getMarketAgentActivity(marketId),
      ]);
      setNiche(market);
      setActivity(activityRes.activity);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load activity');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const seenIdsRef = useRef<Set<string>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await signalApi.getMarketAgentActivity(marketId);
        if (cancelled) return;
        const newItems = res.activity.filter(a => !seenIdsRef.current.has(a.id));
        if (newItems.length === 0) return;
        newItems.forEach(a => seenIdsRef.current.add(a.id));
        setActivity(prev => {
          const existingIds = new Set(prev.map(a => a.id));
          const truly = newItems.filter(a => !existingIds.has(a.id));
          return truly.length > 0 ? [...truly, ...prev] : prev;
        });
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

  const { runs, standalone } = groupIntoRuns(activity);
  const hasContent = runs.length > 0 || standalone.length > 0;

  return (
    <DashboardShell
      title="Activity"
      subtitle={`${niche?.name ?? 'This niche'} agent run history and events.`}
      actions={<NicheViewSwitcher marketId={marketId} active="activity" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading activity" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-4 animate-fade-in">
          <AgentInbox marketId={marketId} />

          <div className="flex items-center justify-between">
            <div />
            <Link
              href={`/markets/${encodeURIComponent(marketId)}/sources`}
              className="text-[11px] text-slate-600 transition hover:text-slate-400"
            >
              Research coverage →
            </Link>
          </div>

          {!hasContent ? (
            <EmptyPanel
              title="No activity yet"
              detail="Run history and agent events appear here after the first scan."
            />
          ) : (
            <>
              {runs.length > 0 && (
                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Run history</p>
                    <Link href={`/markets/${encodeURIComponent(marketId)}/reports`} className="text-[11px] text-slate-600 transition hover:text-slate-400">Latest report →</Link>
                  </div>
                  {runs.map(run => <RunCard key={run.id} run={run} />)}
                </section>
              )}

              {standalone.length > 0 && (
                <section>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Other events</p>
                  <div className="rounded-xl border border-slate-800/70 bg-slate-900/30 px-5 pb-1 pt-2">
                    {standalone.map((item, i) => (
                      <StandaloneItem key={item.id} item={item} isLast={i === standalone.length - 1} />
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      )}
    </DashboardShell>
  );
}
