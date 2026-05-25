'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { signalApi } from '@/lib/api';
import { Market } from '@/lib/types/signals';

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (market: Market) => void;
};

function toSlug(name: string) {
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
}

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

const inputCls =
  'w-full rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/10';

const labelCls = 'text-[10px] font-semibold uppercase tracking-wider text-slate-600';

export function AddNicheDrawer({ isOpen, onClose, onCreated }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetUser, setTargetUser] = useState('');
  const [ideaPrompt, setIdeaPrompt] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setName('');
    setDescription('');
    setTargetUser('');
    setIdeaPrompt('');
    setError(null);
    setSaving(false);
    const t = setTimeout(() => nameRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [isOpen]);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    if (isOpen) {
      panel.removeAttribute('inert');
    } else {
      panel.setAttribute('inert', '');
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

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
        idea_prompt: ideaPrompt.trim() || null,
      });
      onCreated(market);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create niche');
      setSaving(false);
    }
  };

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
        className={`fixed left-0 top-0 z-40 flex h-screen w-full flex-col border-r border-white/[0.06] bg-[#07091a] shadow-[6px_0_40px_rgba(0,0,0,0.7)] transition-transform duration-200 ease-in-out sm:w-80 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-200">New niche</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-slate-600 transition hover:bg-white/[0.04] hover:text-slate-400"
          >
            <IconX />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-1 flex-col gap-4 px-5 py-5">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="niche-name" className={labelCls}>Name *</label>
              <input
                ref={nameRef}
                id="niche-name"
                required
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Developer tools"
                className={inputCls}
                autoComplete="off"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="niche-description" className={labelCls}>Description</label>
              <input
                id="niche-description"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Problem space or niche focus"
                className={inputCls}
                autoComplete="off"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="niche-target" className={labelCls}>Target user</label>
              <input
                id="niche-target"
                value={targetUser}
                onChange={e => setTargetUser(e.target.value)}
                placeholder="e.g. Seed-stage founders"
                className={inputCls}
                autoComplete="off"
              />
            </div>

            <div className="flex min-h-0 flex-1 flex-col gap-1.5">
              <label htmlFor="niche-prompt" className={labelCls}>Research prompt</label>
              <textarea
                id="niche-prompt"
                value={ideaPrompt}
                onChange={e => setIdeaPrompt(e.target.value)}
                placeholder="Optional context for AI-guided research…"
                className={`${inputCls} min-h-0 flex-1 resize-none`}
              />
            </div>

            {error && <p className="shrink-0 text-xs text-rose-400">{error}</p>}
          </div>

          <div className="flex items-center gap-2 border-t border-white/[0.06] px-5 py-4">
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="flex-1 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving ? 'Creating…' : 'Create'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700/60 bg-slate-800/60 px-4 py-2 text-sm font-medium text-slate-400 transition hover:text-slate-200"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
