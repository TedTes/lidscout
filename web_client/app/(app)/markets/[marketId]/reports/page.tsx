'use client';

import { useEffect, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, MarketSignalReport } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

export default function NicheReportPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [report, setReport] = useState<MarketSignalReport | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, reportRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getLatestReport({ market_id: marketId }),
      ]);
      setNiche(market);
      setReport(reportRes);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  return (
    <DashboardShell
      title="Report"
      subtitle={`Latest evidence summary for ${niche?.name ?? 'this watchlist'}.`}
      actions={<NicheViewSwitcher marketId={marketId} />}
    >
      {status === 'loading' && <LoadingPanel label="Loading report" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && !report && (
        <EmptyPanel title="No report yet" detail="Reports appear after the background scan has enough findings to summarize." />
      )}

      {status === 'ready' && report && (
        <div className="space-y-5 animate-fade-in">
          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="border-b border-slate-800/70 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-300">Recommended gaps</h2>
            </div>
            {report.recommended_opportunities.length === 0 ? (
              <div className="p-5">
                <EmptyPanel title="No gaps recommended yet" />
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {report.recommended_opportunities.map(opportunity => (
                  <article key={opportunity.id} className="p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="font-semibold text-slate-100">{opportunity.title}</h3>
                        <p className="mt-1 text-sm leading-relaxed text-slate-500">{opportunity.pain_summary}</p>
                      </div>
                      <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-500">
                        {opportunity.evidence_count} evidence
                      </span>
                    </div>
                    {opportunity.suggested_wedge && (
                      <p className="mt-3 rounded-lg border border-violet-500/15 bg-violet-500/[0.04] px-3 py-2 text-xs leading-relaxed text-violet-300">
                        {opportunity.suggested_wedge}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="border-b border-slate-800/70 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-300">Top patterns</h2>
            </div>
            {report.top_clusters.length === 0 ? (
              <div className="p-5">
                <EmptyPanel title="No patterns in this report" />
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {report.top_clusters.map(cluster => (
                  <div key={cluster.id} className="flex flex-wrap items-center justify-between gap-3 p-5">
                    <div>
                      <ClusterLink id={cluster.id} marketId={marketId}>{cluster.theme}</ClusterLink>
                      <p className="mt-2 text-sm text-slate-500">{cluster.summary}</p>
                    </div>
                    <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-500">
                      {cluster.frequency} findings
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {report.emerging_pains.length > 0 && (
            <section className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
              <h2 className="mb-3 text-sm font-semibold text-slate-300">Emerging pains</h2>
              <div className="space-y-2">
                {report.emerging_pains.map((pain, index) => (
                  <p key={`${pain}-${index}`} className="rounded-lg bg-slate-950/35 px-3 py-2 text-sm text-slate-500">{pain}</p>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </DashboardShell>
  );
}
