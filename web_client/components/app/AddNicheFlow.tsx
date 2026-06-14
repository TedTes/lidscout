'use client';

import { type FormEvent, type KeyboardEvent as ReactKeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';
import { signalApi } from '@/lib/api';
import { Market } from '@/lib/types/signals';

interface TemplateCard {
  id: string;
  name: string;
  description: string;
  companies: string[];
  sourceFamilies: string[];
}

type CategoryFilter = 'all' | 'devtools' | 'data' | 'vertical_saas' | 'sales' | 'marketing' | 'more';
type Step = 'pick' | 'custom';

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (market: Market) => void;
  existingMarkets?: Market[];
};

const CATEGORY_LABELS: Record<CategoryFilter, string> = {
  all: 'All',
  devtools: 'Devtools',
  data: 'Data',
  vertical_saas: 'Vertical SaaS',
  sales: 'Sales',
  marketing: 'Marketing',
  more: 'More',
};

const inputCls =
  'w-full rounded-lg border border-slate-700/70 bg-slate-950/30 px-3 py-2.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/10';

const labelCls = 'text-[10px] font-semibold uppercase tracking-wider text-slate-600';

function toSlug(name: string) {
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
}

function normalize(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase().replace(/\s+/g, ' ');
}

function categoryForTemplate(template: TemplateCard): CategoryFilter {
  const text = `${template.id} ${template.name} ${template.description} ${template.sourceFamilies.join(' ')}`.toLowerCase();
  if (/dbt|warehouse|data|analytics|etl|pipeline|sql/.test(text)) return 'data';
  if (/crm|sales|pipeline|revenue|lead/.test(text)) return 'sales';
  if (/marketing|campaign|seo|content|ads/.test(text)) return 'marketing';
  if (/therapy|ehr|construction|clinic|dental|legal|vertical|practice|billing/.test(text)) return 'vertical_saas';
  if (/devtool|developer|deploy|frontend|backend|admin|database|error|api|github|devops/.test(text)) return 'devtools';
  return 'more';
}

function sourceAccessLabel(template: TemplateCard) {
  const hasProxyLikelySource = template.sourceFamilies.some(family =>
    /review|g2|capterra|trust/.test(family.toLowerCase())
  );
  return hasProxyLikelySource ? 'Proxy required' : 'All sources gate-free';
}

function IconX() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconChevronLeft() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function LoadingTemplates() {
  return (
    <div className="px-8 py-6">
      <div className="mb-5 flex items-center gap-3 text-sm font-medium text-slate-400">
        <span className="flex h-5 w-5 items-center justify-center rounded-full border border-violet-400/20 bg-violet-500/10 text-violet-300">
          <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-90" d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
        </span>
        Loading curated markets...
      </div>
      <div className="space-y-3">
        {[0, 1, 2].map(index => (
          <div
            key={index}
            className="grid grid-cols-[minmax(0,1fr)_auto] gap-5 rounded-xl border border-white/10 bg-white/[0.02] p-4"
          >
            <div className="min-w-0 space-y-3">
              <div className="h-4 w-64 max-w-full animate-pulse rounded bg-white/10" />
              <div className="h-3 w-full max-w-2xl animate-pulse rounded bg-white/[0.07]" />
              <div className="flex gap-2">
                <div className="h-6 w-20 animate-pulse rounded-full bg-white/[0.06]" />
                <div className="h-6 w-24 animate-pulse rounded-full bg-white/[0.06]" />
                <div className="h-6 w-16 animate-pulse rounded-full bg-white/[0.06]" />
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="h-7 w-20 animate-pulse rounded-full bg-white/[0.06]" />
              <div className="h-7 w-28 animate-pulse rounded-full bg-white/[0.06]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TemplatePickerStep({
  loading,
  templates,
  existingMarkets,
  creatingTemplateId,
  error,
  onSelect,
  onCustom,
}: {
  loading: boolean;
  templates: TemplateCard[];
  existingMarkets: Market[];
  creatingTemplateId: string | null;
  error: string | null;
  onSelect: (template: TemplateCard) => void;
  onCustom: () => void;
}) {
  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<CategoryFilter>('all');
  const [focusedIndex, setFocusedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 40);
    return () => clearTimeout(timer);
  }, []);

  const existingNames = useMemo(
    () => new Set(existingMarkets.flatMap(market => [
      normalize(market.name),
      normalize(market.display_label),
    ]).filter(Boolean)),
    [existingMarkets],
  );
  const existingTemplateIds = useMemo(
    () => new Set(existingMarkets.map(market => market.template_niche_id).filter(Boolean)),
    [existingMarkets],
  );

  const templatesWithCategory = useMemo(
    () => templates.map(template => ({
      template,
      category: categoryForTemplate(template),
    })).filter(({ template }) =>
      !existingTemplateIds.has(template.id)
      && !existingNames.has(normalize(template.name))
    ),
    [existingNames, existingTemplateIds, templates],
  );

  const counts = useMemo(() => {
    const next: Record<CategoryFilter, number> = {
      all: templatesWithCategory.length,
      devtools: 0,
      data: 0,
      vertical_saas: 0,
      sales: 0,
      marketing: 0,
      more: 0,
    };
    for (const item of templatesWithCategory) next[item.category] += 1;
    return next;
  }, [templatesWithCategory]);

  const filtered = useMemo(() => {
    const normalizedQuery = normalize(query);
    return templatesWithCategory.filter(({ template, category }) => {
      if (activeCategory !== 'all' && category !== activeCategory) return false;
      if (!normalizedQuery) return true;
      const haystack = normalize([
        template.name,
        template.description,
        template.companies.join(' '),
        template.sourceFamilies.join(' '),
      ].join(' '));
      return haystack.includes(normalizedQuery);
    });
  }, [activeCategory, query, templatesWithCategory]);

  // Reset focused index when results change
  useEffect(() => { setFocusedIndex(0); }, [query, activeCategory]);

  // Scroll focused row into view
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const rows = list.querySelectorAll<HTMLButtonElement>('[data-picker-row]');
    rows[focusedIndex]?.scrollIntoView({ block: 'nearest' });
  }, [focusedIndex]);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setFocusedIndex(i => filtered.length === 0 ? 0 : Math.min(i + 1, filtered.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setFocusedIndex(i => Math.max(i - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const target = filtered[focusedIndex];
      if (target) onSelect(target.template);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="px-8 pb-4">
        <div className="relative">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
            <IconSearch />
          </span>
          <input
            ref={inputRef}
            value={query}
            onChange={event => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search by job, tool, or buyer - e.g. 'shopify', 'devtools', 'therapy'"
            className="w-full rounded-xl border border-white/10 bg-black/15 py-4 pl-11 pr-4 text-base font-medium text-slate-100 outline-none placeholder:text-slate-500 focus:border-violet-500/40"
          />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-slate-500">Filter:</span>
          {(Object.keys(CATEGORY_LABELS) as CategoryFilter[]).map(category => (
            <button
              key={category}
              type="button"
              onClick={() => setActiveCategory(category)}
              className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition ${
                activeCategory === category
                  ? 'border-violet-400/20 bg-violet-100 text-violet-700'
                  : 'border-white/10 bg-white/[0.025] text-slate-400 hover:border-white/20 hover:text-slate-200'
              }`}
            >
              {CATEGORY_LABELS[category]}
              <span className="ml-1 text-current opacity-65">· {counts[category]}</span>
            </button>
          ))}
          <button
            type="button"
            onClick={onCustom}
            className="ml-auto rounded-full border border-dashed border-white/10 px-4 py-1.5 text-sm font-semibold text-slate-500 transition hover:border-white/20 hover:text-slate-300"
          >
            Custom
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </div>

      <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto border-t border-white/10">
        {loading && (
          <LoadingTemplates />
        )}
        {!loading && filtered.length === 0 && (
          <div className="px-8 py-12 text-sm text-slate-500">No curated markets match that search.</div>
        )}
        {!loading && filtered.map(({ template, category }) => {
          const accessLabel = sourceAccessLabel(template);
          const creating = creatingTemplateId === template.id;
          const disabled = creatingTemplateId !== null;
          const selectableIdx = filtered.findIndex(s => s.template.id === template.id);
          const isFocused = selectableIdx === focusedIndex;
          return (
            <button
              key={template.id}
              type="button"
              data-picker-row=""
              disabled={disabled}
              onClick={() => onSelect(template)}
              onMouseEnter={() => setFocusedIndex(selectableIdx)}
              className={`group grid w-full grid-cols-[minmax(0,1fr)_auto] gap-5 border-b border-white/10 px-8 py-5 text-left transition ${
                isFocused
                  ? 'bg-white/[0.05]'
                  : 'hover:bg-white/[0.035]'
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-start gap-3">
                  <h3 className="max-w-2xl text-base font-bold leading-tight text-slate-100">
                    {template.name}
                  </h3>
                  {isFocused && !query && (
                    <span className="hidden text-xs text-slate-600 sm:inline">Enter</span>
                  )}
                </div>
                <p className="mt-1 max-w-3xl text-sm font-medium leading-snug text-slate-400">
                  {template.description}
                  <span className="text-slate-500"> · {plural(template.companies.length, 'tool')} · {plural(Math.max(template.sourceFamilies.length, 1), 'source')}</span>
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {template.companies.slice(0, 5).map(company => (
                    <span key={company} className="rounded-full bg-black/20 px-2.5 py-1 text-xs font-semibold text-slate-400">
                      {company}
                    </span>
                  ))}
                  {template.companies.length > 5 && (
                    <span className="rounded-full px-2.5 py-1 text-xs font-semibold text-slate-500">
                      +{template.companies.length - 5}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex min-w-[185px] flex-col items-end gap-2">
                <div className="flex flex-wrap justify-end gap-2">
                  <span className="rounded-full bg-black/20 px-3 py-1 text-xs font-semibold text-slate-400">
                    {CATEGORY_LABELS[category]}
                  </span>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    accessLabel === 'Proxy required'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {accessLabel}
                  </span>
                </div>
                {creating && (
                  <span className="text-xs font-semibold text-violet-400">Adding...</span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function plural(n: number, singular: string, pluralForm = `${singular}s`) {
  return `${n} ${n === 1 ? singular : pluralForm}`;
}

function IconAlertCircle() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function CustomStep({
  onCreated,
  onBack,
}: {
  onCreated: (market: Market) => void;
  onBack: () => void;
  onClose: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetUser, setTargetUser] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => nameRef.current?.focus(), 30);
    return () => clearTimeout(timer);
  }, []);

  const handleNameChange = (event: FormEvent<HTMLInputElement>) => {
    setName((event.target as HTMLInputElement).value);
    if (error) setError(null);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) return;
    setSaving(true);
    setError(null);
    try {
      const market = await signalApi.createMarket({
        id: toSlug(trimmedName),
        name: trimmedName,
        description: description.trim() || null,
        target_user: targetUser.trim() || null,
      });
      onCreated(market);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong, please try again.');
      setSaving(false);
      setTimeout(() => nameRef.current?.focus(), 50);
    }
  };

  const nameHasError = !!error;

  return (
    <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-8 pb-8 pt-2">

        <div className="flex flex-col gap-1.5">
          <label htmlFor="custom-market-name" className={labelCls}>Market name *</label>
          <input
            ref={nameRef}
            id="custom-market-name"
            required
            value={name}
            onChange={handleNameChange}
            placeholder="e.g. Manage customer support for a SaaS product"
            className={`${inputCls} ${nameHasError ? 'border-rose-500/60 focus:border-rose-500/80 focus:ring-rose-500/10' : ''}`}
            autoComplete="off"
          />
          {!nameHasError && (
            <p className="text-[11px] text-slate-600">Describe a real job-to-be-done or problem space — e.g. "podcast hosting for indie creators".</p>
          )}
          {nameHasError && (
            <div className="flex items-start gap-2 rounded-lg border border-rose-500/25 bg-rose-500/[0.07] px-3 py-2.5">
              <span className="mt-px shrink-0 text-rose-400"><IconAlertCircle /></span>
              <p className="text-sm leading-snug text-rose-300">{error}</p>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="custom-market-description" className={labelCls}>Description</label>
          <input
            id="custom-market-description"
            value={description}
            onChange={event => setDescription(event.target.value)}
            placeholder="Problem space or market focus"
            className={inputCls}
            autoComplete="off"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="custom-market-target" className={labelCls}>Target user</label>
          <input
            id="custom-market-target"
            value={targetUser}
            onChange={event => setTargetUser(event.target.value)}
            placeholder="e.g. Seed-stage founders"
            className={inputCls}
            autoComplete="off"
          />
        </div>

        <p className="text-sm leading-relaxed text-slate-500">
          You can add companies and sources after creating the market.
        </p>

      </div>

      <div className="flex items-center gap-2 border-t border-white/10 px-8 py-5">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving && (
            <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
              <path className="opacity-90" d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
          )}
          {saving ? 'Validating market…' : 'Create market'}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={saving}
          className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-slate-400 transition hover:text-slate-200 disabled:opacity-40"
        >
          Back
        </button>
      </div>
    </form>
  );
}

export function AddNicheFlow({
  isOpen,
  onClose,
  onCreated,
  existingMarkets = [],
}: Props) {
  const [step, setStep] = useState<Step>('pick');
  const [templates, setTemplates] = useState<TemplateCard[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [creatingTemplateId, setCreatingTemplateId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setStep('pick');
    setCreatingTemplateId(null);
    setError(null);
    setTemplatesLoading(true);
    signalApi.getTemplates()
      .then(response => {
        setTemplates(response.templates.map(template => ({
          id: template.id,
          name: template.name,
          description: template.description,
          companies: template.company_names,
          sourceFamilies: template.source_families,
        })));
      })
      .catch(() => setTemplates([]))
      .finally(() => setTemplatesLoading(false));
  }, [isOpen]);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    if (isOpen) panel.removeAttribute('inert');
    else panel.setAttribute('inert', '');
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const handleSelectTemplate = async (template: TemplateCard) => {
    setCreatingTemplateId(template.id);
    setError(null);
    try {
      const market = await signalApi.applyTemplate(template.id);
      onCreated(market);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add market');
      setCreatingTemplateId(null);
    }
  };

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`fixed inset-0 z-[35] bg-black/60 backdrop-blur-sm transition-opacity duration-200 ${isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Add market"
        className={`fixed inset-x-4 top-[7vh] z-40 mx-auto flex max-h-[86vh] max-w-6xl flex-col overflow-hidden rounded-2xl border border-white/15 bg-[#20211f] shadow-[0_24px_80px_rgba(0,0,0,0.75)] transition duration-200 ${
          isOpen
            ? 'translate-y-0 opacity-100'
            : 'pointer-events-none translate-y-4 opacity-0'
        }`}
      >
        <div className="flex shrink-0 items-start justify-between px-8 pb-5 pt-7">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {step === 'custom' && (
                <button
                  type="button"
                  onClick={() => setStep('pick')}
                  className="rounded p-1 text-slate-500 transition hover:bg-white/5 hover:text-slate-300"
                  aria-label="Back"
                >
                  <IconChevronLeft />
                </button>
              )}
              <h2 className="text-xl font-bold tracking-tight text-slate-100">
                {step === 'custom' ? 'Create a custom market' : 'Add a market to monitor'}
              </h2>
            </div>
            <p className="mt-2 max-w-xl text-sm font-medium leading-snug text-slate-400">
              {step === 'custom'
                ? 'Define a market manually. You can add companies, sources, and research scope next.'
                : 'Pick a curated template - companies, sources, and research brief are pre-configured'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-2 text-slate-500 transition hover:bg-white/5 hover:text-slate-300"
          >
            <IconX />
          </button>
        </div>

        {step === 'pick' && (
          <TemplatePickerStep
            loading={templatesLoading}
            templates={templates}
            existingMarkets={existingMarkets}
            creatingTemplateId={creatingTemplateId}
            error={error}
            onSelect={handleSelectTemplate}
            onCustom={() => setStep('custom')}
          />
        )}

        {step === 'custom' && (
          <CustomStep
            onCreated={onCreated}
            onBack={() => setStep('pick')}
            onClose={onClose}
          />
        )}
      </div>
    </>
  );
}
