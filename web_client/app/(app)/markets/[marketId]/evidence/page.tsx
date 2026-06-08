'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, EmptyPanel, ErrorPanel, LoadingPanel, ScoreBadge, UrgencyBadge } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { AccumulatedTheme, EvidenceItem, Market, Signal } from '@/lib/types/signals';

const FAMILY_LABELS: Record<string, string> = {
  technical_forum:  'Technical forums',
  technical_forums: 'Technical forums',
  social:           'Social',
  reviews:          'Reviews',
  owned_site:       'Owned',
  other:            'Other',
};
function familyLabel(f: string) { return FAMILY_LABELS[f] ?? f.replace(/_/g, ' '); }

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type EvidenceView = 'patterns' | 'findings';

export default function EvidencePage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const searchParams = useSearchParams();
  const router = useRouter();

  const view: EvidenceView =
    searchParams.get('view') === 'findings' ? 'findings' : 'patterns';

  const [niche, setNiche] = useState<Market | null>(null);
  const [patterns, setPatterns] = useState<AccumulatedTheme[]>([]);
  const [findings, setFindings] = useState<Signal[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, themesRes, signalsRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getThemes({ market_id: marketId }),
        signalApi.getSignals({ market_id: marketId }),
      ]);
      setNiche(market);
      setPatterns(themesRes.themes);
      setFindings(signalsRes.signals);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evidence');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const patternByFindingId = useMemo(() => {
    const map = new Map<string, AccumulatedTheme>();
    patterns.forEach(p => (p.finding_ids ?? p.signal_ids).forEach(id => map.set(id, p)));
    return map;
  }, [patterns]);

  function switchView(v: EvidenceView) {
    router.replace(`/markets/${encodeURIComponent(marketId)}/evidence?view=${v}`);
  }

  const title = niche?.name ?? '';

  return (
    <DashboardShell
      title={title}
      actions={<NicheViewSwitcher marketId={marketId} active="evidence" />}
    >
      {/* Segmented control */}
      <div className="mb-5 flex w-fit items-center gap-1 rounded-lg border border-slate-800/70 bg-slate-900/40 p-1">
        <button
          onClick={() => switchView('patterns')}
          className={`rounded-md px-4 py-1.5 text-xs font-semibold transition ${
            view === 'patterns'
              ? 'bg-slate-800 text-slate-100 shadow-sm'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Patterns
          {status === 'ready' && patterns.length > 0 && (
            <span className="ml-1.5 rounded bg-slate-700/60 px-1.5 text-[10px] text-slate-400">{patterns.length}</span>
          )}
        </button>
        <button
          onClick={() => switchView('findings')}
          className={`rounded-md px-4 py-1.5 text-xs font-semibold transition ${
            view === 'findings'
              ? 'bg-slate-800 text-slate-100 shadow-sm'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Findings
          {status === 'ready' && findings.length > 0 && (
            <span className="ml-1.5 rounded bg-slate-700/60 px-1.5 text-[10px] text-slate-400">{findings.length}</span>
          )}
        </button>
      </div>

      {status === 'loading' && <LoadingPanel label={view === 'patterns' ? 'Loading patterns' : 'Loading findings'} />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {/* ── Patterns view ── */}
      {status === 'ready' && view === 'patterns' && (
        <div className="space-y-3 animate-fade-in">
          {patterns.length === 0 ? (
            <EmptyPanel
              title="No patterns yet"
              detail="Evidence patterns appear after the agent reviews enough relevant posts across scans."
            />
          ) : (
            patterns
              .slice()
              .sort((a, b) => b.frequency - a.frequency)
              .map(pattern => (
                <Link
                  key={pattern.id}
                  href={`/markets/${encodeURIComponent(marketId)}/themes/${encodeURIComponent(pattern.id)}`}
                  className="block rounded-xl border border-slate-800/70 bg-slate-900/40 p-5 transition hover:border-slate-700/80 hover:bg-slate-900/60"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="font-semibold text-slate-100">{pattern.theme}</h2>
                      {pattern.summary && (
                        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-slate-500">{pattern.summary}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {pattern.status === 'qualified' && (
                        <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-xs font-medium text-emerald-300">
                          Opportunity-ready
                        </span>
                      )}
                      <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-500">
                        {pattern.frequency} {pattern.frequency === 1 ? 'finding' : 'findings'}
                      </span>
                      <ScoreBadge value={pattern.average_score} />
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    {pattern.source_family_breakdown?.length ? (
                      pattern.source_family_breakdown.map(b => (
                        <span key={b.source_family} className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-slate-500">
                          {familyLabel(b.source_family)} {b.count}
                        </span>
                      ))
                    ) : null}
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="text-xs text-slate-600">
                      Across{' '}
                      <span className="font-medium text-slate-400">{pattern.company_count}</span>
                      {pattern.market_company_count != null && (
                        <> of <span className="font-medium text-slate-400">{pattern.market_company_count}</span></>
                      )}{' '}
                      {pattern.company_count === 1 ? 'company' : 'companies'}
                    </span>
                    {pattern.company_names.slice(0, 5).map(name => (
                      <span key={name} className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">{name}</span>
                    ))}
                  </div>

                  {((pattern.evidence_items?.length ?? 0) > 0 || pattern.top_examples.length > 0) && (
                    <div className="mt-4 space-y-2 border-t border-slate-800/50 pt-4">
                      {(pattern.evidence_items?.length ?? 0) > 0
                        ? pattern.evidence_items!.slice(0, 2).map(item => (
                            <EvidenceQuote key={item.id} item={item} />
                          ))
                        : pattern.top_examples.slice(0, 2).map((example, i) => (
                            <p key={i} className="rounded-lg bg-slate-950/35 px-3 py-2 text-xs leading-relaxed text-slate-500">
                              &ldquo;{example}&rdquo;
                            </p>
                          ))}
                    </div>
                  )}
                </Link>
              ))
          )}
        </div>
      )}

      {/* ── Findings view ── */}
      {status === 'ready' && view === 'findings' && (
        <div className="space-y-3 animate-fade-in">
          {findings.length === 0 ? (
            <EmptyPanel
              title="No findings yet"
              detail="Findings appear after the agent extracts evidence from monitored sources."
            />
          ) : (
            findings.map(finding => {
              const pattern = patternByFindingId.get(finding.id);
              return (
                <article key={finding.id} className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="font-semibold leading-snug text-slate-100">{finding.pain}</h2>
                      {finding.job_to_be_done && (
                        <p className="mt-1 text-sm text-slate-500">{finding.job_to_be_done}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <UrgencyBadge urgency={finding.urgency} />
                      <ScoreBadge value={finding.confidence} />
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {pattern && (
                      <button
                        onClick={e => { e.preventDefault(); switchView('patterns'); }}
                        className="inline-flex items-center gap-1 rounded-md bg-violet-600/10 px-2 py-0.5 text-xs font-medium text-violet-400 transition hover:bg-violet-600/20"
                      >
                        {pattern.theme}
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </button>
                    )}
                    {finding.source_label && (
                      <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">
                        {finding.source_label}
                      </span>
                    )}
                    {finding.source_family && !finding.source_label && (
                      <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-slate-500">
                        {familyLabel(finding.source_family)}
                      </span>
                    )}
                    {finding.company_name && <Chip label={finding.company_name} />}
                    {finding.category && <Chip label={finding.category} />}
                    {finding.user_type && <Chip label={finding.user_type} />}
                  </div>

                  {finding.current_workaround && (
                    <p className="mt-3 text-xs text-slate-500">
                      Workaround: <span className="text-slate-400">{finding.current_workaround}</span>
                    </p>
                  )}

                  {finding.evidence_text && (
                    <p className="mt-3 rounded-lg bg-slate-950/35 px-3 py-2 text-xs leading-relaxed text-slate-500">
                      &ldquo;{finding.evidence_text}&rdquo;
                    </p>
                  )}

                  {finding.evidence_url && (
                    <a href={finding.evidence_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-xs font-medium text-violet-400 transition hover:text-violet-300">
                      Open source →
                    </a>
                  )}
                </article>
              );
            })
          )}
        </div>
      )}
    </DashboardShell>
  );
}

function EvidenceQuote({ item }: { item: EvidenceItem }) {
  const source = item.source_label || item.source_family || 'Source';
  return (
    <div className="rounded-lg bg-slate-950/35 px-3 py-2">
      <p className="text-xs leading-relaxed text-slate-500">
        &ldquo;{item.quote || item.pain}&rdquo;
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
        <span>{source}</span>
        {item.company_name && <span>{item.company_name}</span>}
        {item.url && (
          <span className="text-violet-400">Open source →</span>
        )}
      </div>
    </div>
  );
}
