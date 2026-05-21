'use client';

import DashboardShell from '@/components/DashboardShell';
import { SectionCard } from '@/components/DashboardPrimitives';
import { SourceLocator } from '@/lib/types/signals';

// Placeholder — no sources loaded since the management API endpoint is not yet
// wired up. The page structure and empty state are ready for when it lands.
const SOURCES: SourceLocator[] = [];

function IconInfo() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

function IconActivity() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function IconClock() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

export default function SourcesPage() {
  return (
    <DashboardShell
      title="Monitored Sources"
      subtitle="URLs and feeds scanned automatically for market signals"
    >
      {/* How it works callout */}
      <div className="mb-5 flex gap-3 rounded-xl border border-violet-500/15 bg-violet-500/[0.05] px-4 py-3.5">
        <span className="mt-0.5 shrink-0 text-violet-400">
          <IconInfo />
        </span>
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-300">Automated monitoring</p>
          <p className="text-xs leading-relaxed text-slate-500">
            LidScout scans enabled source locators on a daily schedule, extracts pain signals using
            AI, clusters them by theme, and emails a market intelligence report. Sources are
            configured in the backend — add or disable them via the database or the admin API.
          </p>
        </div>
      </div>

      {/* Schedule info row */}
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <InfoCard
          label="Scan schedule"
          value="Daily · 08:00 UTC"
          icon={<IconClock />}
          iconColor="text-slate-500"
        />
        <InfoCard
          label="Active sources"
          value={String(SOURCES.filter(s => s.enabled).length)}
          icon={<IconActivity />}
          iconColor="text-emerald-400"
        />
        <InfoCard
          label="Total sources"
          value={String(SOURCES.length)}
          icon={<IconActivity />}
          iconColor="text-slate-500"
        />
      </div>

      {/* Source list */}
      <SectionCard>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Source locators</h2>
          <span className="rounded-md border border-slate-700/60 bg-slate-800/60 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
            Management API pending
          </span>
        </div>

        {SOURCES.length === 0 ? (
          <SourcesEmptyState />
        ) : (
          <SourceTable sources={SOURCES} />
        )}
      </SectionCard>

      {/* Schema reference */}
      <details className="mt-4 group">
        <summary className="cursor-pointer text-xs text-slate-700 hover:text-slate-500 transition-colors select-none">
          Source schema reference
        </summary>
        <div className="mt-2 overflow-x-auto rounded-lg border border-slate-800/60 bg-slate-900/60 p-4 font-mono text-xs leading-relaxed text-slate-500">
          <pre>{`source_locators (
  id          text  primary key,
  locator     text  not null unique,   -- URL or feed identifier
  enabled     bool  not null default true,
  limit_value int,                     -- max posts per scan
  options     jsonb not null default '{}',
  inserted_at timestamptz,
  updated_at  timestamptz
)`}</pre>
        </div>
      </details>
    </DashboardShell>
  );
}

function InfoCard({
  label,
  value,
  icon,
  iconColor,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  iconColor: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 px-5 py-4">
      <div className="flex items-center gap-1.5">
        <span className={iconColor}>{icon}</span>
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      </div>
      <p className="mt-2 text-xl font-bold tabular-nums tracking-tight text-slate-100">{value}</p>
    </div>
  );
}

function SourcesEmptyState() {
  return (
    <div>
      {/* Column headers */}
      <div className="mb-2 grid grid-cols-[1fr_80px_60px_100px] gap-4 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
        <span>Locator</span>
        <span>Status</span>
        <span>Limit</span>
        <span>Added</span>
      </div>

      {/* Empty state body */}
      <div className="rounded-xl border border-dashed border-slate-800 px-6 py-12 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-slate-800/70">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-600">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-slate-400">No source locators configured</p>
        <p className="mx-auto mt-1.5 max-w-sm text-xs leading-relaxed text-slate-600">
          Add sources via the database or backend API. Enabled sources will appear here and be
          scanned automatically on the daily schedule.
        </p>
        <div className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 font-mono text-xs text-slate-600">
          <span className="text-slate-700">INSERT INTO</span>
          <span className="text-violet-500/70">source_locators</span>
          <span className="text-slate-700">(locator) VALUES</span>
          <span className="text-amber-500/60">('...')</span>
        </div>
      </div>
    </div>
  );
}

function SourceTable({ sources }: { sources: SourceLocator[] }) {
  return (
    <div>
      <div className="mb-2 grid grid-cols-[1fr_80px_60px_100px] gap-4 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
        <span>Locator</span>
        <span>Status</span>
        <span>Limit</span>
        <span>Added</span>
      </div>
      <div className="space-y-1.5">
        {sources.map(source => (
          <div
            key={source.id}
            className="grid grid-cols-[1fr_80px_60px_100px] items-center gap-4 rounded-lg border border-slate-800/60 bg-slate-800/20 px-3 py-3 transition-colors hover:border-slate-700/80"
          >
            <span className="truncate font-mono text-xs text-slate-400">{source.locator}</span>
            <span>
              {source.enabled ? (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.7)]" />
                  Active
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-xs font-medium text-slate-600">
                  <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />
                  Paused
                </span>
              )}
            </span>
            <span className="tabular-nums text-xs text-slate-500">
              {source.limit_value ?? '—'}
            </span>
            <span className="tabular-nums text-xs text-slate-600">
              {formatDate(source.inserted_at)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}
