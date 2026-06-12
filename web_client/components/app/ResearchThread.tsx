'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { relativeTime } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import type { AgentAction, AgentFollowUp } from '@/lib/types/signals';

const CHIPS = [
  'Why is this credible?',
  'What evidence is strongest?',
  'Which users feel this most?',
  'What would invalidate this?',
  'Find more like this',
];

type Props = { marketId: string };

const ACTION_META: Record<string, { label: string; dotCls: string; approveLabel?: string }> = {
  pause_source:           { label: 'Pause noisy source',      dotCls: 'bg-rose-400',    approveLabel: 'Approve' },
  suggest_source:         { label: 'Add better source',       dotCls: 'bg-sky-400',     approveLabel: 'Approve' },
  send_alert:             { label: 'Send alert',              dotCls: 'bg-amber-400',   approveLabel: 'Approve' },
  scan_sources:           { label: 'Run source scan',         dotCls: 'bg-emerald-400', approveLabel: 'Approve' },
  source_needs_attention: { label: 'Source needs attention',  dotCls: 'bg-amber-400' },
  answer_follow_up:       { label: 'Follow-up queued',        dotCls: 'bg-blue-400' },
  wait:                   { label: 'No action needed',        dotCls: 'bg-slate-500' },
};

function actionMeta(type: string) {
  return ACTION_META[type] ?? { label: type.replace(/_/g, ' '), dotCls: 'bg-slate-500' };
}

export default function ResearchThread({ marketId }: Props) {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [items, setItems] = useState<AgentFollowUp[]>([]);
  const [ready, setReady] = useState(false);
  const [text, setText] = useState('');
  const [pending, setPending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setReady(false);
      await signalApi.proposeMarketAgentActions(marketId).catch(() => null);
      const [actionsRes, followUpsRes] = await Promise.all([
        signalApi.getMarketAgentActions(marketId, { status: 'proposed', limit: 25 }),
        signalApi.getMarketAgentFollowUps(marketId),
      ]);
      if (cancelled) return;
      setActions(
        (actionsRes.actions ?? []).filter(action => action.action_type !== 'wait')
      );
      setItems((followUpsRes.follow_ups ?? []).filter(f => f.status !== 'dismissed'));
      setReady(true);
    }

    load()
      .catch(() => {
        if (cancelled) return;
        setActions([]);
        setItems([]);
        setReady(true);
      });
    return () => { cancelled = true; };
  }, [marketId]);

  const handleAsk = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    const q = text.trim();
    if (!q || pending) return;
    setPending(true);
    try {
      const followUp = await signalApi.createMarketAgentFollowUp(marketId, { question: q });
      setItems(prev => [...prev, followUp]);
      setText('');
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch { /* silent */ } finally {
      setPending(false);
    }
  }, [marketId, text, pending]);

  const handleApprove = useCallback((action: AgentAction) => {
    setActions(prev => prev.filter(a => a.id !== action.id));
    signalApi.approveAgentAction(marketId, action.id).catch(() => {});
  }, [marketId]);

  const handleDismissAction = useCallback((action: AgentAction) => {
    setActions(prev => prev.filter(a => a.id !== action.id));
    signalApi.dismissAgentAction(marketId, action.id).catch(() => {});
  }, [marketId]);

  const hasContent = actions.length > 0 || items.length > 0;

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-slate-700/40 bg-slate-900/40">

      {/* header */}
      <div className="flex items-center gap-2 border-b border-white/[0.04] px-4 py-2.5">
        <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.45)]" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-400">Research agent</span>
      </div>

      {/* thread */}
      <div className="max-h-[400px] overflow-y-auto">
        {ready && !hasContent && (
          <p className="px-4 py-4 text-[11px] text-slate-600">Ask anything about this market.</p>
        )}

        {ready && hasContent && (
          <div className="divide-y divide-white/[0.03]">
            {actions.map(action => {
              const meta = actionMeta(action.action_type);
              const sourceLocator = typeof action.metadata?.locator === 'string'
                ? action.metadata.locator
                : null;
              const canApprove = !!meta.approveLabel;

              return (
                <div key={action.id} className="flex items-start gap-3 px-4 py-3">
                  <span className={`mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full ${meta.dotCls}`} />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-slate-200">{meta.label}</p>
                    {action.reason && (
                      <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{action.reason}</p>
                    )}
                    {sourceLocator && (
                      <p className="mt-0.5 truncate text-[10px] text-slate-600">{sourceLocator}</p>
                    )}
                    {action.created_at && (
                      <p className="mt-0.5 text-[10px] text-slate-700">{relativeTime(action.created_at)}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {canApprove && (
                      <button
                        type="button"
                        onClick={() => handleApprove(action)}
                        className="rounded-md border border-violet-500/25 bg-violet-500/10 px-2.5 py-1 text-[11px] font-semibold text-violet-300 transition hover:bg-violet-500/20"
                      >
                        {meta.approveLabel}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDismissAction(action)}
                      className="rounded-md border border-slate-700/50 px-2 py-1 text-[11px] text-slate-500 transition hover:text-slate-300"
                    >
                      {canApprove ? 'Skip' : 'Dismiss'}
                    </button>
                  </div>
                </div>
              );
            })}

            {items.map(fu => (
              <div key={fu.id} className="px-4 py-3 space-y-1.5">
                <p className="text-xs font-medium leading-relaxed text-slate-200">{fu.question}</p>

                {fu.status === 'answered' && fu.response && (
                  <p className="text-[11px] leading-relaxed text-slate-400">{fu.response}</p>
                )}

                {fu.status === 'queued' && (
                  <p className="flex items-center gap-1.5 text-[10px] text-slate-600">
                    <span className="h-1 w-1 animate-pulse rounded-full bg-slate-600" />
                    Pending · answers on next run
                  </p>
                )}

                {fu.created_at && (
                  <p className="text-[10px] text-slate-700">{relativeTime(fu.created_at)}</p>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ask form */}
      <div className="border-t border-white/[0.04] px-4 py-3 space-y-2">
        <form onSubmit={handleAsk} className="flex items-center gap-2">
          <input
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Ask about this market…"
            className="min-w-0 flex-1 rounded-lg border border-slate-700/60 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:border-violet-500/40 focus:outline-none transition"
          />
          <button
            type="submit"
            disabled={pending || !text.trim()}
            className="shrink-0 rounded-md border border-violet-500/25 bg-violet-500/10 px-3 py-1.5 text-[11px] font-semibold text-violet-300 transition hover:bg-violet-500/20 disabled:opacity-40"
          >
            {pending ? '…' : 'Ask'}
          </button>
        </form>

        <div className="flex flex-wrap gap-1.5">
          {CHIPS.map(chip => (
            <button
              key={chip}
              type="button"
              onClick={() => setText(chip)}
              className="rounded-full border border-slate-700/50 px-2 py-0.5 text-[10px] text-slate-500 transition hover:border-violet-500/30 hover:text-violet-400"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

    </div>
  );
}
