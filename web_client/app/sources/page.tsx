'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import { ErrorPanel, LoadingPanel, Metric } from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { Competitor, MonitoredSource, SourceSuggestion } from '@/lib/types/signals';

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconPlus() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconPencil() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconWarn() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function IconChevron({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function toSlug(name: string): string {
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
}

function relativeTime(value: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (isNaN(date.getTime())) return '—';
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputCls =
  'rounded-md border border-slate-700/60 bg-slate-800/60 px-2.5 py-1.5 text-xs text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/10 disabled:opacity-40';

const btnPrimary =
  'inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed';

const btnSecondary =
  'inline-flex items-center gap-1.5 rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:border-slate-600 hover:text-slate-200 disabled:opacity-50';

// ── Page ──────────────────────────────────────────────────────────────────────

type LoadStatus = 'loading' | 'ready' | 'error';

export default function SourcesPage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [sources, setSources] = useState<MonitoredSource[]>([]);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);

  // Add competitor
  const [showAddComp, setShowAddComp] = useState(false);
  const [compForm, setCompForm] = useState({ name: '', website: '', category: '' });
  const [addCompError, setAddCompError] = useState<string | null>(null);
  const [savingComp, setSavingComp] = useState(false);

  // Add source
  const [showAddSource, setShowAddSource] = useState(false);
  const [sourceForm, setSourceForm] = useState({
    competitor_id: '', locator: '', source_type: '', limit: '',
  });
  const [addSourceError, setAddSourceError] = useState<string | null>(null);
  const [savingSource, setSavingSource] = useState(false);

  // Toggle enable/disable
  const [togglingIds, setTogglingIds] = useState<Set<string>>(new Set());

  // Inline edit
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ source_type: '', limit: '' });
  const [editError, setEditError] = useState<string | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);

  // Filter
  const [filterCompId, setFilterCompId] = useState('all');

  // Suggestions
  const [expandedCompId, setExpandedCompId] = useState<string | null>(null);
  const [suggestionsCache, setSuggestionsCache] = useState<Map<string, SourceSuggestion[]>>(new Map());
  const [suggestionsLoadingIds, setSuggestionsLoadingIds] = useState<Set<string>>(new Set());
  const [suggestionsErrors, setSuggestionsErrors] = useState<Map<string, string>>(new Map());
  const [addingLocators, setAddingLocators] = useState<Set<string>>(new Set());

  // ── Load ────────────────────────────────────────────────────────────────────

  const load = async () => {
    setLoadStatus('loading');
    setLoadError(null);
    try {
      const [compRes, srcRes] = await Promise.all([
        signalApi.getCompetitors(),
        signalApi.getSources(),
      ]);
      setCompetitors(compRes.competitors);
      setSources(srcRes.sources);
      setLoadStatus('ready');
      if (compRes.competitors.length > 0) {
        const firstCompetitorId = compRes.competitors[0].id;
        setExpandedCompId(firstCompetitorId);
        void loadSuggestionsFor(firstCompetitorId);
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load data');
      setLoadStatus('error');
    }
  };

  useEffect(() => { load(); }, []);

  // ── Derived ─────────────────────────────────────────────────────────────────

  const competitorById = useMemo(() => {
    const m = new Map<string, Competitor>();
    competitors.forEach(c => m.set(c.id, c));
    return m;
  }, [competitors]);

  const sourceCountByCompId = useMemo(() => {
    const m = new Map<string, number>();
    sources.forEach(s => m.set(s.competitor_id, (m.get(s.competitor_id) ?? 0) + 1));
    return m;
  }, [sources]);

  const filteredSources = useMemo(
    () => filterCompId === 'all' ? sources : sources.filter(s => s.competitor_id === filterCompId),
    [sources, filterCompId],
  );

  const activeCount = sources.filter(s => s.enabled).length;
  const errorCount = sources.filter(s => s.last_error).length;

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleAddCompetitor = async (e: FormEvent) => {
    e.preventDefault();
    setSavingComp(true);
    setAddCompError(null);
    try {
      const created = await signalApi.createCompetitor({
        id: toSlug(compForm.name),
        name: compForm.name,
        website: compForm.website || null,
        category: compForm.category || null,
      });
      setCompetitors(prev => [...prev, created]);
      setCompForm({ name: '', website: '', category: '' });
      setShowAddComp(false);
    } catch (err) {
      setAddCompError(err instanceof Error ? err.message : 'Failed to create company');
    } finally {
      setSavingComp(false);
    }
  };

  const handleAddSource = async (e: FormEvent) => {
    e.preventDefault();
    setSavingSource(true);
    setAddSourceError(null);
    try {
      const created = await signalApi.createCompetitorSource(sourceForm.competitor_id, {
        locator: sourceForm.locator,
        source_type: sourceForm.source_type || undefined,
        limit: sourceForm.limit ? Number(sourceForm.limit) : null,
      });
      setSources(prev => [...prev, created]);
      setSourceForm(f => ({ ...f, locator: '', source_type: '', limit: '' }));
      setShowAddSource(false);
    } catch (err) {
      setAddSourceError(err instanceof Error ? err.message : 'Failed to create source');
    } finally {
      setSavingSource(false);
    }
  };

  const handleToggle = async (source: MonitoredSource) => {
    setTogglingIds(prev => new Set(prev).add(source.id));
    try {
      const updated = await signalApi.updateSource(source.id, { enabled: !source.enabled });
      setSources(prev => prev.map(s => s.id === updated.id ? updated : s));
    } finally {
      setTogglingIds(prev => { const n = new Set(prev); n.delete(source.id); return n; });
    }
  };

  const startEdit = (source: MonitoredSource) => {
    setEditingId(source.id);
    setEditForm({ source_type: source.source_type ?? '', limit: source.limit != null ? String(source.limit) : '' });
    setEditError(null);
  };

  const handleEditSave = async () => {
    if (!editingId) return;
    setSavingEdit(true);
    setEditError(null);
    try {
      const updated = await signalApi.updateSource(editingId, {
        source_type: editForm.source_type || null,
        limit: editForm.limit ? Number(editForm.limit) : null,
      });
      setSources(prev => prev.map(s => s.id === updated.id ? updated : s));
      setEditingId(null);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSavingEdit(false);
    }
  };

  const openAddSourceFor = (competitorId: string) => {
    setSourceForm(f => ({ ...f, competitor_id: competitorId }));
    setShowAddSource(true);
  };

  // Suggestions ───────────────────────────────────────────────────────────────

  const loadSuggestionsFor = async (competitorId: string) => {
    if (suggestionsCache.has(competitorId)) return;

    setSuggestionsLoadingIds(prev => new Set(prev).add(competitorId));
    try {
      const res = await signalApi.getCompetitorSourceSuggestions(competitorId);
      setSuggestionsCache(prev => new Map([...prev, [competitorId, res.suggestions]]));
      setSuggestionsErrors(prev => { const m = new Map(prev); m.delete(competitorId); return m; });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load suggestions';
      setSuggestionsErrors(prev => new Map([...prev, [competitorId, msg]]));
    } finally {
      setSuggestionsLoadingIds(prev => { const s = new Set(prev); s.delete(competitorId); return s; });
    }
  };

  const toggleSuggestions = async (competitorId: string) => {
    if (expandedCompId === competitorId) {
      setExpandedCompId(null);
      return;
    }
    setExpandedCompId(competitorId);
    await loadSuggestionsFor(competitorId);
  };

  const handleAddFromSuggestion = async (competitorId: string, suggestion: SourceSuggestion) => {
    setAddingLocators(prev => new Set(prev).add(suggestion.locator));
    try {
      const created = await signalApi.createCompetitorSource(competitorId, {
        locator: suggestion.locator,
        source_type: suggestion.source_type,
        limit: suggestion.limit ?? null,
        options: suggestion.options,
      });
      setSources(prev => [...prev, created]);
      // Mark as monitored in cache
      setSuggestionsCache(prev => {
        const cached = prev.get(competitorId);
        if (!cached) return prev;
        const updated = cached.map(s =>
          s.locator === suggestion.locator ? { ...s, already_monitored: true } : s,
        );
        return new Map([...prev, [competitorId, updated]]);
      });
    } catch {
      // The button re-enables via finally; no inline error needed here
    } finally {
      setAddingLocators(prev => { const s = new Set(prev); s.delete(suggestion.locator); return s; });
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <DashboardShell title="Sources" subtitle="Companies and their monitored scan sources">

      {loadStatus === 'loading' && <LoadingPanel label="Loading sources" />}
      {loadStatus === 'error' && loadError && <ErrorPanel message={loadError} />}

      {loadStatus === 'ready' && (
        <>
          {/* Stats */}
          <div className="mb-5 grid gap-3 sm:grid-cols-3">
            <Metric label="Companies" value={competitors.length} />
            <Metric label="Active sources" value={activeCount} />
            <Metric label="Source errors" value={errorCount} accent={errorCount > 0} />
          </div>

          {/* ── Competitors ─────────────────────────────────────────── */}
          <section className="mb-5 rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-200">Companies</h2>
              <button
                onClick={() => { setShowAddComp(v => !v); setAddCompError(null); }}
                className={btnSecondary}
              >
                <IconPlus /> Add
              </button>
            </div>

            {/* Add competitor form */}
            {showAddComp && (
              <form onSubmit={handleAddCompetitor} className="border-b border-slate-800/60 bg-slate-800/20 px-4 py-3">
                <div className="flex flex-wrap items-end gap-2">
                  <Field label="Name *">
                    <input required value={compForm.name} onChange={e => setCompForm(f => ({ ...f, name: e.target.value }))} placeholder="Acme Corp" className={`${inputCls} w-40`} />
                  </Field>
                  <Field label="Category">
                    <input value={compForm.category} onChange={e => setCompForm(f => ({ ...f, category: e.target.value }))} placeholder="SaaS" className={`${inputCls} w-28`} />
                  </Field>
                  <Field label="Website">
                    <input value={compForm.website} onChange={e => setCompForm(f => ({ ...f, website: e.target.value }))} placeholder="acme.com" className={`${inputCls} w-36`} />
                  </Field>
                  <div className="flex items-center gap-2 pt-4">
                    <button type="submit" disabled={savingComp} className={btnPrimary}>{savingComp ? 'Saving…' : 'Add'}</button>
                    <button type="button" onClick={() => setShowAddComp(false)} className={btnSecondary}>Cancel</button>
                  </div>
                </div>
                {addCompError && <div className="mt-2"><ErrorPanel message={addCompError} /></div>}
              </form>
            )}

            {/* Competitors table */}
            {competitors.length === 0 ? (
              <div className="px-4 py-10 text-center text-xs text-slate-600">
                No companies yet. Add one to start monitoring.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <div className="grid grid-cols-[1fr_100px_140px_60px_90px_110px] gap-x-3 px-4 py-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
                  <span>Name</span><span>Category</span><span>Website</span>
                  <span>Sources</span><span /><span />
                </div>
                {competitors.map(comp => (
                  <div key={comp.id}>
                    {/* Competitor row */}
                    <div className="grid grid-cols-[1fr_100px_140px_60px_90px_110px] items-center gap-x-3 border-t border-slate-800/50 px-4 py-2.5 text-xs hover:bg-white/[0.01]">
                      <span className="font-medium text-slate-300">{comp.name}</span>
                      <span className="text-slate-500">{comp.category ?? '—'}</span>
                      <span className="truncate font-mono text-[11px] text-slate-600">{comp.website ?? '—'}</span>
                      <span className="tabular-nums text-slate-500">{sourceCountByCompId.get(comp.id) ?? 0}</span>
                      <button onClick={() => openAddSourceFor(comp.id)} className="text-[11px] font-medium text-violet-500 hover:text-violet-400 transition text-left">
                        + source
                      </button>
                      <button
                        onClick={() => toggleSuggestions(comp.id)}
                        className={`inline-flex items-center justify-end gap-1.5 rounded px-2 py-1 text-[11px] font-medium transition ${expandedCompId === comp.id ? 'bg-violet-500/10 text-violet-400' : 'text-slate-500 hover:bg-slate-800/60 hover:text-slate-300'}`}
                      >
                        Suggestions
                        <IconChevron expanded={expandedCompId === comp.id} />
                      </button>
                    </div>

                    {/* Suggestion panel */}
                    {expandedCompId === comp.id && (
                      <SuggestionPanel
                        competitorId={comp.id}
                        suggestions={suggestionsCache.get(comp.id)}
                        loading={suggestionsLoadingIds.has(comp.id)}
                        error={suggestionsErrors.get(comp.id) ?? null}
                        addingLocators={addingLocators}
                        onAdd={(s) => handleAddFromSuggestion(comp.id, s)}
                        btnPrimary={btnPrimary}
                      />
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── Sources ─────────────────────────────────────────────── */}
          <section className="rounded-xl border border-slate-800/80 bg-slate-900/40">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-200">Monitored sources</h2>
              <div className="flex items-center gap-2">
                <select value={filterCompId} onChange={e => setFilterCompId(e.target.value)} className={`${inputCls} pr-6`}>
                  <option value="all">All companies</option>
                  {competitors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <button onClick={() => { setShowAddSource(v => !v); setAddSourceError(null); }} className={btnSecondary}>
                  <IconPlus /> Add source
                </button>
              </div>
            </div>

            {/* Add source form */}
            {showAddSource && (
              <form onSubmit={handleAddSource} className="border-b border-slate-800/60 bg-slate-800/20 px-4 py-3">
                <div className="flex flex-wrap items-end gap-2">
                  <Field label="Company *">
                    <select required value={sourceForm.competitor_id} onChange={e => setSourceForm(f => ({ ...f, competitor_id: e.target.value }))} className={`${inputCls} w-36`}>
                      <option value="">Select…</option>
                      {competitors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </Field>
                  <Field label="Locator *">
                    <input required value={sourceForm.locator} onChange={e => setSourceForm(f => ({ ...f, locator: e.target.value }))} placeholder="https://…" className={`${inputCls} w-56 font-mono`} />
                  </Field>
                  <Field label="Type">
                    <input value={sourceForm.source_type} onChange={e => setSourceForm(f => ({ ...f, source_type: e.target.value }))} placeholder="reddit / g2 / hn" className={`${inputCls} w-28`} />
                  </Field>
                  <Field label="Limit">
                    <input type="number" min={1} value={sourceForm.limit} onChange={e => setSourceForm(f => ({ ...f, limit: e.target.value }))} placeholder="25" className={`${inputCls} w-20`} />
                  </Field>
                  <div className="flex items-center gap-2 pt-4">
                    <button type="submit" disabled={savingSource} className={btnPrimary}>{savingSource ? 'Saving…' : 'Add'}</button>
                    <button type="button" onClick={() => setShowAddSource(false)} className={btnSecondary}>Cancel</button>
                  </div>
                </div>
                {addSourceError && <div className="mt-2"><ErrorPanel message={addSourceError} /></div>}
              </form>
            )}

            {/* Sources table */}
            {filteredSources.length === 0 ? (
              <div className="px-4 py-10 text-center text-xs text-slate-600">
                {sources.length === 0
                  ? 'No sources configured. Add a source or use suggestions from a company row.'
                  : 'No sources match the selected filter.'}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <div className="grid grid-cols-[110px_1fr_80px_80px_55px_90px_24px_48px] items-center gap-x-3 px-4 py-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
                  <span>Company</span><span>Locator</span><span>Type</span>
                  <span>Status</span><span>Limit</span><span>Last scan</span>
                  <span /><span />
                </div>

                {filteredSources.map(source => {
                  const comp = competitorById.get(source.competitor_id);
                  const isToggling = togglingIds.has(source.id);
                  const isEditing = editingId === source.id;

                  return (
                    <div key={source.id}>
                      <div className={`group grid grid-cols-[110px_1fr_80px_80px_55px_90px_24px_48px] items-center gap-x-3 border-t border-slate-800/50 px-4 py-2.5 text-xs transition-colors hover:bg-white/[0.01] ${source.last_error ? 'border-l-2 border-l-amber-500/40' : ''}`}>
                        <span className="truncate text-[11px] text-slate-400">{comp?.name ?? source.competitor_id}</span>
                        <span className="truncate font-mono text-[11px] text-slate-400" title={source.locator}>{source.locator}</span>
                        <span className="truncate text-slate-500">{source.source_type ?? '—'}</span>
                        <button
                          onClick={() => handleToggle(source)}
                          disabled={isToggling}
                          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium transition ${source.enabled ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/15' : 'border-slate-700/50 bg-slate-800/50 text-slate-600 hover:border-slate-600'} disabled:opacity-50`}
                        >
                          {isToggling
                            ? <span className="h-1.5 w-1.5 animate-spin rounded-full border border-current border-t-transparent" />
                            : <span className={`h-1.5 w-1.5 rounded-full ${source.enabled ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                          }
                          {source.enabled ? 'Active' : 'Paused'}
                        </button>
                        <span className="tabular-nums text-slate-500">{source.limit ?? '—'}</span>
                        <span className="tabular-nums text-[11px] text-slate-600" title={source.last_scanned_at ?? undefined}>{relativeTime(source.last_scanned_at)}</span>
                        <span>{source.last_error && <span className="text-amber-500" title={source.last_error}><IconWarn /></span>}</span>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => isEditing ? setEditingId(null) : startEdit(source)}
                            className={`rounded p-1 transition ${isEditing ? 'bg-violet-500/10 text-violet-400' : 'text-slate-700 opacity-0 hover:text-slate-400 group-hover:opacity-100'}`}
                          >
                            {isEditing ? <IconX /> : <IconPencil />}
                          </button>
                        </div>
                      </div>

                      {/* Inline edit row */}
                      {isEditing && (
                        <div className="border-t border-violet-500/10 bg-violet-500/[0.03] px-4 py-3">
                          <div className="flex flex-wrap items-end gap-2">
                            <Field label="Source type">
                              <input value={editForm.source_type} onChange={e => setEditForm(f => ({ ...f, source_type: e.target.value }))} placeholder="reddit / g2 / hn" className={`${inputCls} w-32`} />
                            </Field>
                            <Field label="Limit">
                              <input type="number" min={1} value={editForm.limit} onChange={e => setEditForm(f => ({ ...f, limit: e.target.value }))} placeholder="25" className={`${inputCls} w-20`} />
                            </Field>
                            <div className="flex items-center gap-2 pt-4">
                              <button onClick={handleEditSave} disabled={savingEdit} className={btnPrimary}><IconCheck />{savingEdit ? 'Saving…' : 'Save'}</button>
                              <button onClick={() => setEditingId(null)} className={btnSecondary}>Cancel</button>
                            </div>
                          </div>
                          {source.last_error && <p className="mt-2 text-[11px] text-amber-500/80">Last error: {source.last_error}</p>}
                          {editError && <div className="mt-2"><ErrorPanel message={editError} /></div>}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}
    </DashboardShell>
  );
}

// ── Suggestion panel ─────────────────────────────────────────────────────────

function SuggestionPanel({
  competitorId: _competitorId,
  suggestions,
  loading,
  error,
  addingLocators,
  onAdd,
  btnPrimary,
}: {
  competitorId: string;
  suggestions: SourceSuggestion[] | undefined;
  loading: boolean;
  error: string | null;
  addingLocators: Set<string>;
  onAdd: (suggestion: SourceSuggestion) => void;
  btnPrimary: string;
}) {
  return (
    <div className="border-t border-violet-500/10 bg-slate-950/40">
      {loading && (
        <div className="px-4 py-3">
          <LoadingPanel label="Loading suggestions" />
        </div>
      )}
      {error && (
        <div className="px-4 py-3">
          <ErrorPanel message={error} />
        </div>
      )}
      {!loading && !error && (
        <>
          <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
            Suggested sources {suggestions && suggestions.length > 0 && `· ${suggestions.length}`}
          </div>
          {(!suggestions || suggestions.length === 0) ? (
            <div className="px-4 pb-3 text-xs text-slate-700">No suggestions available.</div>
          ) : (
            suggestions.map(suggestion => (
              <div
                key={suggestion.locator}
                className="flex items-start justify-between gap-4 border-t border-slate-800/30 px-4 py-2.5"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-medium text-slate-300">{suggestion.label}</span>
                    <span className="rounded bg-slate-800/80 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
                      {suggestion.source_type}
                    </span>
                    <span className="truncate font-mono text-[10px] text-slate-600" title={suggestion.locator}>
                      {suggestion.locator}
                    </span>
                  </div>
                  {suggestion.rationale && (
                    <p className="mt-0.5 text-[11px] leading-snug text-slate-600">{suggestion.rationale}</p>
                  )}
                </div>
                <div className="shrink-0 pt-0.5">
                  {suggestion.already_monitored ? (
                    <span className="inline-flex items-center gap-1 rounded border border-emerald-500/20 bg-emerald-500/[0.08] px-2 py-0.5 text-[11px] font-medium text-emerald-500">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Monitored
                    </span>
                  ) : (
                    <button
                      onClick={() => onAdd(suggestion)}
                      disabled={addingLocators.has(suggestion.locator)}
                      className={btnPrimary}
                    >
                      {addingLocators.has(suggestion.locator) ? 'Adding…' : '+ Add'}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}

// ── Field wrapper ─────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">{label}</span>
      {children}
    </div>
  );
}
