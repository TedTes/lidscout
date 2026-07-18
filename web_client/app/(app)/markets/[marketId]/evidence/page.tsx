'use client';

import { useEffect, useMemo, useState } from 'react';
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
type RecencyFilter = 7 | 30 | 90 | null;

const RECENCY_OPTIONS: RecencyFilter[] = [null, 7, 30, 90];

function withinRecency(iso: string | null, days: RecencyFilter): boolean {
  if (days == null) return true;
  if (!iso) return false;
  const ageMs = Date.now() - new Date(iso).getTime();
  return ageMs <= days * 24 * 60 * 60 * 1000;
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 rounded-lg border border-slate-800/70 bg-slate-900/40 px-2.5 py-1.5 text-xs">
      <span className="text-slate-600">{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="min-w-0 max-w-[140px] truncate bg-transparent text-slate-300 outline-none [&>option]:bg-slate-900"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </label>
  );
}

export default function EvidencePage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);

  const [niche, setNiche] = useState<Market | null>(null);
  const [themes, setThemes] = useState<AccumulatedTheme[]>([]);
  const [findings, setFindings] = useState<EvidenceItem[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  const [sourceTypeFilter, setSourceTypeFilter] = useState('all');
  const [companyFilter, setCompanyFilter] = useState('all');
  const [themeFilter, setThemeFilter] = useState('all');
  const [recencyFilter, setRecencyFilter] = useState<RecencyFilter>(null);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, themesRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getThemes({ market_id: marketId }),
      ]);
      setNiche(market);
      setThemes(themesRes.themes);
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

  const themeByFindingId = useMemo(() => {
    const map = new Map<string, AccumulatedTheme>();
    themes.forEach(theme => {
      (theme.finding_ids ?? theme.signal_ids).forEach(id => map.set(id, theme));
      (theme.evidence_items ?? []).forEach(item => map.set(item.id, theme));
    });
    return map;
  }, [themes]);

  const sourceTypeOptions = useMemo(() => {
    const set = new Set<string>();
    findings.forEach(f => { if (f.source_family) set.add(f.source_family); });
    return [{ value: 'all', label: 'All source types' }, ...[...set].sort().map(v => ({ value: v, label: familyLabel(v) }))];
  }, [findings]);

  const companyOptions = useMemo(() => {
    const set = new Set<string>();
    findings.forEach(f => { if (f.company_name) set.add(f.company_name); });
    return [{ value: 'all', label: 'All products' }, ...[...set].sort().map(v => ({ value: v, label: v }))];
  }, [findings]);

  const themeOptions = useMemo(
    () => [{ value: 'all', label: 'All themes' }, ...themes.map(t => ({ value: t.id, label: t.theme }))],
    [themes],
  );

  const filteredFindings = useMemo(() => {
    return findings.filter(f => {
      if (sourceTypeFilter !== 'all' && f.source_family !== sourceTypeFilter) return false;
      if (companyFilter !== 'all' && f.company_name !== companyFilter) return false;
      if (themeFilter !== 'all' && themeByFindingId.get(f.id)?.id !== themeFilter) return false;
      if (!withinRecency(f.detected_at, recencyFilter)) return false;
      return true;
    });
  }, [findings, sourceTypeFilter, companyFilter, themeFilter, recencyFilter, themeByFindingId]);

  const title = niche?.name ?? '';

  return (
    <DashboardShell
      title={title}
      actions={<NicheViewSwitcher marketId={marketId} active="evidence" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading evidence" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-3 animate-fade-in">
          {findings.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <FilterSelect label="Source type" value={sourceTypeFilter} options={sourceTypeOptions} onChange={setSourceTypeFilter} />
              <FilterSelect label="Product" value={companyFilter} options={companyOptions} onChange={setCompanyFilter} />
              <FilterSelect label="Theme" value={themeFilter} options={themeOptions} onChange={setThemeFilter} />
              <div className="flex items-center gap-1 rounded-lg border border-slate-800/70 bg-slate-900/40 p-1">
                {RECENCY_OPTIONS.map(d => (
                  <button
                    key={d ?? 'all'}
                    onClick={() => setRecencyFilter(d)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                      recencyFilter === d ? 'bg-slate-700/80 text-slate-200' : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {d == null ? 'All time' : `${d}d`}
                  </button>
                ))}
              </div>
            </div>
          )}

          {findings.length === 0 ? (
            <EmptyPanel
              title="No evidence yet"
              detail="Evidence appears after the agent extracts useful source-backed findings."
            />
          ) : filteredFindings.length === 0 ? (
            <EmptyPanel title="No evidence matches these filters" detail="Try widening the source, product, theme, or date range filters." />
          ) : (
            filteredFindings.map(finding => (
              <FindingCard
                key={finding.id}
                finding={finding}
                theme={themeByFindingId.get(finding.id)}
                marketId={marketId}
              />
            ))
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

function FindingCard({
  finding,
  theme,
  marketId,
}: {
  finding: EvidenceItem;
  theme: AccumulatedTheme | undefined;
  marketId: string;
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
        {theme && (
          <a
            href={`/markets/${encodeURIComponent(marketId)}/themes?theme=${encodeURIComponent(theme.id)}`}
            className="inline-flex items-center gap-1 rounded-md bg-violet-600/10 px-2 py-0.5 text-xs font-medium text-violet-400 transition hover:bg-violet-600/20"
          >
            {theme.theme}
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </a>
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
