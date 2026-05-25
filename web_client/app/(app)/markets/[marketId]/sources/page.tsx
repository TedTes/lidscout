'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Competitor, Market, MonitoredSource, SourceCoverageSummary, SourceSuggestion } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

const FAMILY_LABELS: Record<string, string> = {
  reviews: 'Reviews',
  social: 'Social',
  technical_forum: 'Technical forums',
  owned_site: 'Owned content',
  other: 'Other',
};

function familyLabel(family: string | null) {
  return FAMILY_LABELS[family ?? 'other'] ?? family?.replace(/_/g, ' ') ?? FAMILY_LABELS.other;
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

function sourceHealth(source: MonitoredSource): 'active' | 'failing' | 'paused' {
  if (!source.enabled) return 'paused';
  if (source.health?.last_status === 'failing' || source.last_error) return 'failing';
  return 'active';
}

function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconChevron({ open }: { open: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-150 ${open ? 'rotate-180' : ''}`}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export default function NicheSourcesPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [sources, setSources] = useState<MonitoredSource[]>([]);
  const [summary, setSummary] = useState<SourceCoverageSummary | null>(null);
  const [companies, setCompanies] = useState<Competitor[]>([]);
  const [suggestions, setSuggestions] = useState<SourceSuggestion[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [suggestionStatus, setSuggestionStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [showAddSource, setShowAddSource] = useState(false);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);

  const load = async () => {
    setStatus('loading');
    setSuggestionStatus('loading');
    setError(null);
    try {
      const [marketsRes, sourcesRes, companiesRes, suggestionsRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getSources({ market_id: marketId }),
        signalApi.getMarketCompetitors(marketId),
        signalApi.getMarketSourceSuggestions(marketId),
      ]);
      const loadedSources = sourcesRes.sources;
      setNiche(marketsRes.markets.find(m => m.id === marketId) ?? null);
      setSources(loadedSources);
      setSummary(sourcesRes.summary ?? null);
      setCompanies(companiesRes.competitors);
      setSuggestions(suggestionsRes.suggestions);
      setStatus('ready');
      setSuggestionStatus('ready');
      if (loadedSources.length === 0) setSuggestionsOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources');
      setStatus('error');
      setSuggestionStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const newSuggestions = suggestions.filter(s => !s.already_monitored);
  const activeCount = summary?.active_count ?? sources.filter(s => s.enabled).length;
  const errorCount = summary?.error_count ?? sources.filter(s => s.last_error || s.health?.last_status === 'failing').length;

  const groupedSources = useMemo(() => {
    const groups = new Map<string, MonitoredSource[]>();
    sources.forEach(source => {
      const family = source.source_family ?? 'other';
      groups.set(family, [...(groups.get(family) ?? []), source]);
    });
    return [...groups.entries()].sort(([a], [b]) => familyLabel(a).localeCompare(familyLabel(b)));
  }, [sources]);

  const removeSource = (id: string) => {
    setSources(prev => prev.filter(s => s.id !== id));
    setSummary(null);
  };

  const toggleSource = async (source: MonitoredSource) => {
    const updated = await signalApi.updateSource(source.id, { enabled: !source.enabled });
    setSources(prev => prev.map(s => s.id === updated.id ? updated : s));
    setSummary(null);
  };

  const addSuggestion = async (suggestion: SourceSuggestion) => {
    if (suggestion.already_monitored) return;
    if (suggestion.competitor_id) {
      await signalApi.createCompetitorSource(suggestion.competitor_id, {
        locator: suggestion.locator,
        source_type: suggestion.source_type,
        limit: suggestion.limit,
        options: suggestion.options,
        market_id: marketId,
      });
    } else {
      await signalApi.createMarketSource(marketId, {
        locator: suggestion.locator,
        source_type: suggestion.source_type,
        limit: suggestion.limit,
        options: suggestion.options,
      });
    }
    await load();
  };

  return (
    <DashboardShell
      title="Sources"
      subtitle={`Sources monitored for ${niche?.name ?? 'this niche'}.`}
      actions={
        <NicheViewSwitcher
          marketId={marketId}
          active="sources"
          trailingAction={
            <button
              type="button"
              onClick={() => setShowAddSource(v => !v)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-300 transition hover:bg-violet-500/15 hover:text-violet-200"
              aria-label="Add source"
              title="Add source"
            >
              <IconPlus />
            </button>
          }
        />
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading sources" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          {/* Stats */}
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label="Monitored" value={summary?.source_count ?? sources.length} />
            <StatCard label="Active" value={activeCount} accent={activeCount > 0} />
            <StatCard label="Failing" value={errorCount} danger={errorCount > 0} />
          </div>

          {/* Add source form */}
          {showAddSource && (
            <AddSourcePanel
              companies={companies}
              marketId={marketId}
              onAdd={async source => {
                setSources(prev => [source, ...prev]);
                setSummary(null);
                setShowAddSource(false);
              }}
              onCancel={() => setShowAddSource(false)}
            />
          )}

          {/* ── Monitored sources ── */}
          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="border-b border-slate-800/70 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-300">Monitored sources</h2>
              <p className="mt-0.5 text-xs text-slate-600">What this niche is currently watching.</p>
            </div>

            {sources.length === 0 ? (
              <div className="p-5">
                <EmptyPanel
                  title="No sources monitored yet"
                  detail="Add from the suggested sources below, or use the + button to add manually."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-800/70">
                {groupedSources.map(([family, familySources]) => (
                  <div key={family} className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-600">{familyLabel(family)}</h3>
                      <span className="text-xs text-slate-700">
                        {summary?.by_family.find(item => item.source_family === family)?.active_count ?? familySources.filter(source => source.enabled).length}
                        {' active · '}
                        {familySources.length} total
                      </span>
                    </div>
                    <div className="space-y-2">
                      {familySources.map(source => (
                        <SourceRow
                          key={source.id}
                          source={source}
                          onToggle={() => toggleSource(source)}
                          onRemoved={() => removeSource(source.id)}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── Suggested sources ── */}
          <section className="rounded-xl border border-slate-800/60 bg-slate-900/25">
            <button
              type="button"
              onClick={() => setSuggestionsOpen(v => !v)}
              className="flex w-full items-center justify-between px-5 py-4 text-left"
            >
              <div>
                <h2 className="text-sm font-medium text-slate-500">Suggested sources</h2>
                {!suggestionsOpen && newSuggestions.length > 0 && (
                  <p className="mt-0.5 text-xs text-slate-700">{newSuggestions.length} new suggestions available</p>
                )}
              </div>
              <span className="text-slate-700">
                <IconChevron open={suggestionsOpen} />
              </span>
            </button>

            {suggestionsOpen && (
              <>
                {suggestionStatus === 'loading' && <div className="border-t border-slate-800/60 p-5"><LoadingPanel label="Loading suggestions" /></div>}
                {suggestionStatus === 'ready' && newSuggestions.length === 0 && (
                  <div className="border-t border-slate-800/60 p-5">
                    <EmptyPanel title="No new suggestions" detail="All ranked suggestions are already monitored." />
                  </div>
                )}
                {suggestionStatus === 'ready' && newSuggestions.length > 0 && (
                  <div className="divide-y divide-slate-800/50 border-t border-slate-800/60">
                    {newSuggestions.slice(0, 8).map(suggestion => (
                      <SuggestionRow
                        key={`${suggestion.template_id ?? suggestion.locator}-${suggestion.competitor_id ?? 'niche'}`}
                        suggestion={suggestion}
                        onAdd={() => addSuggestion(suggestion)}
                      />
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function SourceRow({
  source,
  onToggle,
  onRemoved,
}: {
  source: MonitoredSource;
  onToggle: () => void;
  onRemoved: () => void;
}) {
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [toggling, setToggling] = useState(false);

  const health = sourceHealth(source);
  const scannedAt = relativeTime(source.health?.last_scanned_at ?? source.last_scanned_at);
  const lastError = source.health?.last_error ?? source.last_error;

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await signalApi.deleteSource(source.id);
      onRemoved();
    } catch {
      setRemoving(false);
      setConfirmRemove(false);
    }
  };

  const handleToggle = async () => {
    setToggling(true);
    try {
      await onToggle();
    } finally {
      setToggling(false);
    }
  };

  return (
    <div className={`rounded-lg border px-4 py-3 transition ${health === 'failing' ? 'border-rose-500/20 bg-rose-500/[0.03]' : 'border-slate-800/70 bg-slate-950/25'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        {/* Left: URL + chips + status */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <HealthBadge health={health} />
            {source.competitor_name
              ? <Chip label={source.competitor_name} />
              : <Chip label="Niche-wide" />}
            <Chip label={familyLabel(source.source_family)} />
          </div>
          <p className="mt-2 truncate font-mono text-xs text-slate-500">{source.locator}</p>
          {lastError && (
            <p className="mt-1 text-xs text-rose-400">{lastError}</p>
          )}
          {source.health && (
            <p className="mt-1 text-[11px] text-slate-700">
              Last run: {source.health.last_fetched_count} fetched · {source.health.last_relevant_count} relevant · {source.health.last_extracted_count} extracted
            </p>
          )}
        </div>

        {/* Right: scan time + actions */}
        <div className="flex shrink-0 flex-col items-end gap-2">
          {scannedAt && (
            <span className="text-[11px] text-slate-700">Scanned {scannedAt}</span>
          )}
          {confirmRemove ? (
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-slate-500">Remove?</span>
              <button
                onClick={handleRemove}
                disabled={removing}
                className="rounded px-2 py-1 text-[11px] font-semibold text-rose-400 transition hover:bg-rose-500/10 disabled:opacity-50"
              >
                {removing ? 'Removing…' : 'Confirm'}
              </button>
              <button
                onClick={() => setConfirmRemove(false)}
                className="rounded px-2 py-1 text-[11px] text-slate-600 transition hover:text-slate-400"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleToggle}
                disabled={toggling}
                className="rounded-lg border border-slate-700/80 px-2.5 py-1 text-[11px] font-medium text-slate-400 transition hover:text-slate-100 disabled:opacity-50"
              >
                {source.enabled ? 'Pause' : 'Enable'}
              </button>
              <button
                onClick={() => setConfirmRemove(true)}
                className="rounded-lg border border-slate-700/80 px-2.5 py-1 text-[11px] font-medium text-slate-500 transition hover:border-rose-500/30 hover:text-rose-400"
              >
                Remove
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SuggestionRow({
  suggestion,
  onAdd,
}: {
  suggestion: SourceSuggestion;
  onAdd: () => void;
}) {
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    setAdding(true);
    try {
      await onAdd();
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-medium text-slate-400">{suggestion.label}</h3>
          <Chip label={familyLabel(suggestion.source_family)} />
          {suggestion.competitor_name
            ? <Chip label={suggestion.competitor_name} />
            : <Chip label="Niche-wide" />}
        </div>
        <p className="mt-1 text-xs leading-relaxed text-slate-600">{suggestion.rationale}</p>
        <p className="mt-1.5 truncate font-mono text-[11px] text-slate-700">{suggestion.locator}</p>
      </div>
      <button
        onClick={handleAdd}
        disabled={adding}
        className="rounded-lg border border-violet-500/25 bg-violet-500/[0.07] px-3 py-1.5 text-xs font-semibold text-violet-400 transition hover:bg-violet-500/12 disabled:opacity-50"
      >
        {adding ? 'Adding…' : 'Add source'}
      </button>
    </div>
  );
}

function HealthBadge({ health }: { health: 'active' | 'failing' | 'paused' }) {
  if (health === 'failing') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-400">
        <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
        Failing
      </span>
    );
  }
  if (health === 'paused') {
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] font-medium text-slate-500">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
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

function AddSourcePanel({
  companies,
  marketId,
  onAdd,
  onCancel,
}: {
  companies: Competitor[];
  marketId: string;
  onAdd: (source: MonitoredSource) => void;
  onCancel: () => void;
}) {
  const [locator, setLocator] = useState('');
  const [sourceType, setSourceType] = useState('web');
  const [companyId, setCompanyId] = useState('');
  const [limit, setLimit] = useState('10');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const request = {
        locator,
        source_type: sourceType,
        limit: limit ? Number(limit) : null,
        options: {},
      };
      const source = companyId
        ? await signalApi.createCompetitorSource(companyId, { ...request, market_id: marketId })
        : await signalApi.createMarketSource(marketId, request);
      onAdd(source);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add source');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
      <h2 className="text-sm font-semibold text-slate-300">Add source</h2>
      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_150px_160px_100px]">
        <Field label="URL or API endpoint" value={locator} onChange={setLocator} required placeholder="https://…" />
        <Field label="Type" value={sourceType} onChange={setSourceType} required />
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Scope</span>
          <select
            value={companyId}
            onChange={e => setCompanyId(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700/70 bg-slate-950/40 px-3 py-2 text-sm text-slate-300 outline-none focus:border-violet-500/40"
          >
            <option value="">Niche-wide</option>
            {companies.map(company => (
              <option key={company.id} value={company.id}>{company.name}</option>
            ))}
          </select>
        </label>
        <Field label="Limit" value={limit} onChange={setLimit} />
      </div>
      {error && <p className="mt-3 text-xs text-rose-400">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button
          disabled={submitting || !locator.trim()}
          className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? 'Adding…' : 'Add source'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-400 transition hover:text-slate-200"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="mt-1 w-full rounded-lg border border-slate-700/70 bg-slate-950/40 px-3 py-2 text-sm text-slate-300 outline-none placeholder:text-slate-700 focus:border-violet-500/40"
      />
    </label>
  );
}

function StatCard({
  label,
  value,
  accent,
  danger,
}: {
  label: string;
  value: number;
  accent?: boolean;
  danger?: boolean;
}) {
  return (
    <div className={`rounded-xl border px-5 py-4 ${danger ? 'border-rose-500/20 bg-rose-500/[0.06]' : accent ? 'border-violet-500/20 bg-violet-600/[0.08]' : 'border-slate-800/80 bg-slate-900/50'}`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${danger ? 'text-rose-300' : accent ? 'text-violet-300' : 'text-slate-100'}`}>{value}</p>
    </div>
  );
}
