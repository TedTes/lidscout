import Link from 'next/link';
import GapCard from '@/components/marketing/GapCard';
import { sampleGaps } from '@/components/marketing/sampleGaps';
import { IconArrow } from '@/components/marketing/icons';

const notionGaps = sampleGaps.filter((g) => g.company === 'Notion');

export const metadata = {
  title: 'Notion Pain Report — LidScout',
  description:
    'The top product gaps in Notion, surfaced from Reddit, G2, and Hacker News. Updated weekly.',
};

export default function NotionReportPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2 text-xs text-slate-600">
        <Link href="/" className="hover:text-slate-400 transition">
          LidScout
        </Link>
        <span>/</span>
        <span>Reports</span>
        <span>/</span>
        <span className="text-slate-500">Notion</span>
      </div>

      <div className="mb-10">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/[0.06] px-3 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
            Live report
          </span>
        </div>
        <h1 className="mb-3 text-3xl font-extrabold tracking-tight text-slate-50">
          Notion — Pain Report
        </h1>
        <p className="mb-2 text-sm leading-relaxed text-slate-400">
          Top product gaps surfaced from Reddit, G2, Hacker News, and Capterra. Signals are
          collected daily, clustered by theme, and ranked by mention frequency and recency trend.
        </p>
        <p className="text-xs text-slate-700">Week of May 19, 2026 · 14 gaps tracked</p>
      </div>

      {/* Gap cards */}
      <div className="mb-12 grid gap-4 sm:grid-cols-2">
        {notionGaps.map((gap) => (
          <GapCard key={gap.id} gap={gap} />
        ))}
      </div>

      {/* Full report teaser */}
      <div className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-6 text-center">
        <p className="mb-2 text-sm font-semibold text-slate-200">
          This is a sample — the full report covers 14 gaps
        </p>
        <p className="mb-5 text-xs text-slate-500">
          Get a complete report for any product, delivered to your inbox every Friday.
        </p>
        <Link
          href="/sources"
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:bg-violet-500"
        >
          Get a free report
          <IconArrow />
        </Link>
      </div>
    </div>
  );
}
