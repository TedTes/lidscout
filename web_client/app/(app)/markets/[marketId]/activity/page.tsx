'use client';

import { useEffect, useRef, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ErrorPanel, LoadingPanel, StatRow, relativeTime } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { AgentActivity, Market } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

const EVENT_META: Record<string, { label: string; dotCls: string; textCls: string }> = {
  run_started:         { label: 'Run started',          dotCls: 'bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.5)] animate-pulse', textCls: 'text-violet-400' },
  sources_scanned:     { label: 'Sources scanned',       dotCls: 'bg-sky-400 shadow-[0_0_5px_rgba(56,189,248,0.5)]',    textCls: 'text-sky-400' },
  posts_filtered:      { label: 'Posts filtered',        dotCls: 'bg-slate-500',                                         textCls: 'text-slate-500' },
  signals_extracted:   { label: 'Signals extracted',     dotCls: 'bg-amber-400 shadow-[0_0_5px_rgba(251,191,36,0.5)]',  textCls: 'text-amber-400' },
  clusters_formed:     { label: 'Themes formed',         dotCls: 'bg-indigo-400 shadow-[0_0_5px_rgba(129,140,248,0.5)]', textCls: 'text-indigo-400' },
  gaps_synthesized:    { label: 'Gaps identified',       dotCls: 'bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.5)]', textCls: 'text-emerald-400' },
  run_completed:       { label: 'Run completed',         dotCls: 'bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.5)]', textCls: 'text-emerald-400' },
  source_failed:       { label: 'Source failed',         dotCls: 'bg-rose-400 shadow-[0_0_5px_rgba(251,113,133,0.5)]',   textCls: 'text-rose-400' },
  alert_created:       { label: 'Alert created',         dotCls: 'bg-amber-400 shadow-[0_0_5px_rgba(251,191,36,0.5)]',  textCls: 'text-amber-400' },
  feedback_recorded:   { label: 'Feedback recorded',     dotCls: 'bg-violet-400/60',                                      textCls: 'text-violet-500' },
  preferences_updated: { label: 'Preferences updated',   dotCls: 'bg-slate-500',                                          textCls: 'text-slate-500' },
};

function eventMeta(eventType: string) {
  return EVENT_META[eventType] ?? { label: eventType.replace(/_/g, ' '), dotCls: 'bg-slate-700', textCls: 'text-slate-600' };
}

function ActivityItem({ item, isLast }: { item: AgentActivity; isLast?: boolean }) {
  const meta = eventMeta(item.event_type);
  const time = relativeTime(item.created_at);

  return (
    <div className="flex gap-4 py-4">
      <div className="relative flex flex-col items-center">
        <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${meta.dotCls}`} />
        {!isLast && <span className="mt-1.5 flex-1 w-px bg-slate-800/60" />}
      </div>
      <div className="min-w-0 flex-1 pb-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className={`text-[10px] font-semibold uppercase tracking-wider ${meta.textCls}`}>
            {meta.label}
          </p>
          {time && (
            <span className="text-[11px] text-slate-700">{time}</span>
          )}
        </div>
        <p className="mt-0.5 text-sm font-medium text-slate-300">{item.title}</p>
        {item.detail && (
          <p className="mt-1 text-xs leading-relaxed text-slate-500">{item.detail}</p>
        )}
      </div>
    </div>
  );
}

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

  // Append-only poll — only updates state when there are genuinely new events
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
      } catch {
        // ignore
      }
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const runCount = activity.filter(a => a.event_type === 'run_completed').length;
  const failCount = activity.filter(a => a.event_type === 'source_failed').length;

  return (
    <DashboardShell
      title="Activity"
      subtitle={`${niche?.name ?? 'This niche'} agent run history and events.`}
      actions={<NicheViewSwitcher marketId={marketId} active="activity" onRefresh={load} refreshing={status === 'loading'} />}
    >
      {status === 'loading' && <LoadingPanel label="Loading activity" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <StatRow compact stats={[
            { label: 'Events', value: activity.length },
            { label: 'Runs completed', value: runCount },
            { label: 'Source failures', value: failCount, danger: failCount > 0 },
          ]} />

          {activity.length > 0 && (
            <div className="rounded-xl border border-slate-800/70 bg-slate-900/40 px-5 pt-2 pb-1">
              {activity.map((item, i) => (
                <ActivityItem key={item.id} item={item} isLast={i === activity.length - 1} />
              ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}
