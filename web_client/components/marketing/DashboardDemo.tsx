'use client';

import { useState } from 'react';

type DemoTab = 'gaps' | 'themes' | 'findings';

const GAPS = [
  {
    id: '1',
    title: 'Calendar reliability blocks team adoption',
    pain_summary:
      'Teams hitting timezone sync bugs after switching from Google Calendar — often reverting within weeks.',
    evidence_count: 14,
    suggested_wedge:
      'A lightweight timezone-aware sync layer that treats the workspace as source of truth while resolving conflicts server-side.',
    strength: 'strong',
    saved: false,
  },
  {
    id: '2',
    title: 'No offline mode for field and travel users',
    pain_summary:
      'Users lose access to critical docs during commutes and flights — blocking adoption for distributed teams.',
    evidence_count: 9,
    suggested_wedge:
      'Progressive Web App shell with a local-first sync queue that replays edits on reconnect.',
    strength: 'moderate',
    saved: false,
  },
  {
    id: '3',
    title: 'API rate limits break power automation workflows',
    pain_summary:
      'Zapier and Make users hitting limits on high-volume workspaces, forcing manual workarounds mid-workflow.',
    evidence_count: 11,
    suggested_wedge:
      'Tiered API plans with burst allowances and webhook-first patterns to reduce polling pressure.',
    strength: 'strong',
    saved: true,
  },
];

const THEMES = [
  {
    id: 't1',
    theme: 'Calendar reliability',
    summary:
      'Recurring timezone sync failures causing team-wide reverts to Google Calendar.',
    frequency: 14,
    score: 8.2,
    companies: ['Notion', 'Linear', 'Cron'],
  },
  {
    id: 't2',
    theme: 'Offline & low-connectivity access',
    summary:
      'No graceful degradation when users go offline — blocks field teams and remote workers.',
    frequency: 9,
    score: 7.8,
    companies: ['Notion', 'Coda'],
  },
  {
    id: 't3',
    theme: 'API rate limits and automation',
    summary: 'Power users hitting limits that break high-volume Zapier/Make workflows.',
    frequency: 11,
    score: 7.5,
    companies: ['Notion', 'Asana', 'Linear', 'ClickUp'],
  },
  {
    id: 't4',
    theme: 'PDF export fidelity',
    summary: 'Complex pages lose formatting and table layout on PDF export.',
    frequency: 7,
    score: 6.9,
    companies: ['Notion', 'Coda'],
  },
];

const FINDINGS = [
  {
    id: 'f1',
    pain: 'Timezone sync breaks team calendar after update',
    urgency: 'high',
    score: 0.91,
    company: 'Notion',
    category: 'Calendar reliability',
    quote:
      '"We tried to move our whole team to Notion Calendar but the timezone sync issues made it unusable after two weeks. Back to Google Calendar."',
    source: 'r/Notion',
  },
  {
    id: 'f2',
    pain: 'No offline access for documents during travel',
    urgency: 'high',
    score: 0.87,
    company: 'Notion',
    category: 'Offline access',
    quote:
      '"Notion is unusable on flights. I\'ve started keeping local copies of everything critical because I can\'t rely on it being there when I\'m offline."',
    source: 'HN',
  },
  {
    id: 'f3',
    pain: 'Zapier integration fails at scale due to API limits',
    urgency: 'medium',
    score: 0.83,
    company: 'Notion',
    category: 'API & automation',
    quote:
      '"Hit the API rate limit again. Third time this week. We have a Zap that syncs 800+ records daily and it keeps failing halfway through."',
    source: 'G2',
  },
];

const TABS: Array<{ id: DemoTab; label: string }> = [
  { id: 'gaps', label: 'Gaps' },
  { id: 'themes', label: 'Themes' },
  { id: 'findings', label: 'Findings' },
];

function UrgencyDot({ urgency }: { urgency: string }) {
  const color =
    urgency === 'high'
      ? 'bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.7)]'
      : urgency === 'medium'
      ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.7)]'
      : 'bg-slate-500';
  return <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${color}`} />;
}

function ScoreChip({ value }: { value: number }) {
  const color =
    value >= 0.85
      ? 'bg-emerald-500/10 text-emerald-400'
      : value >= 0.7
      ? 'bg-violet-500/10 text-violet-400'
      : 'bg-slate-800 text-slate-500';
  return (
    <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold tabular-nums ${color}`}>
      {value.toFixed(2)}
    </span>
  );
}

function GapsView() {
  const [saved, setSaved] = useState<Set<string>>(new Set(['3']));
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const visible = GAPS.filter(g => !dismissed.has(g.id));

  return (
    <div className="space-y-3">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Gaps identified', value: GAPS.length },
          { label: 'Strong signals', value: GAPS.filter(g => g.strength === 'strong').length },
          { label: 'Evidence items', value: 34 },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg border border-slate-800/70 bg-slate-900/40 px-3 py-2.5"
          >
            <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
              {label}
            </p>
            <p className="text-lg font-black tabular-nums text-slate-100">{value}</p>
          </div>
        ))}
      </div>

      {/* Filter row */}
      <div className="flex gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1 w-fit">
        {(['All', 'Saved', 'Dismissed'] as const).map((f, i) => (
          <button
            key={f}
            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
              i === 0 ? 'bg-slate-700 text-slate-100 shadow-sm' : 'text-slate-500'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Gap cards */}
      <div className="space-y-2">
        {visible.map(gap => (
          <div
            key={gap.id}
            className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold leading-snug text-slate-100">
                  {gap.title}
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">{gap.pain_summary}</p>
              </div>
              <span
                className={`shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${
                  gap.strength === 'strong'
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-amber-500/10 text-amber-400'
                }`}
              >
                {gap.evidence_count} evidence
              </span>
            </div>

            {gap.suggested_wedge && (
              <p className="mt-2.5 rounded-lg border border-violet-500/15 bg-violet-500/[0.04] px-2.5 py-1.5 text-[11px] leading-relaxed text-violet-300">
                {gap.suggested_wedge}
              </p>
            )}

            <div className="mt-3 flex items-center gap-2">
              <button
                onClick={() =>
                  setSaved(prev => {
                    const next = new Set(prev);
                    next.has(gap.id) ? next.delete(gap.id) : next.add(gap.id);
                    return next;
                  })
                }
                className={`rounded-md border px-2.5 py-1 text-[11px] font-semibold transition ${
                  saved.has(gap.id)
                    ? 'border-violet-500/30 bg-violet-500/10 text-violet-300'
                    : 'border-slate-700/70 text-slate-500 hover:border-slate-600 hover:text-slate-300'
                }`}
              >
                {saved.has(gap.id) ? '✓ Saved' : 'Save'}
              </button>
              <button
                onClick={() =>
                  setDismissed(prev => new Set([...prev, gap.id]))
                }
                className="rounded-md border border-slate-700/70 px-2.5 py-1 text-[11px] font-semibold text-slate-600 transition hover:border-slate-600 hover:text-slate-400"
              >
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ThemesView() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Themes', value: THEMES.length },
          { label: 'Findings grouped', value: 41 },
          { label: 'Multi-company', value: 3 },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg border border-slate-800/70 bg-slate-900/40 px-3 py-2.5"
          >
            <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
              {label}
            </p>
            <p className="text-lg font-black tabular-nums text-slate-100">{value}</p>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        {THEMES.map(theme => (
          <div
            key={theme.id}
            className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4 transition hover:border-slate-700/80 hover:bg-slate-900/60 cursor-pointer"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-100">{theme.theme}</h3>
                <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{theme.summary}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span className="rounded-md bg-slate-800/70 px-1.5 py-0.5 text-[11px] text-slate-500">
                  {theme.frequency} findings
                </span>
                <span className="rounded px-1.5 py-0.5 text-[11px] font-semibold tabular-nums bg-violet-500/10 text-violet-400">
                  {theme.score}
                </span>
              </div>
            </div>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {theme.companies.map(c => (
                <span
                  key={c}
                  className="rounded bg-slate-800/50 px-1.5 py-0.5 text-[11px] text-slate-500"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FindingsView() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Findings', value: FINDINGS.length },
          { label: 'High urgency', value: FINDINGS.filter(f => f.urgency === 'high').length },
          { label: 'Themes linked', value: THEMES.length },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg border border-slate-800/70 bg-slate-900/40 px-3 py-2.5"
          >
            <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
              {label}
            </p>
            <p className="text-lg font-black tabular-nums text-slate-100">{value}</p>
          </div>
        ))}
      </div>

      {/* Filter + search */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-1 rounded-lg border border-slate-800/80 bg-slate-900/60 p-1">
          {['All', 'High', 'Medium', 'Low'].map((f, i) => (
            <button
              key={f}
              className={`rounded-md px-2 py-1 text-[11px] font-medium capitalize transition ${
                i === 0 ? 'bg-slate-700 text-slate-100 shadow-sm' : 'text-slate-500'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600"
            width="11"
            height="11"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            readOnly
            placeholder="Search findings…"
            className="w-36 rounded-lg border border-slate-700/70 bg-slate-900/60 py-1.5 pl-7 pr-2.5 text-[11px] text-slate-300 outline-none placeholder:text-slate-600"
          />
        </div>
      </div>

      <div className="space-y-2">
        {FINDINGS.map(finding => (
          <article
            key={finding.id}
            className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold leading-snug text-slate-100">
                  {finding.pain}
                </h3>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span
                  className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${
                    finding.urgency === 'high'
                      ? 'bg-rose-500/10 text-rose-400'
                      : finding.urgency === 'medium'
                      ? 'bg-amber-500/10 text-amber-400'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  <UrgencyDot urgency={finding.urgency} />
                  {finding.urgency}
                </span>
                <ScoreChip value={finding.score} />
              </div>
            </div>

            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className="rounded-md bg-slate-800/50 px-1.5 py-0.5 text-[11px] text-violet-400">
                {finding.category}
              </span>
              <span className="rounded-md bg-slate-800/50 px-1.5 py-0.5 text-[11px] text-slate-500">
                {finding.company}
              </span>
            </div>

            <p className="mt-2.5 rounded-lg bg-slate-950/35 px-2.5 py-2 text-[11px] italic leading-relaxed text-slate-500">
              {finding.quote}
            </p>
            <p className="mt-1.5 text-[11px] text-slate-700">via {finding.source}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export default function DashboardDemo() {
  const [activeTab, setActiveTab] = useState<DemoTab>('gaps');

  return (
    <section className="border-t border-slate-800/40 py-20">
      <div className="mx-auto max-w-5xl px-6">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
          Live demo
        </p>
        <h2 className="mb-3 text-2xl font-bold text-slate-100">
          The actual dashboard — with real data from a live run
        </h2>
        <p className="mb-8 max-w-xl text-sm leading-relaxed text-slate-500">
          This is the same interface you get after setting up a niche. Gap cards are interactive — try saving or dismissing one.
        </p>

        {/* Browser chrome */}
        <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-[#07091a] shadow-2xl shadow-black/60">
          {/* Browser top bar */}
          <div className="flex items-center gap-3 border-b border-slate-800/70 bg-slate-900/60 px-4 py-2.5">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
              <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
              <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
            </div>
            <div className="flex-1 rounded-md bg-slate-800/60 px-3 py-1 text-center text-[11px] text-slate-600 truncate">
              <span className="hidden sm:inline">lidscout.vercel.app/markets/notion-tools/gaps</span>
              <span className="sm:hidden">lidscout.vercel.app</span>
            </div>
          </div>

          {/* App layout */}
          <div className="flex min-h-0 h-[520px] sm:h-[560px]">
            {/* Sidebar — hidden on mobile */}
            <div className="hidden sm:block w-44 shrink-0 border-r border-slate-800/70 bg-slate-900/30 p-3">
              <div className="mb-4 flex items-center gap-2 px-1">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-600 text-white">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="4" />
                    <line x1="4.93" y1="4.93" x2="9.17" y2="9.17" /><line x1="14.83" y1="14.83" x2="19.07" y2="19.07" />
                    <line x1="14.83" y1="9.17" x2="19.07" y2="4.93" /><line x1="4.93" y1="19.07" x2="9.17" y2="14.83" />
                  </svg>
                </div>
                <div>
                  <p className="text-[11px] font-bold text-slate-200">LidScout</p>
                  <p className="text-[9px] text-slate-600">Niche intelligence</p>
                </div>
              </div>

              <div className="mb-1.5 flex items-center justify-between px-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-700">
                  Niches
                </span>
                <span className="text-slate-600">+</span>
              </div>

              {['Notion tools', 'Dev tools'].map((market, i) => (
                <div
                  key={market}
                  className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] font-medium ${
                    i === 0
                      ? 'bg-violet-500/10 text-violet-300'
                      : 'text-slate-600 hover:text-slate-400'
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                      i === 0 ? 'bg-violet-400' : 'bg-slate-700'
                    }`}
                  />
                  {market}
                </div>
              ))}
            </div>

            {/* Main content */}
            <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
              {/* Page header */}
              <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-800/50 px-4 py-3">
                <div className="min-w-0">
                  <h1 className="text-sm font-semibold text-slate-100">
                    {activeTab === 'gaps' ? 'Gaps' : activeTab === 'themes' ? 'Themes' : 'Findings'}
                  </h1>
                  <p className="hidden sm:block truncate text-[11px] text-slate-500 max-w-[220px]">
                    {activeTab === 'gaps'
                      ? 'Notion tools · ranked gaps'
                      : activeTab === 'themes'
                      ? 'Notion tools · pain patterns'
                      : 'Notion tools · raw evidence'}
                  </p>
                </div>

                {/* Tab switcher */}
                <div className="shrink-0">
                  <div className="flex gap-0.5 rounded-full border border-slate-800/80 bg-slate-900/50 p-1">
                    {TABS.map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${
                          activeTab === tab.id
                            ? 'bg-violet-500/15 text-violet-300'
                            : 'text-slate-500 hover:text-slate-300'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Scrollable content */}
              <div className="flex-1 overflow-y-auto p-5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {activeTab === 'gaps' && <GapsView />}
                {activeTab === 'themes' && <ThemesView />}
                {activeTab === 'findings' && <FindingsView />}
              </div>
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-[11px] text-slate-700">
          Sample data from a Notion tooling market · Click the tabs and gap actions above
        </p>
      </div>
    </section>
  );
}
