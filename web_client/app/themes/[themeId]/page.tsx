'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import {
  Chip,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
  SectionCard,
  UrgencyBadge,
} from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Signal, SignalCluster } from '@/lib/types/signals';

type Props = { params: { themeId: string } };
type Status = 'loading' | 'ready' | 'error';

function BackIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

export default function ThemeDetailPage({ params }: Props) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setStatus('loading');
      setError(null);
      try {
        const [signalsData, clustersData] = await Promise.all([
          signalApi.getSignals(),
          signalApi.getClusters(),
        ]);
        setSignals(signalsData.signals);
        setClusters(clustersData.clusters);
        setStatus('ready');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load theme');
        setStatus('error');
      }
    };
    load();
  }, []);

  const theme = clusters.find(c => c.id === decodeURIComponent(params.themeId));

  const relatedSignals = useMemo(() => {
    if (!theme) return [];
    const ids = new Set(theme.signal_ids);
    return signals.filter(s => ids.has(s.id));
  }, [theme, signals]);

  return (
    <DashboardShell
      title={theme?.theme ?? 'Theme detail'}
      subtitle={theme?.summary}
      actions={
        <Link
          href="/themes"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-800/60 px-3 py-2 text-xs font-semibold text-slate-300 shadow-sm transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100"
        >
          <BackIcon />
          All themes
        </Link>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading theme" />}
      {status === 'error' && error && <ErrorPanel message={error} />}
      {status === 'ready' && !theme && (
        <EmptyPanel
          title="Theme not found"
          detail="The theme may no longer exist in the latest dataset."
        />
      )}

      {theme && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Mentions" value={theme.frequency} />
            <Metric label="Findings" value={theme.signal_ids.length} />
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">
                Avg strength
              </p>
              <div className="mt-2.5">
                <ScoreBadge value={theme.average_score} />
              </div>
            </div>
          </div>

          <SectionCard title="Top examples">
            {theme.top_examples.length === 0 ? (
              <p className="text-sm text-slate-600">No examples saved for this theme.</p>
            ) : (
              <div className="space-y-2">
                {theme.top_examples.map((example, i) => (
                  <div
                    key={i}
                    className="flex gap-3 rounded-lg border border-slate-800/60 bg-slate-800/30 px-4 py-3"
                  >
                    <span className="mt-0.5 shrink-0 text-xs font-bold tabular-nums text-slate-700">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <p className="text-sm leading-relaxed text-slate-400">{example}</p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title={`Related findings (${relatedSignals.length})`}>
            {relatedSignals.length === 0 ? (
              <p className="text-sm text-slate-600">No related findings currently available.</p>
            ) : (
              <div className="space-y-2">
                {relatedSignals.map(signal => (
                  <div
                    key={signal.id}
                    className="flex overflow-hidden rounded-lg border border-slate-800/60 transition-colors hover:border-slate-700/80"
                  >
                    <div
                      className={`w-0.5 shrink-0 ${
                        signal.urgency === 'high'
                          ? 'bg-rose-500'
                          : signal.urgency === 'medium'
                            ? 'bg-amber-500'
                            : 'bg-slate-700'
                      }`}
                    />
                    <div className="flex-1 px-4 py-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <p className="font-medium leading-snug text-slate-200">{signal.pain}</p>
                        <ScoreBadge value={signal.confidence * 10} />
                      </div>
                      {signal.evidence_text && (
                        <p className="mt-1.5 rounded-md border border-slate-800/40 bg-slate-800/20 px-3 py-2 text-xs leading-relaxed text-slate-500 italic">
                          &ldquo;{signal.evidence_text}&rdquo;
                        </p>
                      )}
                      {signal.current_workaround && (
                        <p className="mt-1 text-xs text-slate-500">
                          ↪ {signal.current_workaround}
                        </p>
                      )}
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <UrgencyBadge urgency={signal.urgency} />
                        {signal.category && <Chip label={signal.category} />}
                        {signal.user_type && <Chip label={signal.user_type} />}
                        {signal.willingness_to_pay && (
                          <span className="rounded-md border border-emerald-500/20 bg-emerald-500/[0.07] px-2 py-0.5 text-xs font-medium text-emerald-400">
                            WTP
                          </span>
                        )}
                        {signal.evidence_url && (
                          <a
                            href={signal.evidence_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ml-auto inline-flex items-center gap-1 rounded-md bg-slate-800/50 px-2 py-0.5 text-xs text-slate-600 transition hover:text-slate-400"
                          >
                            <LinkIcon />
                            Source
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}
    </DashboardShell>
  );
}
