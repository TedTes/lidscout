import Link from 'next/link';
import { IconArrow } from './icons';

export default function Pricing() {
  return (
    <section className="py-20 border-t border-slate-800/40">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mb-10 text-center max-w-xl mx-auto">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
            Pricing
          </p>
          <h2 className="text-2xl font-bold text-slate-100">
            Free during early access
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-500">
            Paid plans launch Q3. Until then, every feature is fully available at no cost — no
            trial limits, no credit card, no nag emails.
          </p>
        </div>

        <div className="mx-auto max-w-sm">
          <div className="rounded-2xl border border-violet-500/20 bg-slate-900/40 p-6">
            <div className="mb-1 flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-100">Early access</p>
              <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-400">
                Free until Q3
              </span>
            </div>
            <p className="mb-5 text-xs text-slate-600">
              No credit card required. Early users get a rate-lock when paid plans launch.
            </p>

            <ul className="mb-6 space-y-2.5">
              {[
                'Up to 3 markets monitored',
                'Company watchlists inside each market',
                'Weekly gap report every Friday',
                'Full source links on every finding',
                'Email + in-app delivery',
                'Slack digest (coming soon)',
              ].map((item) => (
                <li key={item} className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="shrink-0 text-emerald-500">✓</span>
                  {item}
                </li>
              ))}
            </ul>

            <Link
              href="/sources"
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:bg-violet-500"
            >
              Get your market report
              <IconArrow />
            </Link>
          </div>

          <p className="mt-4 text-center text-xs text-slate-700">
            Paid plans launch Q3 2026. Early access users are rate-locked at launch pricing.
          </p>
        </div>
      </div>
    </section>
  );
}
