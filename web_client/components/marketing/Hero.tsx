import Link from 'next/link';
import { IconArrow } from './icons';
import LiveActivityCounter from './animations/LiveActivityCounter';
import PipelineFunnel from './animations/PipelineFunnel';
import { sampleGaps } from './sampleGaps';
import GapCard from './GapCard';

export default function Hero() {
  const featured = sampleGaps.slice(0, 3);

  return (
    <section className="relative overflow-hidden pt-28 pb-16">
      {/* Glow */}
      <div className="pointer-events-none absolute inset-0 flex items-start justify-center">
        <div className="h-[500px] w-[700px] -translate-y-1/4 rounded-full bg-violet-600/[0.05] blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-5xl px-6">

        {/* Top row: copy (left) + funnel (right on lg) */}
        <div className="flex items-start justify-between gap-8">
          {/* Left: label + headline + CTAs */}
          <div className="min-w-0 flex-1">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-500/[0.06] px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.9)]" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-violet-300">
                Continuous customer research
              </span>
            </div>

            <div className="mb-8 max-w-xl">
              <h1 className="mb-5 text-4xl font-extrabold leading-tight tracking-tight text-slate-50 lg:text-5xl">
                User interviews you don&apos;t have to schedule
              </h1>
              <p className="mb-7 max-w-lg text-base leading-relaxed text-slate-400">
                LidScout scans Reddit, Hacker News, G2, and review sites continuously —
                extracting and ranking what users actually want, delivered as a weekly
                gap report your team can act on.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/sources"
                  className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:bg-violet-500"
                >
                  Get a free report
                  <IconArrow />
                </Link>
                <Link
                  href="/reports/notion-2026"
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-800/50 px-5 py-2.5 text-sm font-semibold text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100"
                >
                  Read the Notion analysis →
                </Link>
              </div>
            </div>
          </div>

          {/* Right: pipeline funnel — only visible lg+ */}
          <div className="shrink-0 hidden lg:flex items-center justify-end pl-4 pt-2">
            <div className="relative pl-28">
              <PipelineFunnel />
            </div>
          </div>
        </div>

        {/* Activity counter */}
        <div className="mb-5">
          <LiveActivityCounter />
        </div>

        {/* Gap cards */}
        <div className="mb-1 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          <p className="text-xs text-slate-600">
            Live output — Notion gaps surfaced this week
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {featured.map((gap, i) => (
            <GapCard key={gap.id} gap={gap} dimmed={i === 2} />
          ))}
        </div>
        <p className="mt-3 text-right text-xs text-slate-700">
          + 11 more gaps in the full Notion report →
        </p>
      </div>
    </section>
  );
}
