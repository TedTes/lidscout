import Link from 'next/link';

// ── Empty state ──────────────────────────────────────────────────────────────

export function EmptyPanel({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-800 px-6 py-14 text-center">
      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-slate-800/70">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-slate-600"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
      </div>
      <p className="text-sm font-semibold text-slate-400">{title}</p>
      {detail && (
        <p className="mx-auto mt-1.5 max-w-sm text-xs leading-relaxed text-slate-600">{detail}</p>
      )}
    </div>
  );
}

// ── Error state ──────────────────────────────────────────────────────────────

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-500/20 bg-rose-500/[0.06] px-4 py-3">
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="mt-0.5 shrink-0 text-rose-400"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <p className="text-sm text-rose-300">{message}</p>
    </div>
  );
}

// ── Loading state ────────────────────────────────────────────────────────────

export function LoadingPanel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-violet-500/20 bg-violet-500/[0.05] px-4 py-3">
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-violet-900 border-t-violet-400" />
      <p className="text-sm text-slate-500">{label}&hellip;</p>
    </div>
  );
}

// ── Skeleton loader ──────────────────────────────────────────────────────────

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-800/60 px-5 py-4">
      <div className="h-3 w-3/5 animate-shimmer rounded-md" />
      <div className="ml-auto h-3 w-16 animate-shimmer rounded-md" />
    </div>
  );
}

// ── Metric card ──────────────────────────────────────────────────────────────

export function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-5 py-4 transition-colors ${
        accent
          ? 'border-violet-500/20 bg-violet-600/[0.08]'
          : 'border-slate-800/80 bg-slate-900/50'
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p
        className={`mt-2 text-2xl font-bold tabular-nums tracking-tight ${
          accent ? 'text-violet-300' : 'text-slate-100'
        }`}
      >
        {value}
      </p>
    </div>
  );
}

// ── Score badge ──────────────────────────────────────────────────────────────

export function ScoreBadge({ value }: { value: number }) {
  const cfg =
    value >= 8
      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
      : value >= 6
        ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
        : 'bg-slate-800/70 border-slate-700/50 text-slate-500';

  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-bold tabular-nums ${cfg}`}
    >
      {value.toFixed(1)}
    </span>
  );
}

// ── Urgency badge ────────────────────────────────────────────────────────────

export function UrgencyBadge({ urgency }: { urgency: 'low' | 'medium' | 'high' }) {
  const cfg = {
    high: {
      wrap: 'bg-rose-500/10 border-rose-500/20',
      dot: 'bg-rose-400 shadow-[0_0_6px_rgba(251,113,133,0.8)]',
      text: 'text-rose-400',
      label: 'High',
    },
    medium: {
      wrap: 'bg-amber-500/10 border-amber-500/20',
      dot: 'bg-amber-400',
      text: 'text-amber-400',
      label: 'Med',
    },
    low: {
      wrap: 'bg-slate-800/60 border-slate-700/50',
      dot: 'bg-slate-600',
      text: 'text-slate-500',
      label: 'Low',
    },
  }[urgency];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${cfg.wrap}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      <span className={cfg.text}>{cfg.label}</span>
    </span>
  );
}

// ── Category chip ─────────────────────────────────────────────────────────────

export function Chip({ label }: { label: string }) {
  return (
    <span className="rounded-md bg-slate-800/70 px-2 py-0.5 text-xs text-slate-400">
      {label}
    </span>
  );
}

// ── Cluster link ─────────────────────────────────────────────────────────────

export function ClusterLink({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <Link
      href={`/clusters/${encodeURIComponent(id)}`}
      className="inline-flex items-center gap-1 rounded-md bg-violet-600/10 px-2 py-0.5 text-xs font-medium text-violet-400 transition hover:bg-violet-600/20 hover:text-violet-300"
    >
      {children}
      <svg
        width="10"
        height="10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </Link>
  );
}

// ── Section card wrapper ─────────────────────────────────────────────────────

export function SectionCard({
  title,
  children,
  className,
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-slate-800/80 bg-slate-900/40 p-5 ${className ?? ''}`}
    >
      {title && (
        <h2 className="mb-4 text-sm font-semibold text-slate-300">{title}</h2>
      )}
      {children}
    </section>
  );
}

// ── Divider ──────────────────────────────────────────────────────────────────

export function Divider() {
  return <div className="h-px bg-slate-800/80" />;
}
