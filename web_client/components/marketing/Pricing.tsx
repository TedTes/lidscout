import Link from 'next/link';
import { IconArrow } from './icons';

const FEATURES = [
  '3 markets',
  'company watchlists',
  'continuous agent loop',
  'feedback-trained ranking',
  'weekly digest + threshold alerts',
  'source links on every finding',
];

export default function Pricing() {
  return (
    <section className="border-t border-slate-800/40 py-24">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mx-auto max-w-2xl">
          {/* Headline */}
          <p className="mb-4 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
            Pricing
          </p>
          <h2 className="mb-3 text-4xl font-black leading-tight text-slate-100 sm:text-5xl">
            Free until Q3.
            <br />
            <span className="text-slate-500">No credit card. No catch.</span>
          </h2>
          <p className="mb-8 text-sm leading-relaxed text-slate-600">
            Every feature available now. Paid plans launch Q3 2026 — early access users are
            rate-locked at launch pricing.
          </p>

          {/* Feature row */}
          <div className="mb-10 flex flex-wrap items-center gap-x-1 gap-y-2">
            {FEATURES.map((f, i) => (
              <span key={f} className="flex items-center gap-1">
                <span className="text-xs text-slate-500">{f}</span>
                {i < FEATURES.length - 1 && (
                  <span className="text-slate-800 mx-0.5">·</span>
                )}
              </span>
            ))}
          </div>

          {/* CTA */}
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-900/50 transition hover:bg-violet-500"
          >
            Start your research agent
            <IconArrow />
          </Link>
        </div>
      </div>
    </section>
  );
}
