'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import { EmptyPanel, ErrorPanel, LoadingPanel, Metric, ScoreBadge } from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { SignalCluster } from '@/lib/types/signals';

type Status = 'loading' | 'ready' | 'error';

function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export default function ThemesPage() {
  const [themes, setThemes] = useState<SignalCluster[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const res = await signalApi.getClusters();
      setThemes(res.clusters);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load themes');
      setStatus('error');
    }
  };

  useEffect(() => { load(); }, []);

  const avgScore =
    themes.length > 0
      ? themes.reduce((s, t) => s + t.average_score, 0) / themes.length
      : 0;

  return (
    <DashboardShell
      title="Themes"
      subtitle="Recurring pain patterns grouped from extracted findings"
      actions={
        <button
          onClick={load}
          disabled={status === 'loading'}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-800/60 px-3 py-2 text-xs font-semibold text-slate-300 shadow-sm transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100 disabled:opacity-50"
        >
          <RefreshIcon />
          Refresh
        </button>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading themes" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Themes" value={themes.length} />
            <Metric label="Avg strength" value={avgScore.toFixed(1)} accent={avgScore >= 6} />
            <Metric
              label="Total mentions"
              value={themes.reduce((s, t) => s + t.frequency, 0)}
            />
          </div>

          {themes.length === 0 ? (
            <EmptyPanel
              title="No themes identified yet"
              detail="Themes appear after background scans group recurring findings."
            />
          ) : (
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/40">
              <div className="grid grid-cols-[1fr_80px_80px_32px] items-center gap-x-4 border-b border-slate-800/80 px-5 py-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
                <span>Theme</span>
                <span>Findings</span>
                <span>Mentions</span>
                <span />
              </div>

              {themes.map((theme, i) => (
                <Link
                  key={theme.id}
                  href={`/themes/${encodeURIComponent(theme.id)}`}
                  className={`grid grid-cols-[1fr_80px_80px_32px] items-center gap-x-4 px-5 py-3.5 text-sm transition-colors hover:bg-white/[0.02] ${i > 0 ? 'border-t border-slate-800/50' : ''}`}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-200">{theme.theme}</p>
                    {theme.summary && (
                      <p className="mt-0.5 truncate text-xs text-slate-600">{theme.summary}</p>
                    )}
                  </div>
                  <span className="tabular-nums text-xs text-slate-500">
                    {theme.signal_ids.length}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums text-xs text-slate-500">{theme.frequency}</span>
                    <ScoreBadge value={theme.average_score} />
                  </div>
                  <span className="text-slate-700">
                    <ChevronIcon />
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}
