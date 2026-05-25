'use client';

import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import DashboardShell from '@/components/app/DashboardShell';
import { NicheViewSwitcher } from '@/components/app/NicheViewSwitcher';
import { ClusterLink, EmptyPanel, ErrorPanel, LoadingPanel } from '@/components/ui/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import {
  AgentColdStartPlan,
  AgentFeedbackAction,
  AgentPreferences,
  AgentPreferencesUpdateRequest,
  Market,
  Opportunity,
  SignalCluster,
} from '@/lib/types/signals';

type Props = { params: { marketId: string } };
type Status = 'loading' | 'ready' | 'error';
type Tier = 'strong' | 'moderate' | 'weak';
type GapFilter = 'all' | 'saved' | 'dismissed';
type ItemFeedbackAction = Extract<AgentFeedbackAction, 'save' | 'dismiss'>;
type TrainingFeedbackAction = Extract<AgentFeedbackAction, 'more_like_this' | 'less_like_this'>;

const TIER_META: Record<Tier, { label: string; dotCls: string; badgeCls: string }> = {
  strong: { label: 'Strong signal', dotCls: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]', badgeCls: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400' },
  moderate: { label: 'Moderate signal', dotCls: 'bg-amber-400', badgeCls: 'border-amber-500/25 bg-amber-500/10 text-amber-400' },
  weak: { label: 'Weak signal', dotCls: 'bg-slate-600', badgeCls: 'border-slate-700/50 bg-slate-800/60 text-slate-500' },
};

function opportunityTier(confidence: number): Tier {
  if (confidence >= 0.7) return 'strong';
  if (confidence >= 0.4) return 'moderate';
  return 'weak';
}

function fallbackTitleFromId(id: string) {
  return id.split(/[-_]/).filter(Boolean).map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(' ');
}

function isItemFeedbackAction(action: AgentFeedbackAction): action is ItemFeedbackAction {
  return action === 'save' || action === 'dismiss';
}

function isTrainingFeedbackAction(action: AgentFeedbackAction): action is TrainingFeedbackAction {
  return action === 'more_like_this' || action === 'less_like_this';
}

// ── Icons ──────────────────────────────────────────────────────────────────────

function IconBookmark({ filled }: { filled?: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function IconThumbUp() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function IconThumbDown() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
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

function IconEdit() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function NicheWorkspacePage({ params }: Props) {
  const marketId = decodeURIComponent(params.marketId);
  const [niche, setNiche] = useState<Market | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [clusters, setClusters] = useState<SignalCluster[]>([]);
  const [coldStart, setColdStart] = useState<AgentColdStartPlan | null>(null);
  const [preferences, setPreferences] = useState<AgentPreferences | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [error, setError] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [gapFilter, setGapFilter] = useState<GapFilter>('all');
  const [itemFeedbackMap, setItemFeedbackMap] = useState<Map<string, ItemFeedbackAction>>(new Map());
  const [trainingFeedbackMap, setTrainingFeedbackMap] = useState<Map<string, TrainingFeedbackAction>>(new Map());

  const load = async () => {
    setStatus('loading');
    setError(null);
    setFeedbackError(null);
    setNiche(null);
    setColdStart(null);
    setPreferences(null);
    setItemFeedbackMap(new Map());
    setTrainingFeedbackMap(new Map());
    try {
      const [marketsRes, oppsRes, clustersRes, coldStartRes, feedbackRes, preferencesRes] = await Promise.all([
        signalApi.getMarkets(),
        signalApi.getOpportunities({ market_id: marketId }),
        signalApi.getClusters({ market_id: marketId }),
        signalApi.getMarketAgentColdStart(marketId).catch(() => null),
        signalApi.getMarketAgentFeedback(marketId).catch(() => null),
        signalApi.getMarketAgentPreferences(marketId).catch(() => null),
      ]);
      setNiche(marketsRes.markets.find(m => m.id === marketId) ?? null);
      setOpportunities(oppsRes.opportunities);
      setClusters(clustersRes.clusters);
      setColdStart(coldStartRes);
      setPreferences(preferencesRes);

      if (feedbackRes?.feedback) {
        // Take latest action per opportunity (sort asc by created_at, last wins)
        const sorted = [...feedbackRes.feedback].sort((a, b) =>
          (a.created_at ?? '').localeCompare(b.created_at ?? '')
        );
        const itemMap = new Map<string, ItemFeedbackAction>();
        const trainingMap = new Map<string, TrainingFeedbackAction>();
        for (const f of sorted) {
          if (isItemFeedbackAction(f.action)) itemMap.set(f.opportunity_id, f.action);
          if (isTrainingFeedbackAction(f.action)) trainingMap.set(f.opportunity_id, f.action);
        }
        setItemFeedbackMap(itemMap);
        setTrainingFeedbackMap(trainingMap);
      }

      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load niche');
      setStatus('error');
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketId]);

  const clusterById = useMemo(() => new Map(clusters.map(c => [c.id, c])), [clusters]);

  const savedIds = useMemo(
    () => new Set([...itemFeedbackMap].filter(([, v]) => v === 'save').map(([k]) => k)),
    [itemFeedbackMap]
  );
  const dismissedIds = useMemo(
    () => new Set([...itemFeedbackMap].filter(([, v]) => v === 'dismiss').map(([k]) => k)),
    [itemFeedbackMap]
  );

  const filteredOpportunities = opportunities.filter(o => {
    if (gapFilter === 'saved') return savedIds.has(o.id);
    if (gapFilter === 'dismissed') return dismissedIds.has(o.id);
    return !dismissedIds.has(o.id);
  });

  const strongCount = opportunities.filter(o => o.confidence >= 0.7).length;
  const evidenceCount = opportunities.reduce((sum, o) => sum + o.evidence_count, 0);
  const title = niche?.name ?? (status === 'loading' ? '' : fallbackTitleFromId(marketId));

  const handleItemFeedback = async (opportunityId: string, action: ItemFeedbackAction) => {
    const previousAction = itemFeedbackMap.get(opportunityId);
    setFeedbackError(null);
    setItemFeedbackMap(prev => {
      const next = new Map(prev);
      next.set(opportunityId, action);
      return next;
    });
    try {
      await signalApi.createOpportunityFeedback(opportunityId, { market_id: marketId, action });
    } catch (err) {
      setItemFeedbackMap(prev => {
        const next = new Map(prev);
        if (previousAction) next.set(opportunityId, previousAction);
        else next.delete(opportunityId);
        return next;
      });
      setFeedbackError(err instanceof Error ? err.message : 'Failed to record feedback');
    }
  };

  const handleTrainingFeedback = async (opportunityId: string, action: TrainingFeedbackAction) => {
    const previousAction = trainingFeedbackMap.get(opportunityId);
    setFeedbackError(null);
    setTrainingFeedbackMap(prev => {
      const next = new Map(prev);
      next.set(opportunityId, action);
      return next;
    });
    try {
      await signalApi.createOpportunityFeedback(opportunityId, { market_id: marketId, action });
    } catch (err) {
      setTrainingFeedbackMap(prev => {
        const next = new Map(prev);
        if (previousAction) next.set(opportunityId, previousAction);
        else next.delete(opportunityId);
        return next;
      });
      setFeedbackError(err instanceof Error ? err.message : 'Failed to record feedback');
    }
  };

  const needsSetup = coldStart?.status === 'setup_needed' && opportunities.length === 0;

  return (
    <DashboardShell
      title={title}
      subtitle={niche?.description ?? 'Ranked product gaps backed by public evidence.'}
      actions={<NicheViewSwitcher marketId={marketId} active="gaps" onRefresh={load} refreshing={status === 'loading'} />}
    >
      {status === 'loading' && <LoadingPanel label="Loading gaps" />}
      {status === 'error' && error && <ErrorPanel message={error} />}

      {status === 'ready' && (
        <div className="space-y-5 animate-fade-in">

          {coldStart && (
            <ResearchBriefPanel
              coldStart={coldStart}
              preferences={preferences}
              marketId={marketId}
              onPreferencesUpdated={setPreferences}
            />
          )}

          {needsSetup ? (
            <ColdStartPanel coldStart={coldStart!} marketId={marketId} />
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <Summary label="Gaps identified" value={opportunities.length} accent={opportunities.length > 0} />
                <Summary label="Strong signals" value={strongCount} accent={strongCount > 0} />
                <Summary label="Evidence items" value={evidenceCount} />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1">
                  {(['all', 'saved', 'dismissed'] as const).map(filter => (
                    <button
                      key={filter}
                      onClick={() => setGapFilter(filter)}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition ${gapFilter === filter ? 'bg-slate-700 text-slate-100 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
                {savedIds.size > 0 && gapFilter !== 'saved' && (
                  <span className="text-xs text-slate-600">{savedIds.size} saved</span>
                )}
              </div>
              {feedbackError && (
                <p className="text-xs text-rose-400">{feedbackError}</p>
              )}

              {filteredOpportunities.length === 0 ? (
                <EmptyPanel
                  title={gapFilter === 'all' ? 'No gaps identified yet' : `No ${gapFilter} gaps`}
                  detail={gapFilter === 'all' ? 'Gaps appear after active sources are scanned.' : undefined}
                />
              ) : (
                <div className="space-y-3">
                  {filteredOpportunities.map((opportunity, index) => (
                    <GapCard
                      key={opportunity.id}
                      rank={index + 1}
                      opportunity={opportunity}
                      marketId={marketId}
                      theme={opportunity.cluster_id ? clusterById.get(opportunity.cluster_id) : undefined}
                      meta={TIER_META[opportunityTier(opportunity.confidence)]}
                      itemAction={itemFeedbackMap.get(opportunity.id) ?? null}
                      trainingAction={trainingFeedbackMap.get(opportunity.id) ?? null}
                      onItemFeedback={action => handleItemFeedback(opportunity.id, action)}
                      onTrainingFeedback={action => handleTrainingFeedback(opportunity.id, action)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

// ── Research Brief Panel ───────────────────────────────────────────────────────

function ResearchBriefPanel({
  coldStart,
  preferences,
  marketId,
  onPreferencesUpdated,
}: {
  coldStart: AgentColdStartPlan;
  preferences: AgentPreferences | null;
  marketId: string;
  onPreferencesUpdated: (prefs: AgentPreferences) => void;
}) {
  const [open, setOpen] = useState(coldStart.status === 'setup_needed');
  const [editing, setEditing] = useState(false);

  return (
    <section className="rounded-xl border border-slate-800/60 bg-slate-900/30">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center justify-between px-5 py-3.5 text-left"
      >
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 rounded-full ${coldStart.status === 'setup_needed' ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]' : 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]'}`} />
          <span className="text-xs font-semibold text-slate-500">Research brief</span>
          {coldStart.status === 'setup_needed' && (
            <span className="rounded-md bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">Setup needed</span>
          )}
        </div>
        <span className="text-slate-700"><IconChevron open={open} /></span>
      </button>

      {open && (
        <div className="border-t border-slate-800/50 px-5 pb-5 pt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-3">
              {coldStart.brief.objective && (
                <BriefField label="Objective" value={coldStart.brief.objective} />
              )}
              {coldStart.brief.target_user && (
                <BriefField label="Target user" value={coldStart.brief.target_user} />
              )}
            </div>
            <div className="space-y-3">
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Sources</p>
                <p className="text-xs text-slate-400">
                  <span className="font-medium text-slate-300">{coldStart.monitored_source_count}</span> monitored
                  {coldStart.active_source_count > 0 && (
                    <> · <span className="font-medium text-slate-300">{coldStart.active_source_count}</span> active</>
                  )}
                  {coldStart.suggested_source_count > 0 && (
                    <> · <Link href={`/markets/${encodeURIComponent(marketId)}/sources`} className="text-violet-400 hover:underline">{coldStart.suggested_source_count} suggested</Link></>
                  )}
                </p>
              </div>
              {coldStart.brief.source_family_priorities.length > 0 && (
                <div>
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Source priorities</p>
                  <div className="flex flex-wrap gap-1.5">
                    {coldStart.brief.source_family_priorities.map(fam => (
                      <span key={fam} className="rounded-md bg-slate-800/70 px-2 py-0.5 text-[11px] text-slate-400">{fam}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {preferences && !editing && (
            <div className="mt-4 border-t border-slate-800/50 pt-4">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Agent preferences</p>
                <button
                  onClick={() => setEditing(true)}
                  className="flex items-center gap-1 rounded px-1.5 py-1 text-[11px] text-slate-600 transition hover:bg-white/[0.04] hover:text-slate-400"
                >
                  <IconEdit /> Edit
                </button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {preferences.preferred_source_families.length > 0 && (
                  <div>
                    <p className="mb-1.5 text-[10px] text-slate-700">Preferred sources</p>
                    <div className="flex flex-wrap gap-1">
                      {preferences.preferred_source_families.map(f => <PrefChip key={f} label={f} />)}
                    </div>
                  </div>
                )}
                {preferences.ignored_themes.length > 0 && (
                  <div>
                    <p className="mb-1.5 text-[10px] text-slate-700">Ignored themes</p>
                    <div className="flex flex-wrap gap-1">
                      {preferences.ignored_themes.map(t => <PrefChip key={t} label={t} muted />)}
                    </div>
                  </div>
                )}
                {preferences.ignored_categories.length > 0 && (
                  <div>
                    <p className="mb-1.5 text-[10px] text-slate-700">Ignored categories</p>
                    <div className="flex flex-wrap gap-1">
                      {preferences.ignored_categories.map(c => <PrefChip key={c} label={c} muted />)}
                    </div>
                  </div>
                )}
                {preferences.extra_instructions && (
                  <div className="sm:col-span-2">
                    <p className="mb-1 text-[10px] text-slate-700">Extra instructions</p>
                    <p className="text-xs leading-relaxed text-slate-500">{preferences.extra_instructions}</p>
                  </div>
                )}
                {preferences.preferred_source_families.length === 0 &&
                  preferences.ignored_themes.length === 0 &&
                  preferences.ignored_categories.length === 0 &&
                  !preferences.extra_instructions && (
                    <p className="text-xs text-slate-700 sm:col-span-2">No preferences set — agent uses defaults.</p>
                  )}
              </div>
            </div>
          )}

          {editing && preferences && (
            <PreferencesEditForm
              marketId={marketId}
              preferences={preferences}
              onSaved={prefs => { onPreferencesUpdated(prefs); setEditing(false); }}
              onCancel={() => setEditing(false)}
            />
          )}
        </div>
      )}
    </section>
  );
}

function BriefField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">{label}</p>
      <p className="text-xs leading-relaxed text-slate-400">{value}</p>
    </div>
  );
}

function PrefChip({ label, muted }: { label: string; muted?: boolean }) {
  return (
    <span className={`rounded-md px-2 py-0.5 text-[11px] ${muted ? 'bg-slate-800/50 text-slate-600' : 'bg-violet-500/10 text-violet-400'}`}>
      {label}
    </span>
  );
}

// ── Preferences edit form ──────────────────────────────────────────────────────

function PreferencesEditForm({
  marketId,
  preferences,
  onSaved,
  onCancel,
}: {
  marketId: string;
  preferences: AgentPreferences;
  onSaved: (prefs: AgentPreferences) => void;
  onCancel: () => void;
}) {
  const [preferredFamilies, setPreferredFamilies] = useState(preferences.preferred_source_families.join(', '));
  const [ignoredThemes, setIgnoredThemes] = useState(preferences.ignored_themes.join(', '));
  const [ignoredCategories, setIgnoredCategories] = useState(preferences.ignored_categories.join(', '));
  const [extraInstructions, setExtraInstructions] = useState(preferences.extra_instructions ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseList = (v: string) => v.split(',').map(s => s.trim()).filter(Boolean);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const request: AgentPreferencesUpdateRequest = {
        preferred_source_families: parseList(preferredFamilies),
        ignored_themes: parseList(ignoredThemes),
        ignored_categories: parseList(ignoredCategories),
        extra_instructions: extraInstructions.trim() || null,
      };
      const updated = await signalApi.updateMarketAgentPreferences(marketId, request);
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save preferences');
      setSaving(false);
    }
  };

  const fieldCls = 'w-full rounded-md border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-xs text-slate-300 outline-none placeholder:text-slate-700 transition focus:border-violet-500/60';
  const labelCls = 'mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-600';

  return (
    <div className="mt-4 border-t border-slate-800/50 pt-4">
      <p className={labelCls}>Edit preferences</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
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
      <div className="mt-3 flex gap-2">
        <button
          onClick={save}
          disabled={saving}
          className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          onClick={onCancel}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-200"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Cold-start setup panel ─────────────────────────────────────────────────────

const SETUP_ACTION_LABELS: Record<string, string> = {
  refine_research_brief: 'Refine the research brief',
  add_companies: 'Add companies to this niche',
  add_sources: 'Add monitored sources',
  review_suggested_sources: 'Review suggested sources',
  run_first_scan: 'Ready for first scan',
};

function setupActionLabel(action: string) {
  return SETUP_ACTION_LABELS[action] ?? fallbackTitleFromId(action);
}

function ColdStartPanel({ coldStart, marketId }: { coldStart: AgentColdStartPlan; marketId: string }) {
  return (
    <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-5">
      <div className="mb-2 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]" />
        <h2 className="text-sm font-semibold text-amber-300">Agent needs setup</h2>
      </div>
      <p className="mb-4 text-xs leading-relaxed text-slate-500">
        This niche doesn&apos;t have enough data to surface gaps yet. Complete the steps below to start the research agent.
      </p>
      {coldStart.next_actions.length > 0 && (
        <ul className="mb-4 space-y-1.5">
          {coldStart.next_actions.map((action, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-700" />
              {setupActionLabel(action)}
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        <Link
          href={`/markets/${encodeURIComponent(marketId)}/sources`}
          className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-semibold text-violet-300 transition hover:bg-violet-500/15"
        >
          Add sources
        </Link>
        <Link
          href={`/markets/${encodeURIComponent(marketId)}/sources`}
          className="rounded-lg border border-slate-700/60 px-3 py-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-200"
        >
          Add companies
        </Link>
      </div>
    </div>
  );
}

// ── Gap card ───────────────────────────────────────────────────────────────────

function GapCard({
  rank,
  opportunity,
  marketId,
  theme,
  meta,
  itemAction,
  trainingAction,
  onItemFeedback,
  onTrainingFeedback,
}: {
  rank: number;
  opportunity: Opportunity;
  marketId: string;
  theme?: SignalCluster;
  meta: typeof TIER_META['strong'];
  itemAction: ItemFeedbackAction | null;
  trainingAction: TrainingFeedbackAction | null;
  onItemFeedback: (action: ItemFeedbackAction) => void;
  onTrainingFeedback: (action: TrainingFeedbackAction) => void;
}) {
  const saved = itemAction === 'save';
  const dismissed = itemAction === 'dismiss';

  return (
    <div className={`rounded-xl border bg-slate-900/40 px-5 py-4 transition-colors hover:border-slate-700/80 ${dismissed ? 'border-slate-800/40 opacity-50' : 'border-slate-800/70'}`}>
      <div className="flex items-start gap-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-bold tabular-nums text-slate-500">
          {rank}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
            <h3 className="font-semibold leading-snug text-slate-100">{opportunity.title}</h3>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${meta.badgeCls}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${meta.dotCls}`} />
                {meta.label}
              </span>
              <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                {opportunity.evidence_count} evidence
              </span>
              {theme && <ClusterLink id={theme.id} marketId={marketId}>{theme.theme}</ClusterLink>}
            </div>
          </div>

          {opportunity.pain_summary && (
            <p className="mb-3 text-sm leading-relaxed text-slate-400">{opportunity.pain_summary}</p>
          )}

          <div className="grid gap-2 sm:grid-cols-2">
            {opportunity.target_user && (
              <div className="rounded-lg border border-slate-800/50 bg-slate-800/20 px-3 py-2">
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Affected user</p>
                <p className="text-xs text-slate-400">{opportunity.target_user}</p>
              </div>
            )}
            {opportunity.suggested_wedge && (
              <div className="rounded-lg border border-violet-500/15 bg-violet-500/[0.04] px-3 py-2">
                <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-700">Suggested wedge</p>
                <p className="text-xs text-violet-300">{opportunity.suggested_wedge}</p>
              </div>
            )}
          </div>

          {opportunity.company_count > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="text-xs text-slate-600">
                Across <span className="font-medium text-slate-400">{opportunity.company_count}</span>
                {opportunity.market_company_count != null && (
                  <> of <span className="font-medium text-slate-400">{opportunity.market_company_count}</span></>
                )}{' '}
                {opportunity.company_count === 1 ? 'company' : 'companies'}
              </span>
              {opportunity.company_names.slice(0, 4).map(name => (
                <span key={name} className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">{name}</span>
              ))}
            </div>
          )}

          {opportunity.why_it_matters && (
            <p className="mt-2.5 text-xs leading-relaxed text-slate-500">{opportunity.why_it_matters}</p>
          )}

          <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-800/50 pt-3">
            <div className="flex items-center gap-1.5">
              <FeedbackButton
                active={saved}
                onClick={() => onItemFeedback('save')}
                icon={<IconBookmark filled={saved} />}
                label={saved ? 'Saved' : 'Save'}
                activeClass="border-violet-500/30 bg-violet-500/10 text-violet-400"
              />
              <FeedbackButton
                active={dismissed}
                onClick={() => onItemFeedback('dismiss')}
                icon={<IconX />}
                label={dismissed ? 'Dismissed' : 'Dismiss'}
                activeClass="border-slate-600 text-slate-400"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <FeedbackButton
                active={trainingAction === 'more_like_this'}
                onClick={() => onTrainingFeedback('more_like_this')}
                icon={<IconThumbUp />}
                label="More"
                activeClass="border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                title="More like this"
              />
              <FeedbackButton
                active={trainingAction === 'less_like_this'}
                onClick={() => onTrainingFeedback('less_like_this')}
                icon={<IconThumbDown />}
                label="Less"
                activeClass="border-rose-500/30 bg-rose-500/10 text-rose-400"
                title="Less like this"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeedbackButton({
  active,
  onClick,
  icon,
  label,
  activeClass,
  title,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
  activeClass: string;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition ${active ? activeClass : 'border-slate-700/50 text-slate-600 hover:border-slate-600 hover:text-slate-400'}`}
    >
      {icon}
      {label}
    </button>
  );
}

// ── Summary stat card ──────────────────────────────────────────────────────────

function Summary({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`rounded-xl border px-5 py-4 ${accent ? 'border-violet-500/20 bg-violet-600/[0.08]' : 'border-slate-800/80 bg-slate-900/50'}`}>
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${accent ? 'text-violet-300' : 'text-slate-100'}`}>{value}</p>
    </div>
  );
}
