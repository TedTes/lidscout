'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { relativeTime } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import type { AgentAction, AgentFollowUp } from '@/lib/types/signals';

type Props = { marketId: string };

const ACTION_META: Record<string, { label: string; dotCls: string; approveLabel: string }> = {
  pause_source:      { label: 'Pause source',       dotCls: 'bg-rose-400',   approveLabel: 'Approve' },
  suggest_source:   { label: 'Improve sources',    dotCls: 'bg-sky-400',    approveLabel: 'Approve' },
  send_alert:       { label: 'Send alert',         dotCls: 'bg-amber-400',  approveLabel: 'Approve' },
  answer_follow_up: { label: 'Answer follow-up',   dotCls: 'bg-blue-400',   approveLabel: 'Approve' },
  scan_sources:     { label: 'Scan sources',       dotCls: 'bg-emerald-400', approveLabel: 'Approve' },
  wait:             { label: 'No action needed',   dotCls: 'bg-slate-500',  approveLabel: 'Approve' },
};

function actionMeta(type: string) {
  return ACTION_META[type] ?? { label: type, dotCls: 'bg-slate-500', approveLabel: 'Approve' };
}

export default function AgentInbox({ marketId }: Props) {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [followUps, setFollowUps] = useState<AgentFollowUp[]>([]);
  const [ready, setReady] = useState(false);
  const [askText, setAskText] = useState('');
  const [askOpen, setAskOpen] = useState(false);
  const [askPending, setAskPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      signalApi.proposeMarketAgentActions(marketId).catch(() => null),
      signalApi.getMarketAgentFollowUps(marketId).catch(() => null),
    ]).then(([plan, fuRes]) => {
      if (cancelled) return;
      setActions(plan?.actions ?? []);
      setFollowUps(
        (fuRes?.follow_ups ?? []).filter(f => f.status === 'queued')
      );
      setReady(true);
    });
    return () => { cancelled = true; };
  }, [marketId]);

  const handleApprove = useCallback((action: AgentAction) => {
    setActions(prev => prev.filter(a => a.id !== action.id));
    signalApi.approveAgentAction(marketId, action.id).catch(() => {});
  }, [marketId]);

  const handleDismissAction = useCallback((action: AgentAction) => {
    setActions(prev => prev.filter(a => a.id !== action.id));
    signalApi.dismissAgentAction(marketId, action.id).catch(() => {});
  }, [marketId]);

  const handleSkipFollowUp = useCallback((id: string) => {
    setFollowUps(prev => prev.filter(f => f.id !== id));
  }, []);

  const handleAsk = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    const q = askText.trim();
    if (!q || askPending) return;
    setAskPending(true);
    try {
      const followUp = await signalApi.createMarketAgentFollowUp(marketId, { question: q });
      setFollowUps(prev => [followUp, ...prev]);
      setAskText('');
      setAskOpen(false);
    } catch { /* silent */ } finally {
      setAskPending(false);
    }
  }, [marketId, askText, askPending]);

  if (!ready) return null;

  const totalPending = actions.length + followUps.length;

  return (
    <div className="overflow-hidden rounded-xl border border-violet-500/20 bg-violet-500/[0.03]">
      {totalPending > 0 && (
        <div className="flex items-center gap-2 border-b border-white/[0.04] px-4 py-2">
          <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_5px_rgba(167,139,250,0.45)]" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-400">
            Agent · {totalPending} {totalPending === 1 ? 'item' : 'items'}
          </span>
        </div>
      )}

      {totalPending > 0 && (
        <div className="divide-y divide-white/[0.03]">
          {actions.map(action => {
            const meta = actionMeta(action.action_type);
            const sourceLocator = typeof action.metadata?.locator === 'string'
              ? action.metadata.locator
              : null;
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
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <button
                    onClick={() => handleApprove(action)}
                    className="rounded-md border border-violet-500/25 bg-violet-500/10 px-2.5 py-1 text-[11px] font-semibold text-violet-300 transition hover:bg-violet-500/20"
                  >
                    {meta.approveLabel}
                  </button>
                  <button
                    onClick={() => handleDismissAction(action)}
                    className="rounded-md border border-slate-700/50 px-2 py-1 text-[11px] text-slate-500 transition hover:text-slate-300"
                  >
                    Skip
                  </button>
                </div>
              </div>
            );
          })}

          {followUps.map(fu => {
            return (
              <div key={fu.id} className="px-4 py-3">
                <div className="flex items-start gap-3">
                  <span className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-400/80">Queued question</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-slate-300">"{fu.question}"</p>
                    {fu.created_at && (
                      <p className="mt-0.5 text-[10px] text-slate-600">{relativeTime(fu.created_at)}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <button
                      onClick={() => handleSkipFollowUp(fu.id)}
                      className="rounded-md border border-slate-700/50 px-2 py-1 text-[11px] text-slate-500 transition hover:text-slate-300"
                    >
                      Skip
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className={`px-4 py-2.5${totalPending > 0 ? ' border-t border-white/[0.04]' : ''}`}>
        {askOpen ? (
          <form onSubmit={handleAsk} className="flex items-center gap-2">
            <input
              autoFocus
              value={askText}
              onChange={e => setAskText(e.target.value)}
              placeholder="Ask the research agent…"
              className="min-w-0 flex-1 rounded-lg border border-slate-700/60 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:border-violet-500/40 focus:outline-none transition"
            />
            <button
              type="submit"
              disabled={askPending || !askText.trim()}
              className="whitespace-nowrap rounded-md border border-violet-500/25 bg-violet-500/10 px-3 py-1.5 text-[11px] font-semibold text-violet-300 transition hover:bg-violet-500/20 disabled:opacity-40"
            >
              {askPending ? '…' : 'Ask'}
            </button>
            <button
              type="button"
              onClick={() => { setAskOpen(false); setAskText(''); }}
              className="text-[11px] text-slate-600 transition hover:text-slate-400"
            >
              Cancel
            </button>
          </form>
        ) : (
          <button
            onClick={() => setAskOpen(true)}
            className="text-[11px] text-slate-600 transition hover:text-slate-400"
          >
            + Ask the research agent
          </button>
        )}
      </div>
    </div>
  );
}
