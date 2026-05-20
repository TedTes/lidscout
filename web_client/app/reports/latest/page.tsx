'use client';

import { useEffect, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import {
  ClusterLink,
  EmptyPanel,
  ErrorPanel,
  LoadingPanel,
  Metric,
  ScoreBadge,
} from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { MarketSignalReport } from '@/lib/types/signals';

type Status = 'loading' | 'ready' | 'error';

export default function LatestReportPage() {
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
      title="Latest report"
      subtitle={report ? `Generated ${formatDate(report.generated_at)}` : undefined}
      actions={
        <button
          onClick={load}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:border-sky-300 hover:text-sky-700"
        >
          Refresh
        </button>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading latest report" />}
      {status === 'error' && error && <ErrorPanel message={error} />}
      {status === 'ready' && report && (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="Top clusters" value={report.top_clusters.length} />
            <Metric label="Emerging pains" value={report.emerging_pains.length} />
            <Metric label="Opportunities" value={report.recommended_opportunities.length} />
          </div>

          <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900">Ranked clusters</h2>
            {report.top_clusters.length === 0 ? (
              <EmptyPanel title="No clusters in report" detail="Run the pipeline to generate report content." />
            ) : (
              <div className="mt-3 divide-y divide-gray-100">
                {report.top_clusters.map(cluster => (
                  <div key={cluster.id} className="py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-semibold text-gray-900">
                        <ClusterLink id={cluster.id}>{cluster.theme}</ClusterLink>
                      </h3>
                      <ScoreBadge value={cluster.average_score} />
                    </div>
                    <p className="mt-1 text-sm text-gray-600">{cluster.summary}</p>
                    <p className="mt-1 text-xs text-gray-400">{cluster.frequency} mentions</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="grid gap-5 lg:grid-cols-2">
            <ReportList title="Emerging pains" items={report.emerging_pains} />
            <ReportList title="Recommended opportunities" items={report.recommended_opportunities} />
          </div>
        </div>
      )}
    </DashboardShell>
  );
}

function ReportList({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-gray-500">No items available.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className="rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-700">
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
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
