import Link from 'next/link';
import { PRODUCT_DESCRIPTION, PRODUCT_TAGLINE } from '@/lib/positioning';
import { IconArrow } from './icons';
import MarketRadarPreview from './animations/MarketRadarPreview';

export default function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 pb-14">
      {/* Glow */}
      <div className="pointer-events-none absolute inset-0 flex items-start justify-center">
        <div className="h-[500px] w-[700px] -translate-y-1/4 rounded-full bg-violet-600/[0.05] blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-5xl px-6">
        <div className="grid items-center gap-10 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="min-w-0 flex-1">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-500/[0.06] px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_6px_rgba(167,139,250,0.9)]" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-violet-300">
                {PRODUCT_TAGLINE}
              </span>
            </div>

            <div className="mb-8 max-w-xl">
              <h1 className="mb-5 text-4xl font-extrabold leading-tight tracking-tight text-slate-50 lg:text-5xl">
                Your continuous competitive research agent
              </h1>
              <p className="mb-7 max-w-lg text-base leading-relaxed text-slate-400">
                {PRODUCT_DESCRIPTION}
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:bg-violet-500"
                >
                  Get started free
                  <IconArrow />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-800/50 px-5 py-2.5 text-sm font-semibold text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 hover:text-slate-100"
                >
                  Sign in →
                </Link>
              </div>
            </div>
          </div>

          <MarketRadarPreview />
        </div>
      </div>
    </section>
  );
}
