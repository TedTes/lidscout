'use client';

import { FormEvent, useState } from 'react';
import { signalApi } from '@/lib/api';
import { Market } from '@/lib/types/signals';

function toSlug(name: string) {
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
}

type Props = {
  onAdd: (market: Market) => void;
  onCancel: () => void;
};

export function AddMarketPanel({ onAdd, onCancel }: Props) {
  const [form, setForm] = useState({ name: '', description: '', target_user: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const market = await signalApi.createMarket({
        id: toSlug(form.name),
        name: form.name,
        description: form.description || null,
        target_user: form.target_user || null,
      });
      onAdd(market);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create niche');
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.04] p-5">
      <h3 className="mb-4 text-sm font-semibold text-slate-200">New niche</h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Name *</label>
          <input
            required
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Developer tools"
            className="rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60"
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Description</label>
            <input
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="What niche or problem space?"
              className="rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Target user</label>
            <input
              value={form.target_user}
              onChange={e => setForm(f => ({ ...f, target_user: e.target.value }))}
              placeholder="e.g. Seed-stage founders"
              className="rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60"
            />
          </div>
        </div>
        {error && <p className="text-xs text-rose-400">{error}</p>}
        <div className="flex items-center gap-2 pt-1">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
          >
            {saving ? 'Creating…' : 'Create niche'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-slate-700/60 bg-slate-800/60 px-4 py-2 text-sm font-medium text-slate-400 transition hover:text-slate-200"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
