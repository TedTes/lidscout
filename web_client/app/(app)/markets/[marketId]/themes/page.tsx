'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { EmptyPanel, ErrorPanel, LoadingPanel, relativeTime } from '@/components/ui/DashboardPrimitives';
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

function themeSourceCount(theme: AccumulatedTheme): number {
  const items = theme.evidence_items ?? [];
  if (items.length > 0) {
    return new Set(items.map(i => i.source_label || i.source_family).filter(Boolean)).size;
  }
  // No evidence items to derive distinct sources from — fall back to the count of
  // source families/types as a coarser approximation.
  return theme.source_family_breakdown?.length ?? 0;
}

function topEvidenceQuote(theme: AccumulatedTheme): EvidenceItem | null {
  const items = theme.evidence_items ?? [];
  if (items.length === 0) return null;
  return [...items].sort((a, b) => {
    const bTime = b.detected_at ? Date.parse(b.detected_at) : 0;
    const aTime = a.detected_at ? Date.parse(a.detected_at) : 0;
    return bTime - aTime;
  })[0];
}

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

export default function ThemesPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const searchParams = useSearchParams();
  const highlightedThemeId = searchParams.get('theme');

  const [niche, setNiche] = useState<Market | null>(null);
  const [themes, setThemes] = useState<AccumulatedTheme[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus('loading');
      setError(null);
      try {
        const [market, themesRes] = await Promise.all([
          signalApi.getMarket(marketId),
          signalApi.getThemes({ market_id: marketId }),
        ]);
        if (cancelled) return;
        setNiche(market);
        setThemes(themesRes.themes);
        setStatus('ready');
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load themes');
        setStatus('error');
      }
    })();
    return () => { cancelled = true; };
  }, [marketId]);

  useEffect(() => {
    if (status !== 'ready' || !highlightedThemeId) return;
    const timer = setTimeout(() => {
      document.getElementById(`theme-${highlightedThemeId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 80);
    return () => clearTimeout(timer);
  }, [status, highlightedThemeId]);

  const sortedThemes = useMemo(
    () => [...themes].sort((a, b) => b.frequency - a.frequency),
    [themes],
  );

  const title = niche?.name ?? '';

  return (
    <DashboardShell
      title={title}
      actions={<NicheViewSwitcher marketId={marketId} active="themes" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading themes" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-3 animate-fade-in">
          {sortedThemes.length === 0 ? (
            <EmptyPanel
              title="No themes yet"
              detail="Recurring complaint themes appear after the agent reviews enough relevant posts across scans."
            />
          ) : (
            sortedThemes.map(theme => (
              <ThemeCard
                key={theme.id}
                theme={theme}
                marketId={marketId}
                highlighted={theme.id === highlightedThemeId}
              />
            ))
          )}
        </div>
      )}
    </DashboardShell>
  );
}

function ThemeCard({
  theme,
  highlighted,
}: {
  theme: AccumulatedTheme;
  marketId: string;
  highlighted?: boolean;
}) {
  const sourceCount = themeSourceCount(theme);
  const topQuote = topEvidenceQuote(theme);
  const recency = relativeTime(theme.latest_finding_at);
  const quoteText = cleanText(topQuote?.quote || topQuote?.pain);
  const quoteUrl = topQuote ? readableSourceUrl(topQuote.url, topQuote.post_id) : null;

  return (
    <div id={`theme-${theme.id}`}>
      <article
        className={`rounded-xl border bg-slate-900/40 p-5 transition ${
          highlighted
            ? 'border-violet-500/50 ring-1 ring-violet-500/30'
            : 'border-slate-800/70 hover:border-slate-700/80 hover:bg-slate-900/60'
        }`}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-slate-100">{theme.theme}</h2>
            {theme.summary && (
              <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-500">{theme.summary}</p>
            )}
          </div>
          {theme.status === 'qualified' && (
            <span className="shrink-0 rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-xs font-medium text-emerald-300">
              Gap-ready
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
          <span>{theme.frequency} {theme.frequency === 1 ? 'evidence item' : 'evidence items'}</span>
          <span className="h-3 w-px bg-slate-800" />
          <span>{sourceCount} {sourceCount === 1 ? 'source' : 'sources'}</span>
          {recency && (
            <>
              <span className="h-3 w-px bg-slate-800" />
              <span>Last seen {recency}</span>
            </>
          )}
        </div>

        {theme.source_family_breakdown?.length ? (
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {theme.source_family_breakdown.map(b => (
              <span key={b.source_family} className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-slate-500">
                {familyLabel(b.source_family)} {b.count}
              </span>
            ))}
          </div>
        ) : null}

        {quoteText && (
          <div className="mt-4 flex items-start gap-3 rounded-lg bg-slate-950/30 border-t border-slate-800/50 px-3 py-2.5">
            <p className="min-w-0 flex-1 text-xs leading-relaxed text-slate-400 line-clamp-2">
              &ldquo;{quoteText}&rdquo;
            </p>
            {quoteUrl && (
              <a
                href={quoteUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="shrink-0 rounded border border-slate-700/50 px-2 py-0.5 text-[10px] font-medium text-slate-500 transition hover:border-violet-500/30 hover:text-violet-400"
              >
                Open ↗
              </a>
            )}
          </div>
        )}
      </article>
    </div>
  );
}
