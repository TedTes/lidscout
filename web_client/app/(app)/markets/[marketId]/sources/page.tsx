'use client';

import { useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Market, MonitoredSource, SourceCoverageSummary } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type SourceHealth = 'active' | 'failing' | 'paused' | 'excluded';

const FAMILY_LABELS: Record<string, string> = {
  reviews:          'Reviews',
  social:           'Social',
  technical_forum:  'Technical forums',
  technical_forums: 'Technical forums',
  owned_site:       'Owned content',
  other:            'Other',
};
function familyLabel(family: string | null) {
  return FAMILY_LABELS[family ?? 'other'] ?? family?.replace(/_/g, ' ') ?? 'Other';
}

function relativeTime(iso: string | null): string | null {
  if (!iso) return null;
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 2) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function sourceHealth(source: MonitoredSource): SourceHealth {
  if (source.excluded || source.muted) return 'excluded';
  if (!source.enabled) return 'paused';
  if (source.health?.last_status === 'failing' || source.last_error) return 'failing';
  return 'active';
}

const HEALTH_ORDER: Record<SourceHealth, number> = { active: 0, failing: 1, paused: 2, excluded: 3 };

function sourceHref(locator: string) {
  const href = /^https?:\/\//i.test(locator) ? locator : `https://${locator}`;
  try {
    const url = new URL(href);
    const host = url.hostname.toLowerCase();
    if (host === 'hn.algolia.com' && url.pathname.startsWith('/api/')) {
      const search = new URL('https://hn.algolia.com/');
      const query = url.searchParams.get('query');
      if (query) search.searchParams.set('query', query);
      search.searchParams.set('sort', 'byDate');
      search.searchParams.set('dateRange', 'all');
      if (url.searchParams.get('tags') === 'comment') {
        search.searchParams.set('type', 'comment');
      }
      return search.toString();
    }
    if (host === 'api.github.com' && url.pathname === '/search/issues') {
      const repo = url.searchParams.get('q')?.match(/(?:^|\s)repo:([^\s]+)/)?.[1];
      if (repo) return `https://github.com/${repo}/issues`;
    }
    if (host === 'api.stackexchange.com' && url.pathname.includes('/search/advanced')) {
      const site = url.searchParams.get('site') ?? 'stackoverflow';
      const query = url.searchParams.get('q') ?? '';
      const base =
        site === 'stackoverflow'
          ? 'https://stackoverflow.com/search'
          : `https://${site}.stackexchange.com/search`;
      const search = new URL(base);
      if (query) search.searchParams.set('q', query);
      return search.toString();
    }
    if (url.pathname.endsWith('/latest.json')) {
      return `${url.origin}${url.pathname.replace(/\/latest\.json$/, '/latest')}`;
    }
    if (url.pathname.endsWith('.json')) {
      return `${url.origin}${url.pathname.replace(/\.json$/, '')}`;
    }
    return href;
  } catch {
    return href;
  }
}

function compareSources(a: MonitoredSource, b: MonitoredSource) {
  const healthDelta = HEALTH_ORDER[sourceHealth(a)] - HEALTH_ORDER[sourceHealth(b)];
  if (healthDelta !== 0) return healthDelta;
  return a.locator.localeCompare(b.locator);
}

function IconCopy() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

export default function NicheSourcesPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [sources, setSources] = useState<MonitoredSource[]>([]);
  const [summary, setSummary] = useState<SourceCoverageSummary | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    setStatus('loading');
    setError(null);
    try {
      const [market, sourcesRes] = await Promise.all([
        signalApi.getMarket(marketId),
        signalApi.getMarketSources(marketId),
      ]);
      setNiche(market);
      setSources(sourcesRes.sources);
      setSummary(sourcesRes.summary ?? null);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const sortedSources = useMemo(
    () => [...sources].sort(compareSources),
    [sources],
  );

  const copySources = () => {
    const lines = sources.map(s => {
      const h = sourceHealth(s);
      const icon = h === 'active' ? '✅' : h === 'failing' ? '❌' : '⊘';
      return `${icon} ${s.locator}  [${familyLabel(s.source_family)}${s.company_name ? ` · ${s.company_name}` : ''}]${s.last_error ? `  ⚠ ${s.last_error}` : ''}`;
    });
    const active = sources.filter(s => sourceHealth(s) === 'active').length;
    const failing = sources.filter(s => sourceHealth(s) === 'failing').length;
    const header = `${niche?.name ?? 'Watchlist'} sources (${sources.length} total · ${active} active · ${failing} failing)\n\n`;
    navigator.clipboard.writeText(header + lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const updateSource = (updated: MonitoredSource) => {
    setSources(prev => prev.map(s => s.id === updated.id ? updated : s));
    setSummary(null);
  };

  const activeCount = summary?.active_count ?? sources.filter(s => sourceHealth(s) === 'active').length;
  const failingCount = summary?.failing_count ?? summary?.error_count ?? sources.filter(s => sourceHealth(s) === 'failing').length;
  const pausedCount = summary?.paused_count ?? sources.filter(s => sourceHealth(s) === 'paused').length;
  const excludedCount = summary?.excluded_count ?? sources.filter(s => sourceHealth(s) === 'excluded').length;
  const totalCount = summary?.source_count ?? sources.length;

  return (
    <DashboardShell
      title="Research coverage"
      subtitle={`Source coverage for ${niche?.name ?? 'this watchlist'}.`}
      actions={<NicheViewSwitcher marketId={marketId} active="sources" />}
    >
      {status === 'loading' && <LoadingPanel label="Loading sources" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-4 animate-fade-in">

          {/* ── Summary band ── */}
          {totalCount > 0 && (
            <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-800/70 bg-slate-900/30 px-5 py-3.5">
              <SummaryPill label="Total" value={totalCount} />
              <span className="h-4 w-px bg-slate-800/70" />
              <SummaryPill label="Active" value={activeCount} dotCls="bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.6)]" />
              {failingCount > 0 && (
                <SummaryPill label="Failing" value={failingCount} dotCls="bg-rose-400" />
              )}
              {pausedCount > 0 && (
                <SummaryPill label="Paused" value={pausedCount} dotCls="bg-amber-400" />
              )}
              {excludedCount > 0 && (
                <SummaryPill label="Excluded" value={excludedCount} dotCls="bg-slate-600" />
              )}
            </div>
          )}

          {/* ── Sources list ── */}
          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex items-center justify-between border-b border-slate-800/70 px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-300">Monitored sources</h2>
                <p className="mt-0.5 text-xs text-slate-600">
                  Public sources monitored for this watchlist. Exclude any that are not relevant to you.
                </p>
              </div>
              {sources.length > 0 && (
                <button
                  type="button"
                  onClick={copySources}
                  title="Copy all sources to clipboard"
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${copied ? 'border-emerald-500/30 text-emerald-400' : 'border-slate-700/60 text-slate-500 hover:border-slate-600 hover:text-slate-300'}`}
                >
                  <IconCopy />
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              )}
            </div>

            {sources.length === 0 ? (
              <div className="p-5">
                <EmptyPanel
                  title="No sources configured"
                  detail="Add or apply a watchlist with public sources, then run a scan to activate coverage."
                />
              </div>
            ) : (
              <div className="space-y-2 p-5">
                {sortedSources.map(source => (
                  <SourceRow
                    key={source.id}
                    marketId={marketId}
                    source={source}
                    onUpdated={updateSource}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function SummaryPill({ label, value, dotCls }: { label: string; value: number; dotCls?: string }) {
  return (
    <div className="flex items-center gap-2">
      {dotCls && <span className={`h-1.5 w-1.5 rounded-full ${dotCls}`} />}
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-semibold text-slate-200">{value}</span>
    </div>
  );
}

function plural(n: number, singular: string, pluralForm = `${singular}s`) {
  return `${n} ${n === 1 ? singular : pluralForm}`;
}

function SourceRow({
  marketId,
  source,
  onUpdated,
}: {
  marketId: string;
  source: MonitoredSource;
  onUpdated: (s: MonitoredSource) => void;
}) {
  const [busy, setBusy] = useState(false);
  const health = sourceHealth(source);
  const scannedAt = relativeTime(source.health?.last_scanned_at ?? source.last_scanned_at);
  const lastError = source.health?.last_error ?? source.last_error;
  const contribution = source.contribution ?? {
    findings_count: source.findings_count ?? 0,
    themes_count: source.themes_count ?? 0,
    opportunities_count: source.opportunities_count ?? 0,
  };
  const hasContribution =
    contribution.findings_count > 0 ||
    contribution.themes_count > 0 ||
    contribution.opportunities_count > 0;

  const handleExclude = async () => {
    setBusy(true);
    try {
      const updated = await signalApi.excludeMarketSource(marketId, source.id);
      onUpdated(updated);
    } finally {
      setBusy(false);
    }
  };

  const handleRestore = async () => {
    setBusy(true);
    try {
      const updated = await signalApi.restoreMarketSource(marketId, source.id);
      onUpdated(updated);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`rounded-lg border px-4 py-3 transition ${
      health === 'failing'  ? 'border-rose-500/20 bg-rose-500/[0.03]' :
      health === 'excluded' ? 'border-slate-800/40 bg-slate-950/15 opacity-60' :
      'border-slate-800/70 bg-slate-950/25'
    }`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        {/* Left */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <HealthBadge health={health} />
          </div>
          <a
            href={sourceHref(source.locator)}
            target="_blank"
            rel="noreferrer"
            className="mt-2 block break-all font-mono text-xs leading-5 text-slate-400 underline-offset-2 transition hover:text-violet-300 hover:underline"
          >
            {source.locator}
          </a>
          {(source.company_name || source.scan_frequency || source.limit !== null) && (
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-700">
              {source.company_name && <span>{source.company_name}</span>}
              {source.scan_frequency && <span>{source.scan_frequency}</span>}
              {source.limit !== null && <span>Limit {source.limit}</span>}
            </div>
          )}
          {lastError && health !== 'excluded' && (
            <p className="mt-1 text-xs text-rose-400">{lastError}</p>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            {scannedAt && (
              <span className="text-[11px] text-slate-700">Scanned {scannedAt}</span>
            )}
            {hasContribution && (
              <span className="text-[11px] text-slate-700">
                {plural(contribution.findings_count, 'finding')}
                {' · '}
                {plural(contribution.themes_count, 'theme')}
                {' · '}
                {plural(contribution.opportunities_count, 'opportunity', 'opportunities')}
              </span>
            )}
            {source.health && source.health.last_fetched_count > 0 && (
              <span className="text-[11px] text-slate-700">
                {source.health.last_fetched_count} fetched
                {source.health.last_relevant_count > 0 && ` · ${source.health.last_relevant_count} relevant`}
                {source.health.last_extracted_count > 0 && ` · ${source.health.last_extracted_count} extracted`}
              </span>
            )}
          </div>
        </div>

        {/* Right: action */}
        <div className="shrink-0">
          {health === 'excluded' ? (
            <button
              onClick={handleRestore}
              disabled={busy}
              className="rounded-lg border border-slate-700/60 px-2.5 py-1 text-[11px] font-medium text-slate-400 transition hover:border-violet-500/30 hover:text-violet-300 disabled:opacity-40"
            >
              {busy ? '…' : 'Restore'}
            </button>
          ) : (
            <button
              onClick={handleExclude}
              disabled={busy}
              className="rounded-lg border border-slate-700/60 px-2.5 py-1 text-[11px] font-medium text-slate-500 transition hover:border-rose-500/20 hover:text-rose-400 disabled:opacity-40"
            >
              {busy ? '…' : 'Exclude'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function HealthBadge({ health }: { health: SourceHealth }) {
  if (health === 'failing') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-400">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
        Failing
      </span>
    );
  }
  if (health === 'excluded') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] font-medium text-slate-500">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
        Excluded
      </span>
    );
  }
  if (health === 'paused') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-400">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        Paused
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]" />
      Active
    </span>
  );
}
