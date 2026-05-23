import { IconExternalLink } from './icons';
import type { SampleGap } from './sampleGaps';

const strengthCfg = {
  strong: {
    dot: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]',
    label: 'Strong signal',
    badge: 'border-emerald-500/20 bg-emerald-500/[0.07] text-emerald-400',
  },
  moderate: {
    dot: 'bg-amber-400',
    label: 'Moderate signal',
    badge: 'border-amber-500/20 bg-amber-500/[0.07] text-amber-400',
  },
};

export default function GapCard({ gap, dimmed = false }: { gap: SampleGap; dimmed?: boolean }) {
  const cfg = strengthCfg[gap.strength];

  return (
    <div
      className={`rounded-xl border bg-slate-900/50 p-5 transition-colors ${
        dimmed
          ? 'border-slate-800/40 opacity-60'
          : 'border-slate-800/70 hover:border-slate-700/80'
      }`}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium ${cfg.badge}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
          {cfg.label}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="rounded-md bg-violet-500/10 px-2 py-0.5 text-[11px] text-violet-300">
            {gap.market}
          </span>
          <span className="rounded-md bg-slate-800/60 px-2 py-0.5 text-[11px] text-slate-500">
            {gap.company}
          </span>
          <span className="text-[11px] tabular-nums text-slate-700">
            {gap.mentions} mentions
          </span>
        </div>
      </div>

      {/* Title */}
      <h3 className="mb-2 text-sm font-semibold leading-snug text-slate-100">
        {gap.title}
      </h3>

      {/* Pain summary */}
      <p className="mb-3 text-xs leading-relaxed text-slate-500">{gap.painSummary}</p>

      {/* Evidence quote */}
      <blockquote className="mb-3 rounded-lg border border-slate-800/50 bg-slate-800/30 px-3 py-2 text-xs italic leading-relaxed text-slate-500">
        &ldquo;{gap.evidenceQuote}&rdquo;
      </blockquote>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <p className="text-[11px] leading-relaxed text-slate-600 line-clamp-1">
          <span className="font-medium text-slate-500">Wedge: </span>
          {gap.suggestedWedge}
        </p>
        <a
          href={gap.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-3 flex shrink-0 items-center gap-1 text-[11px] text-slate-700 transition hover:text-slate-400"
        >
          {gap.sourceLabel}
          <IconExternalLink />
        </a>
      </div>
    </div>
  );
}
