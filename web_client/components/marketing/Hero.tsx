import Link from 'next/link';
import { IconArrow } from './icons';
import LiveActivityCounter from './animations/LiveActivityCounter';
import PipelineFunnel from './animations/PipelineFunnel';
import ProductSearch from './animations/ProductSearch';

export default function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 pb-16">
      {/* Glow */}
      <div className="pointer-events-none absolute inset-0 flex items-start justify-center">
        <div className="h-[500px] w-[700px] -translate-y-1/4 rounded-full bg-violet-600/[0.05] blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-5xl px-6">
        {/* Top row: copy (left) + funnel (right on lg) */}
        <div className="flex items-start justify-between gap-8">
          <div className="min-w-0 flex-1">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-500/[0.06] px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.9)]" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-violet-300">
              Continuous opportunity research
              </span>
            </div>

            <div className="mb-8 max-w-xl">
              <h1 className="mb-5 text-4xl font-extrabold leading-tight tracking-tight text-slate-50 lg:text-5xl">
                Evidence-backed market research for product opportunities
              </h1>
              <p className="mb-7 max-w-lg text-base leading-relaxed text-slate-400">
                Pick a niche, track the companies inside it, and let LidScout surface
                recurring user pain from Reddit, Hacker News, reviews, forums, and changelogs
                as ranked product gaps with source evidence.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/sources"
                  className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:bg-violet-500"
                >
                  Get a market report
                  <IconArrow />
                </Link>
                <Link
                  href="/reports/notion-2026"
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-800/50 px-5 py-2.5 text-sm font-semibold text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100"
                >
                  See a sample report →
                </Link>
              </div>
            </div>
          </div>

          {/* Pipeline funnel — lg only */}
          <div className="shrink-0 hidden lg:flex items-center justify-end pl-4 pt-2">
            <div className="relative pl-28">
              <PipelineFunnel />
            </div>
          </div>
        </div>

        {/* Activity counter */}
        <div className="mb-6">
          <LiveActivityCounter />
        </div>

        {/* Interactive market search + gap cards */}
        <ProductSearch />
      </div>
    </section>
  );
}
