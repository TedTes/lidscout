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
            Free while we&apos;re in beta
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-500">
            LidScout is in early access. Get a full report for any product at no cost while we
            fine-tune signal quality with real teams.
          </p>
        </div>

        <div className="mx-auto max-w-sm">
          <div className="rounded-2xl border border-violet-500/20 bg-slate-900/40 p-6">
            <div className="mb-1 flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-100">Beta access</p>
              <span className="rounded-md bg-violet-500/10 px-2 py-0.5 text-[11px] font-semibold text-violet-400">
                Free
              </span>
            </div>
            <p className="mb-5 text-xs text-slate-600">
              No credit card. Cancel any time.
            </p>

            <ul className="mb-6 space-y-2.5">
              {[
                'Up to 3 products monitored',
                'Weekly gap report every Friday',
                'Full source links on every signal',
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
              Get your free report
              <IconArrow />
            </Link>
          </div>

          <p className="mt-4 text-center text-xs text-slate-700">
            Paid plans will be introduced after beta. Early users will be grandfathered.
          </p>
        </div>
      </div>
    </section>
  );
}
