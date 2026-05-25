'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { Chip, EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Competitor, Market, MonitoredSource, SourceSuggestion } from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';

const FAMILY_LABELS: Record<string, string> = {
  reviews: 'Reviews',
  social: 'Social',
  technical_forum: 'Technical forums',
  owned_site: 'Owned content',
  other: 'Other',
};

export default function NicheSourcesPage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [sources, setSources] = useState<MonitoredSource[]>([]);
  const [companies, setCompanies] = useState<Competitor[]>([]);
  const [suggestions, setSuggestions] = useState<SourceSuggestion[]>([]);
  const [status, setStatus] = useState<Status>('loading');
  const [suggestionStatus, setSuggestionStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [showAddSource, setShowAddSource] = useState(false);
  const [showAddCompany, setShowAddCompany] = useState(false);

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
      setNiche(marketsRes.markets.find(market => market.id === marketId) ?? null);
      setSources(sourcesRes.sources);
      setCompanies(companiesRes.competitors);
      setSuggestions(suggestionsRes.suggestions);
      setStatus('ready');
      setSuggestionStatus('ready');
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

  const groupedSources = useMemo(() => {
    const groups = new Map<string, MonitoredSource[]>();
    sources.forEach(source => {
      const family = source.source_family ?? 'other';
      groups.set(family, [...(groups.get(family) ?? []), source]);
    });
    return [...groups.entries()].sort(([a], [b]) => familyLabel(a).localeCompare(familyLabel(b)));
  }, [sources]);

  const newSuggestions = suggestions.filter(suggestion => !suggestion.already_monitored);
  const activeCount = sources.filter(source => source.enabled).length;
  const errorCount = sources.filter(source => source.last_error).length;

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

  const toggleSource = async (source: MonitoredSource) => {
    const updated = await signalApi.updateSource(source.id, { enabled: !source.enabled });
    setSources(prev => prev.map(item => item.id === updated.id ? updated : item));
  };

  return (
    <DashboardShell
      title="Sources"
      subtitle={`Sources monitored for ${niche?.name ?? 'this niche'}.`}
      actions={
        <div className="flex flex-wrap justify-end gap-2">
          <NicheViewSwitcher marketId={marketId} active="sources" />
          <button onClick={() => setShowAddCompany(v => !v)} className="rounded-lg border border-slate-700/80 bg-slate-800/60 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-slate-600 hover:text-slate-100">
            Add company
          </button>
          <button onClick={() => setShowAddSource(v => !v)} className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-2 text-xs font-semibold text-violet-300 transition hover:bg-violet-500/15">
            Add source
          </button>
        </div>
      }
    >
      {status === 'loading' && <LoadingPanel label="Loading sources" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">
          <div className="grid gap-3 sm:grid-cols-4">
            <Summary label="Sources" value={sources.length} />
            <Summary label="Active" value={activeCount} accent={activeCount > 0} />
            <Summary label="Companies" value={companies.length} />
            <Summary label="Errors" value={errorCount} accent={errorCount > 0} danger={errorCount > 0} />
          </div>

          {showAddCompany && (
            <AddCompanyPanel
              onAdd={async company => {
                setCompanies(prev => [...prev, company]);
                setShowAddCompany(false);
                await load();
              }}
              onCancel={() => setShowAddCompany(false)}
              marketId={marketId}
            />
          )}

          {showAddSource && (
            <AddSourcePanel
              companies={companies}
              marketId={marketId}
              onAdd={async source => {
                setSources(prev => [source, ...prev]);
                setShowAddSource(false);
                await load();
              }}
              onCancel={() => setShowAddSource(false)}
            />
          )}

          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/70 px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-300">Suggested sources</h2>
                <p className="mt-1 text-xs text-slate-600">Review the highest-signal sources before adding them to the scan list.</p>
              </div>
              <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-500">
                {newSuggestions.length} new
              </span>
            </div>
            {suggestionStatus === 'loading' && <div className="p-5"><LoadingPanel label="Loading suggestions" /></div>}
            {suggestionStatus === 'ready' && newSuggestions.length === 0 && (
              <div className="p-5">
                <EmptyPanel title="No new suggestions" detail="The highest-ranked suggestions are already monitored." />
              </div>
            )}
            {suggestionStatus === 'ready' && newSuggestions.length > 0 && (
              <div className="divide-y divide-slate-800/60">
                {newSuggestions.slice(0, 8).map(suggestion => (
                  <div key={`${suggestion.template_id ?? suggestion.locator}-${suggestion.competitor_id ?? 'niche'}`} className="flex flex-wrap items-start justify-between gap-3 p-5">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-sm font-semibold text-slate-200">{suggestion.label}</h3>
                        <Chip label={familyLabel(suggestion.source_family)} />
                        {suggestion.competitor_name ? <Chip label={suggestion.competitor_name} /> : <Chip label="Niche-wide" />}
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-slate-500">{suggestion.rationale}</p>
                      <p className="mt-2 truncate font-mono text-[11px] text-slate-700">{suggestion.locator}</p>
                    </div>
                    <button onClick={() => addSuggestion(suggestion)} className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-2 text-xs font-semibold text-violet-300 transition hover:bg-violet-500/15">
                      Add
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="border-b border-slate-800/70 px-5 py-4">
              <h2 className="text-sm font-semibold text-slate-300">Monitored sources</h2>
            </div>
            {sources.length === 0 ? (
              <div className="p-5">
                <EmptyPanel title="No sources yet" detail="Add suggested sources or create a source manually." />
              </div>
            ) : (
              <div className="divide-y divide-slate-800/70">
                {groupedSources.map(([family, familySources]) => (
                  <div key={family} className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-600">{familyLabel(family)}</h3>
                      <span className="text-xs text-slate-700">{familySources.length} sources</span>
                    </div>
                    <div className="space-y-2">
                      {familySources.map(source => (
                        <SourceRow key={source.id} source={source} onToggle={() => toggleSource(source)} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function AddCompanyPanel({ marketId, onAdd, onCancel }: { marketId: string; onAdd: (company: Competitor) => void; onCancel: () => void }) {
  const [name, setName] = useState('');
  const [website, setWebsite] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const id = slugify(name);
      const company = await signalApi.createMarketCompetitor(marketId, {
        id,
        name,
        website: website.trim() || null,
      });
      onAdd(company);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add company');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-5">
      <h2 className="text-sm font-semibold text-slate-300">Add company</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Field label="Company name" value={name} onChange={setName} required />
        <Field label="Website" value={website} onChange={setWebsite} placeholder="https://example.com" />
      </div>
      {error && <p className="mt-3 text-xs text-rose-400">{error}</p>}
      <div className="mt-4 flex gap-2">
        <button disabled={submitting || !name.trim()} className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50">
          {submitting ? 'Adding...' : 'Add company'}
        </button>
        <button type="button" onClick={onCancel} className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-400 transition hover:text-slate-200">
          Cancel
        </button>
      </div>
    </form>
  );
}

function AddSourcePanel({ companies, marketId, onAdd, onCancel }: { companies: Competitor[]; marketId: string; onAdd: (source: MonitoredSource) => void; onCancel: () => void }) {
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
        <Field label="URL or API endpoint" value={locator} onChange={setLocator} required placeholder="https://..." />
        <Field label="Type" value={sourceType} onChange={setSourceType} required />
        <label className="block">
          <span className="text-xs font-medium text-slate-500">Scope</span>
          <select value={companyId} onChange={event => setCompanyId(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700/70 bg-slate-950/40 px-3 py-2 text-sm text-slate-300 outline-none focus:border-violet-500/40">
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
        <button disabled={submitting || !locator.trim()} className="rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50">
          {submitting ? 'Adding...' : 'Add source'}
        </button>
        <button type="button" onClick={onCancel} className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-400 transition hover:text-slate-200">
          Cancel
        </button>
      </div>
    </form>
  );
}

function SourceRow({ source, onToggle }: { source: MonitoredSource; onToggle: () => void }) {
  return (
    <div className="rounded-lg border border-slate-800/70 bg-slate-950/25 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {source.competitor_name ? <Chip label={source.competitor_name} /> : <Chip label="Niche-wide" />}
            <Chip label={source.source_type} />
            <span className={`rounded-md px-2 py-0.5 text-xs ${source.enabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800/70 text-slate-500'}`}>
              {source.enabled ? 'Active' : 'Paused'}
            </span>
          </div>
          <p className="mt-2 truncate font-mono text-xs text-slate-500">{source.locator}</p>
          {source.last_error && <p className="mt-1 text-xs text-rose-400">{source.last_error}</p>}
        </div>
        <button onClick={onToggle} className="rounded-lg border border-slate-700/80 px-3 py-1.5 text-xs font-semibold text-slate-400 transition hover:text-slate-100">
          {source.enabled ? 'Pause' : 'Enable'}
        </button>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, required }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; required?: boolean }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <input
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        className="mt-1 w-full rounded-lg border border-slate-700/70 bg-slate-950/40 px-3 py-2 text-sm text-slate-300 outline-none placeholder:text-slate-700 focus:border-violet-500/40"
      />
    </label>
  );
}

function Summary({ label, value, accent, danger }: { label: string; value: number; accent?: boolean; danger?: boolean }) {
  return (
    <div className={`rounded-xl border px-5 py-4 ${danger ? 'border-rose-500/20 bg-rose-500/[0.06]' : accent ? 'border-violet-500/20 bg-violet-600/[0.08]' : 'border-slate-800/80 bg-slate-900/50'}`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${danger ? 'text-rose-300' : accent ? 'text-violet-300' : 'text-slate-100'}`}>{value}</p>
    </div>
  );
}

function familyLabel(family: string | null) {
  return FAMILY_LABELS[family ?? 'other'] ?? family?.replace(/_/g, ' ') ?? FAMILY_LABELS.other;
}

function slugify(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
