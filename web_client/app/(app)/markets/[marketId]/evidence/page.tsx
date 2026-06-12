'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, EmptyPanel, ErrorPanel, LoadingPanel, ScoreBadge, UrgencyBadge } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { readableSourceUrl } from '@/lib/sourceUrls';
import { AccumulatedTheme, EvidenceItem, Market } from '@/lib/types/signals';

const FAMILY_LABELS: Record<string, string> = {
  technical_forum:  'Technical forums',
  technical_forums: 'Technical forums',
  social:           'Social',
  reviews:          'Reviews',
  owned_site:       'Owned',
  other:            'Other',
};
function familyLabel(f: string) { return FAMILY_LABELS[f] ?? f.replace(/_/g, ' '); }

function cleanText(text: string | null | undefined): string {
  if (!text) return '';
  return text
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

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
  const [findings, setFindings] = useState<EvidenceItem[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, themesRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getThemes({ market_id: marketId }),
      ]);
      setNiche(market);
      setPatterns(themesRes.themes);
      setFindings(evidenceItemsFromThemes(themesRes.themes));
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
    patterns.forEach(pattern => {
      (pattern.finding_ids ?? pattern.signal_ids).forEach(id => map.set(id, pattern));
      (pattern.evidence_items ?? []).forEach(item => map.set(item.id, pattern));
    });
    return map;
  }, [patterns]);

  function switchView(v: EvidenceView) {
    router.replace(`/markets/${encodeURIComponent(marketId)}/evidence?view=${v}`);
  }

  const title = niche?.name ?? '';

  return (
    <DashboardShell
      title={title}
      actions={<NicheViewSwitcher marketId={marketId} active={view === 'patterns' ? 'patterns' : 'evidence'} />}
    >
      {status === 'loading' && <LoadingPanel label={view === 'patterns' ? 'Loading patterns' : 'Loading evidence'} />}
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
                <PatternCard
                  key={pattern.id}
                  pattern={pattern}
                />
              ))
          )}
        </div>
      )}

      {/* ── Evidence view ── */}
      {status === 'ready' && view === 'findings' && (
        <div className="space-y-3 animate-fade-in">
          {findings.length === 0 ? (
            <EmptyPanel
              title="No evidence yet"
              detail="Evidence appears after the agent extracts useful source-backed findings."
            />
          ) : (
            findings.map(finding => {
              const pattern = patternByFindingId.get(finding.id);
              return (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  pattern={pattern}
                  onViewPattern={() => switchView('patterns')}
                />
              );
            })
          )}
        </div>
      )}
    </DashboardShell>
  );
}

function evidenceItemsFromThemes(themes: AccumulatedTheme[]): EvidenceItem[] {
  const seen = new Set<string>();
  const items: EvidenceItem[] = [];

  themes.forEach(theme => {
    (theme.evidence_items ?? []).forEach(item => {
      if (seen.has(item.id)) return;
      seen.add(item.id);
      items.push(item);
    });
  });

  return items.sort((a, b) => {
    const bTime = b.detected_at ? Date.parse(b.detected_at) : 0;
    const aTime = a.detected_at ? Date.parse(a.detected_at) : 0;
    return bTime - aTime;
  });
}

function PatternCard({ pattern }: { pattern: AccumulatedTheme }) {
  const evidenceItems = pattern.evidence_items?.length
    ? pattern.evidence_items.slice(0, 3)
    : null;
  const topExamples = !evidenceItems ? pattern.top_examples.slice(0, 2) : null;

  return (
    <article className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-5 transition hover:border-slate-700/80 hover:bg-slate-900/60">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-slate-100">{pattern.theme}</h2>
          {pattern.summary && (
            <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-500">{pattern.summary}</p>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {pattern.status === 'qualified' && (
            <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-xs font-medium text-emerald-300">
              Opportunity-ready
            </span>
          )}
          <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-500">
            {pattern.frequency} {pattern.frequency === 1 ? 'finding' : 'findings'}
          </span>
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

      {(evidenceItems || topExamples) && (
        <div className="mt-4 space-y-1.5 border-t border-slate-800/50 pt-4">
          {evidenceItems
            ? evidenceItems.map(item => <EvidenceRow key={item.id} item={item} />)
            : topExamples!.map((example, i) => (
                <p key={i} className="text-xs leading-relaxed text-slate-500 line-clamp-2">
                  {cleanText(example)}
                </p>
              ))}
        </div>
      )}
    </article>
  );
}

function EvidenceRow({ item }: { item: EvidenceItem }) {
  const [expanded, setExpanded] = useState(false);
  const source = item.source_label || (item.source_family ? familyLabel(item.source_family) : null);
  const rawText = item.pain || item.quote;
  const text = cleanText(rawText);
  const isLong = text.length > 160;
  const sourceUrl = readableSourceUrl(item.url, item.post_id);

  return (
    <div className="flex items-start gap-3 rounded-lg bg-slate-950/30 px-3 py-2">
      <div className="min-w-0 flex-1">
        {text && (
          <p className={`text-xs leading-relaxed text-slate-400 ${!expanded && isLong ? 'line-clamp-2' : ''}`}>
            {text}
          </p>
        )}
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded(v => !v)}
            className="mt-0.5 text-[10px] text-slate-600 transition hover:text-slate-400"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
        {(source || item.company_name) && (
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
            {source && <span>{source}</span>}
            {item.company_name && <span>{item.company_name}</span>}
          </div>
        )}
      </div>
      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer noopener"
          aria-label="Open source in new tab"
          className="shrink-0 rounded border border-slate-700/50 px-2 py-0.5 text-[10px] font-medium text-slate-500 transition hover:border-violet-500/30 hover:text-violet-400"
        >
          Open ↗
        </a>
      )}
    </div>
  );
}

function FindingCard({
  finding,
  pattern,
  onViewPattern,
}: {
  finding: EvidenceItem;
  pattern: AccumulatedTheme | undefined;
  onViewPattern: () => void;
}) {
  const [quoteExpanded, setQuoteExpanded] = useState(false);
  const quoteText = cleanText(finding.quote || finding.pain);
  const quoteLong = quoteText.length > 200;
  const sourceUrl = readableSourceUrl(finding.url, finding.post_id);
  const title = cleanText(finding.pain) || cleanText(finding.quote) || 'Evidence item';

  return (
    <article className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-semibold leading-snug text-slate-100">{title}</h2>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {finding.urgency && <UrgencyBadge urgency={finding.urgency} />}
          {finding.confidence != null && <ScoreBadge value={finding.confidence} />}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {pattern && (
          <button
            onClick={onViewPattern}
            className="inline-flex items-center gap-1 rounded-md bg-violet-600/10 px-2 py-0.5 text-xs font-medium text-violet-400 transition hover:bg-violet-600/20"
          >
            {pattern.theme}
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
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
      </div>

      {quoteText && (
        <div className="mt-3 rounded-lg bg-slate-950/35 px-3 py-2">
          <p className={`text-xs leading-relaxed text-slate-500 ${!quoteExpanded && quoteLong ? 'line-clamp-3' : ''}`}>
            &ldquo;{quoteText}&rdquo;
          </p>
          {quoteLong && (
            <button
              type="button"
              onClick={() => setQuoteExpanded(v => !v)}
              className="mt-1 text-[10px] text-slate-600 transition hover:text-slate-400"
            >
              {quoteExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      )}

      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer noopener"
          aria-label="Open source in new tab"
          className="mt-3 inline-flex items-center gap-1 rounded border border-slate-700/50 px-2.5 py-1 text-xs font-medium text-slate-500 transition hover:border-violet-500/30 hover:text-violet-400"
        >
          Open source ↗
        </a>
      )}
    </article>
  );
}
