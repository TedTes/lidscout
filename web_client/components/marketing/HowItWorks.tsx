import ScanPanelLive from './animations/ScanPanelLive';

export default function HowItWorks() {
  return (
    <section className="py-20 border-t border-slate-800/40">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mb-10 max-w-xl">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
            How it works
          </p>
          <h2 className="text-2xl font-bold text-slate-100">
            Choose a market once, get signal every week
          </h2>
        </div>

        <div className="space-y-4">
          {/* Step 1 */}
          <div className="grid gap-6 rounded-2xl border border-slate-800/60 bg-slate-900/30 p-6 sm:grid-cols-[1fr_320px]">
            <div className="flex flex-col justify-center">
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold tabular-nums text-slate-500">
                  1
                </span>
                <h3 className="text-sm font-semibold text-slate-100">
                  Add a market watchlist
                </h3>
              </div>
              <p className="mb-3 text-xs leading-relaxed text-slate-500">
                Start with a niche such as workspace tools, vertical SaaS, or AI devtools.
                Add the companies you want watched inside that market, then attach review pages,
                forums, Reddit searches, changelogs, and JSON feeds.
              </p>
              <p className="text-xs text-slate-600 italic">
                Example: add <span className="text-slate-400">Workspace tools</span> → track{' '}
                <span className="text-slate-400">Notion, Linear, Figma, Asana</span>
              </p>
            </div>
            {/* Visual */}
            <div className="rounded-xl border border-slate-800/50 bg-[#0a0c1e] p-4 text-xs">
              <p className="mb-3 text-slate-600 text-[10px] uppercase tracking-wider">Add market</p>
              <div className="mb-2 rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2 text-slate-300">
                Workspace tools
              </div>
              <div className="mb-3 rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2 text-slate-500">
                Notion · Linear · Figma · Asana
              </div>
              <p className="mb-2 text-slate-700 text-[10px]">Suggested sources</p>
              <div className="flex flex-wrap gap-1.5">
                {['Reddit', 'G2', 'Hacker News', 'Changelogs', 'Capterra'].map((s) => (
                  <span
                    key={s}
                    className="rounded-md border border-violet-500/20 bg-violet-500/[0.06] px-2 py-0.5 text-[10px] text-violet-400"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Step 2 */}
          <div className="grid gap-6 rounded-2xl border border-slate-800/60 bg-slate-900/30 p-6 sm:grid-cols-[1fr_320px]">
            <div className="flex flex-col justify-center">
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold tabular-nums text-slate-500">
                  2
                </span>
                <h3 className="text-sm font-semibold text-slate-100">
                  We listen continuously
                </h3>
              </div>
              <p className="mb-3 text-xs leading-relaxed text-slate-500">
                LidScout fetches every source on a daily cadence. Each post passes through a
                two-stage filter — first fast rule-based rejection of noise (job posts, tutorials,
                promotions), then an LLM classifier that confirms whether the post expresses
                genuine product pain.
              </p>
              <p className="text-xs text-slate-600 italic">
                We discard roughly <span className="text-slate-400">80% of incoming posts</span>{' '}
                as low-signal before anything reaches your report.
              </p>
            </div>
            {/* Visual — animated scan panel */}
            <ScanPanelLive />
          </div>

          {/* Step 3 */}
          <div className="grid gap-6 rounded-2xl border border-slate-800/60 bg-slate-900/30 p-6 sm:grid-cols-[1fr_320px]">
            <div className="flex flex-col justify-center">
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold tabular-nums text-slate-500">
                  3
                </span>
                <h3 className="text-sm font-semibold text-slate-100">
                  Every Friday: a ranked gap report
                </h3>
              </div>
              <p className="mb-3 text-xs leading-relaxed text-slate-500">
                Findings are embedded and clustered by theme within the selected market.
                Recurring clusters become ranked product gaps — each with a target user, pain
                summary, evidence quotes, and a specific suggested wedge.
              </p>
              <p className="text-xs text-slate-600 italic">
                Example this week:{' '}
                <span className="text-slate-400">
                  &ldquo;Calendar reliability complaints now appear across 3 workspace tools.&rdquo;
                </span>
              </p>
            </div>
            {/* Visual */}
            <div className="rounded-xl border border-slate-800/50 bg-[#0a0c1e] p-4 text-xs">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-slate-400 font-semibold">Week of May 19</p>
                <span className="rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
                  3 new gaps
                </span>
              </div>
              <div className="space-y-2">
                <div className="rounded-lg border border-emerald-500/15 bg-emerald-500/[0.04] px-3 py-2">
                  <p className="text-slate-200 font-medium mb-0.5">Calendar reliability</p>
                  <p className="text-slate-600">14 mentions · +8 from last week</p>
                </div>
                <div className="rounded-lg border border-slate-800/40 bg-slate-800/20 px-3 py-2">
                  <p className="text-slate-300 font-medium mb-0.5">Database performance</p>
                  <p className="text-slate-600">11 mentions · +3 from last week</p>
                </div>
                <div className="rounded-lg border border-slate-800/40 bg-slate-800/20 px-3 py-2">
                  <p className="text-slate-400 mb-0.5">API rate limits</p>
                  <p className="text-slate-700">9 mentions</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
