'use client';

import { useEffect, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import {
  ClusterLink,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
  SectionCard,
} from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { MarketSignalReport, Opportunity } from '@/lib/types/signals';

type Status = 'loading' | 'ready' | 'error';

function RefreshIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function TrendingIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  );
}

function LightbulbIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="9" y1="18" x2="15" y2="18" />
      <line x1="10" y1="22" x2="14" y2="22" />
      <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
    </svg>
  );
}

export default function ReportsPage() {
  const [report, setReport] = useState<MarketSignalReport | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      setReport(await signalApi.getLatestReport());
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <DashboardShell
      title="Report"
      subtitle={report ? `Generated ${formatDate(report.generated_at)} · all companies` : undefined}
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
      {status === 'loading' && <LoadingPanel label="Loading latest report" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && report && (
        <div className="space-y-5 animate-fade-in">
          {/* Metrics */}
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Top themes" value={report.top_clusters.length} />
            <Metric label="Emerging pains" value={report.emerging_pains.length} />
            <Metric label="Gaps" value={report.recommended_opportunities.length} accent />
          </div>

          {/* Ranked clusters */}
          <SectionCard title="Ranked themes">
            {report.top_clusters.length === 0 ? (
              <EmptyPanel
                title="No themes in report"
                detail="Reports populate after background scans collect and group findings."
              />
            ) : (
              <div className="space-y-2">
                {report.top_clusters.map((cluster, i) => (
                  <div
                    key={cluster.id}
                    className="flex gap-4 rounded-lg border border-slate-800/60 bg-slate-800/20 px-4 py-3.5 transition-colors hover:border-slate-700/80"
                  >
                    {/* Rank number */}
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-bold tabular-nums text-slate-500">
                      {i + 1}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="font-semibold text-slate-200">
                          <ClusterLink id={cluster.id}>{cluster.theme}</ClusterLink>
                        </h3>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-600">{cluster.frequency} mentions</span>
                          <ScoreBadge value={cluster.average_score} />
                        </div>
                      </div>
                      {cluster.summary && (
                        <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
                          {cluster.summary}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          {/* Two-column grid */}
          <div className="grid gap-5 lg:grid-cols-2">
            <InsightList
              title="Emerging pains"
              items={report.emerging_pains}
              icon={<TrendingIcon />}
              iconColor="text-rose-400"
              emptyMessage="No emerging pains identified."
            />
            <InsightList
              title="Recommended gaps"
              items={[]}
              icon={<LightbulbIcon />}
              iconColor="text-amber-400"
              emptyMessage="No gaps recommended yet."
              renderItems={() => (
                <OpportunityList opportunities={report.recommended_opportunities} />
              )}
            />
          </div>
        </div>
      )}
    </DashboardShell>
  );
}

function InsightList({
  title,
  items,
  icon,
  iconColor,
  emptyMessage,
  renderItems,
}: {
  title: string;
  items: string[];
  icon: React.ReactNode;
  iconColor: string;
  emptyMessage: string;
  renderItems?: () => React.ReactNode;
}) {
  const count = renderItems ? undefined : items.length;
  return (
    <section className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
      <div className="mb-4 flex items-center gap-2">
        <span className={iconColor}>{icon}</span>
        <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
        {(count ?? 0) > 0 && (
          <span className="ml-auto rounded-full bg-slate-800 px-2 py-0.5 text-xs tabular-nums text-slate-500">
            {count}
          </span>
        )}
      </div>

      {renderItems ? (
        renderItems()
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-600">{emptyMessage}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li
              key={`${item}-${i}`}
              className="flex gap-3 rounded-lg border border-slate-800/60 bg-slate-800/30 px-3 py-2.5"
            >
              <span className="mt-0.5 shrink-0 text-[10px] font-bold tabular-nums text-slate-700">
                {String(i + 1).padStart(2, '0')}
              </span>
              <p className="text-sm leading-relaxed text-slate-400">{item}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function OpportunityList({ opportunities }: { opportunities: Opportunity[] }) {
  if (opportunities.length === 0) {
    return <p className="text-sm text-slate-600">No gaps recommended yet.</p>;
  }

  return (
    <ul className="space-y-2">
      {opportunities.map((opportunity, i) => (
        <li
          key={opportunity.id}
          className="rounded-lg border border-slate-800/60 bg-slate-800/30 px-3 py-2.5"
        >
          <div className="flex items-start gap-3">
            <span className="mt-0.5 shrink-0 text-[10px] font-bold tabular-nums text-slate-700">
              {String(i + 1).padStart(2, '0')}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold leading-relaxed text-slate-300">
                  {opportunity.title}
                </p>
                <span className="rounded-md bg-slate-800 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                  {opportunity.evidence_count} evidence
                </span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
                {opportunity.suggested_wedge}
              </p>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}
