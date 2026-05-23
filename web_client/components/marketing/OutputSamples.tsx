import { sampleGaps } from './sampleGaps';
import GapCardPulse from './animations/GapCardPulse';
import Link from 'next/link';

export default function OutputSamples() {
  return (
    <section className="py-20 border-t border-slate-800/40">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mb-10 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-xl">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
              Real output
            </p>
            <h2 className="text-2xl font-bold text-slate-100">
              What a market gap report looks like
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-500">
              Six gaps surfaced across the workspace tools market this week. Each one is
              clustered from real user posts and tied back to the company and source evidence.
            </p>
          </div>
          <Link
            href="/reports/notion-2026"
            className="shrink-0 rounded-lg border border-slate-700/80 bg-slate-800/50 px-4 py-2 text-xs font-semibold text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100"
          >
            Read the full Notion report →
          </Link>
        </div>

        <GapCardPulse gaps={sampleGaps} />

        <p className="mt-6 text-center text-xs text-slate-700">
          A full report typically surfaces 10–20 gaps per market, ranked by evidence count,
          source diversity, and recency.
        </p>
      </div>
    </section>
  );
}
