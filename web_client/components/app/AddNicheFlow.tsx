'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { signalApi } from '@/lib/api';
import { Market } from '@/lib/types/signals';

interface TemplateCard {
  id: string;
  name: string;
  description: string;
  companies: string[];
  sourceFamilies: string[];
}

// ── Shared styles ──────────────────────────────────────────────────────────────

const inputCls =
  'w-full rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/10';

const labelCls = 'text-[10px] font-semibold uppercase tracking-wider text-slate-600';

function toSlug(name: string) {
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
}

// ── Icons ──────────────────────────────────────────────────────────────────────

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
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

// ── Step: Template Picker ──────────────────────────────────────────────────────

function TemplatePickerStep({
  loading,
  templates,
  onSelect,
  onCustom,
}: {
  loading: boolean;
  templates: TemplateCard[];
  onSelect: (template: TemplateCard) => void;
  onCustom: () => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-1 px-5 pb-3 pt-1">
        <p className="text-xs text-slate-500">
          Start with a curated niche — companies, sources, and a research brief are pre-configured.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
        {loading && (
          <p className="mb-3 text-xs text-slate-600">Loading curated niches…</p>
        )}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {templates.map(t => (
            <button
              key={t.id}
              onClick={() => onSelect(t)}
              className="group flex flex-col gap-2 rounded-xl border border-slate-800/60 bg-slate-900/40 p-4 text-left transition hover:border-violet-500/30 hover:bg-violet-500/[0.04]"
            >
              <p className="text-sm font-semibold text-slate-200 group-hover:text-violet-200">{t.name}</p>
              <p className="text-xs leading-relaxed text-slate-500 line-clamp-2">{t.description}</p>
              <div className="flex flex-wrap gap-1 pt-0.5">
                {t.companies.slice(0, 4).map(c => (
                  <span key={c} className="rounded bg-slate-800/70 px-1.5 py-0.5 text-[10px] text-slate-500">{c}</span>
                ))}
                {t.companies.length > 4 && (
                  <span className="rounded bg-slate-800/40 px-1.5 py-0.5 text-[10px] text-slate-600">+{t.companies.length - 4}</span>
                )}
              </div>
            </button>
          ))}
        </div>

        <div className="mt-4 border-t border-slate-800/50 pt-4">
          <button
            onClick={onCustom}
            className="w-full rounded-xl border border-dashed border-slate-800 bg-slate-900/20 px-4 py-3 text-left text-sm font-medium text-slate-500 transition hover:border-slate-700 hover:text-slate-300"
          >
            Start from scratch — define your own niche
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Step: Confirm template ─────────────────────────────────────────────────────

function ConfirmStep({
  template,
  onConfirm,
  onBack,
}: {
  template: TemplateCard;
  onConfirm: () => void;
  onBack: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setCreating(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create niche');
      setCreating(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-1 space-y-4">
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Niche</p>
          <p className="text-sm font-semibold text-slate-200">{template.name}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{template.description}</p>
        </div>

        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
            {template.companies.length} companies pre-configured
          </p>
          <div className="flex flex-wrap gap-1.5">
            {template.companies.map(c => (
              <span key={c} className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-400">{c}</span>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Source channels</p>
          <div className="flex flex-wrap gap-1.5">
            {template.sourceFamilies.map(f => (
              <span key={f} className="rounded-md border border-slate-800/50 bg-slate-800/40 px-2 py-0.5 text-[11px] capitalize text-slate-500">
                {f.replace(/_/g, ' ')}
              </span>
            ))}
            <span className="rounded-md border border-slate-800/50 bg-slate-800/40 px-2 py-0.5 text-[11px] text-slate-500">
              Reddit per company
            </span>
            <span className="rounded-md border border-slate-800/50 bg-slate-800/40 px-2 py-0.5 text-[11px] text-slate-500">
              Hacker News per company
            </span>
          </div>
        </div>

        <p className="text-[11px] leading-relaxed text-slate-600">
          Companies and sources are copied at creation time. You can add, remove, or edit them after.
        </p>

        {error && <p className="text-xs text-rose-400">{error}</p>}
      </div>

      <div className="flex items-center gap-2 border-t border-white/[0.06] px-5 py-4">
        <button
          onClick={handleConfirm}
          disabled={creating}
          className="flex-1 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {creating ? 'Creating…' : 'Create niche'}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={creating}
          className="rounded-lg border border-slate-700/60 bg-slate-800/60 px-4 py-2 text-sm font-medium text-slate-400 transition hover:text-slate-200 disabled:opacity-40"
        >
          Back
        </button>
      </div>
    </div>
  );
}

// ── Step: Custom niche form ────────────────────────────────────────────────────

function CustomStep({
  onCreated,
  onBack,
}: {
  onCreated: (market: Market) => void;
  onBack: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetUser, setTargetUser] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => nameRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
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
      setError(err instanceof Error ? err.message : 'Failed to create niche');
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-5 pb-5 pt-1">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="custom-niche-name" className={labelCls}>Name *</label>
          <input
            ref={nameRef}
            id="custom-niche-name"
            required
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Developer tools"
            className={inputCls}
            autoComplete="off"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="custom-niche-description" className={labelCls}>Description</label>
          <input
            id="custom-niche-description"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Problem space or niche focus"
            className={inputCls}
            autoComplete="off"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="custom-niche-target" className={labelCls}>Target user</label>
          <input
            id="custom-niche-target"
            value={targetUser}
            onChange={e => setTargetUser(e.target.value)}
            placeholder="e.g. Seed-stage founders"
            className={inputCls}
            autoComplete="off"
          />
        </div>

        <p className="text-[11px] leading-relaxed text-slate-600">
          You&apos;ll add companies and sources after creating the niche.
        </p>

        {error && <p className="shrink-0 text-xs text-rose-400">{error}</p>}
      </div>

      <div className="flex items-center gap-2 border-t border-white/[0.06] px-5 py-4">
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="flex-1 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving ? 'Creating…' : 'Create niche'}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={saving}
          className="rounded-lg border border-slate-700/60 bg-slate-800/60 px-4 py-2 text-sm font-medium text-slate-400 transition hover:text-slate-200 disabled:opacity-40"
        >
          Back
        </button>
      </div>
    </form>
  );
}

// ── Main drawer ────────────────────────────────────────────────────────────────

type Step = 'pick' | 'confirm' | 'custom';

const STEP_TITLES: Record<Step, string> = {
  pick: 'Add niche',
  confirm: 'Confirm niche',
  custom: 'Custom niche',
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (market: Market) => void;
};

export function AddNicheFlow({ isOpen, onClose, onCreated }: Props) {
  const [step, setStep] = useState<Step>('pick');
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateCard | null>(null);
  const [templates, setTemplates] = useState<TemplateCard[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setStep('pick');
      setSelectedTemplate(null);
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
    }
  }, [isOpen]);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    if (isOpen) panel.removeAttribute('inert');
    else panel.setAttribute('inert', '');
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  const handleSelectTemplate = (template: TemplateCard) => {
    setSelectedTemplate(template);
    setStep('confirm');
  };

  const handleConfirm = async () => {
    if (!selectedTemplate) return;
    const market = await signalApi.applyTemplate(selectedTemplate.id);
    onCreated(market);
  };

  const canGoBack = step !== 'pick';

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`fixed inset-0 z-[35] bg-black/30 transition-opacity duration-200 ${isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Add niche"
        className={`fixed left-0 top-0 z-40 flex h-screen w-full flex-col border-r border-white/[0.06] bg-[#07091a] shadow-[6px_0_40px_rgba(0,0,0,0.7)] transition-transform duration-200 ease-in-out sm:w-[480px] ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <div className="flex items-center gap-2">
            {canGoBack && (
              <button
                type="button"
                onClick={() => setStep('pick')}
                className="rounded p-1 text-slate-600 transition hover:bg-white/[0.04] hover:text-slate-400"
                aria-label="Back"
              >
                <IconChevronLeft />
              </button>
            )}
            <h2 className="text-sm font-semibold text-slate-200">{STEP_TITLES[step]}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-slate-600 transition hover:bg-white/[0.04] hover:text-slate-400"
          >
            <IconX />
          </button>
        </div>

        {step === 'pick' && (
          <TemplatePickerStep
            loading={templatesLoading}
            templates={templates}
            onSelect={handleSelectTemplate}
            onCustom={() => setStep('custom')}
          />
        )}

        {step === 'confirm' && selectedTemplate && (
          <ConfirmStep
            template={selectedTemplate}
            onConfirm={handleConfirm}
            onBack={() => setStep('pick')}
          />
        )}

        {step === 'custom' && (
          <CustomStep
            onCreated={onCreated}
            onBack={() => setStep('pick')}
          />
        )}
      </div>
    </>
  );
}
