'use client';

import { useEffect, useState } from 'react';
import { signalApi } from '@/lib/api';
import { AgentPreferences, AgentPreferencesUpdateRequest } from '@/lib/types/signals';

const fieldCls = 'w-full rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 outline-none placeholder:text-slate-700 transition focus:border-violet-500/60';
const labelCls = 'mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-600';

export function AgentSettingsPanel({ marketId }: { marketId: string }) {
  const [preferences, setPreferences] = useState<AgentPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [preferredFamilies, setPreferredFamilies] = useState('');
  const [ignoredThemes, setIgnoredThemes] = useState('');
  const [ignoredCategories, setIgnoredCategories] = useState('');
  const [extraInstructions, setExtraInstructions] = useState('');

  useEffect(() => {
    signalApi.getMarketAgentPreferences(marketId)
      .then(prefs => {
        setPreferences(prefs);
        setPreferredFamilies(prefs.preferred_source_families.join(', '));
        setIgnoredThemes(prefs.ignored_themes.join(', '));
        setIgnoredCategories(prefs.ignored_categories.join(', '));
        setExtraInstructions(prefs.extra_instructions ?? '');
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [marketId]);

  const parseList = (v: string) => v.split(',').map(s => s.trim()).filter(Boolean);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const request: AgentPreferencesUpdateRequest = {
        preferred_source_families: parseList(preferredFamilies),
        ignored_themes: parseList(ignoredThemes),
        ignored_categories: parseList(ignoredCategories),
        extra_instructions: extraInstructions.trim() || null,
      };
      const updated = await signalApi.updateMarketAgentPreferences(marketId, request);
      setPreferences(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/40 px-5 py-4">
        <p className="text-xs text-slate-600">Loading settings…</p>
      </div>
    );
  }

  if (!preferences) return null;

  return (
    <div className="rounded-xl border border-slate-800/70 bg-slate-900/40 px-5 py-4">
      <p className="mb-4 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
        Agent settings
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className={labelCls}>Preferred source families</label>
          <input
            value={preferredFamilies}
            onChange={e => setPreferredFamilies(e.target.value)}
            placeholder="reviews, social, technical_forum"
            className={fieldCls}
          />
          <p className="mt-0.5 text-[10px] text-slate-700">Comma-separated</p>
        </div>
        <div>
          <label className={labelCls}>Ignored themes</label>
          <input
            value={ignoredThemes}
            onChange={e => setIgnoredThemes(e.target.value)}
            placeholder="pricing, onboarding"
            className={fieldCls}
          />
          <p className="mt-0.5 text-[10px] text-slate-700">Comma-separated</p>
        </div>
        <div>
          <label className={labelCls}>Ignored categories</label>
          <input
            value={ignoredCategories}
            onChange={e => setIgnoredCategories(e.target.value)}
            placeholder="marketing, hiring"
            className={fieldCls}
          />
          <p className="mt-0.5 text-[10px] text-slate-700">Comma-separated</p>
        </div>
        <div>
          <label className={labelCls}>Extra instructions</label>
          <textarea
            value={extraInstructions}
            onChange={e => setExtraInstructions(e.target.value)}
            rows={2}
            placeholder="Focus on B2B SaaS tools…"
            className={`${fieldCls} resize-none`}
          />
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}

      <div className="mt-3 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save settings'}
        </button>
        {saved && <span className="text-xs text-emerald-400">Saved</span>}
      </div>
    </div>
  );
}
