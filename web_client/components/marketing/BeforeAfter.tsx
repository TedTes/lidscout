export default function BeforeAfter() {
  return (
    <section className="py-20 border-t border-slate-800/40">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mb-10 max-w-xl">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
            The problem
          </p>
          <h2 className="text-2xl font-bold text-slate-100">
            Every PM already does this research — just badly
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-500">
            You know competitor feedback lives somewhere in Reddit, G2, and Twitter. You bookmark
            it. You mean to organise it. You never do. LidScout does the listening for you.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {/* Before */}
          <div className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-5">
            <div className="mb-4 flex items-center gap-2">
              <span className="rounded-md bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold text-rose-400">
                Without LidScout
              </span>
            </div>

            {/* Mock messy doc */}
            <div className="rounded-xl border border-slate-800/50 bg-[#0a0c1e] p-4 font-mono text-xs">
              <p className="mb-3 text-slate-400 font-sans font-semibold text-sm">Competitor Research — Q2</p>
              <div className="space-y-1.5 text-slate-600">
                <p>• TODO: catch up on r/notion this week</p>
                <p>• <span className="line-through opacity-50">read G2 reviews for Linear</span></p>
                <p>• bookmark dump (47 tabs)</p>
                <p>• <span className="text-amber-600/70">⚠ 3 unread Slack threads from sales</span></p>
                <p>• ask Sarah what she found on Figma</p>
                <p>• <span className="line-through opacity-50">write up findings before roadmap mtg</span></p>
                <p className="text-rose-600/60">• roadmap meeting was yesterday</p>
              </div>
              <div className="mt-4 border-t border-slate-800/50 pt-3 text-slate-700">
                <p>Last updated: 3 weeks ago</p>
              </div>
            </div>

            <ul className="mt-4 space-y-2">
              {[
                '4–6 hours per week of manual triage',
                'Stale by the time you read it',
                'No way to prioritise signal vs. noise',
                'Lives in one person\'s head',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2 text-xs text-slate-600">
                  <span className="mt-0.5 shrink-0 text-rose-600">✕</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* After */}
          <div className="rounded-2xl border border-violet-500/15 bg-slate-900/40 p-5">
            <div className="mb-4 flex items-center gap-2">
              <span className="rounded-md bg-violet-500/10 px-2 py-0.5 text-[11px] font-semibold text-violet-400">
                With LidScout
              </span>
            </div>

            {/* Mock clean report */}
            <div className="rounded-xl border border-slate-800/50 bg-[#0a0c1e] p-4 text-xs">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-slate-300 font-semibold text-sm">Week of May 19</p>
                <span className="text-slate-700">Notion · 14 gaps tracked</span>
              </div>
              <div className="space-y-2">
                {[
                  { label: 'Calendar reliability', count: 14, up: true },
                  { label: 'Database performance', count: 11, up: true },
                  { label: 'API rate limits', count: 9, up: false },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between rounded-lg border border-slate-800/40 bg-slate-800/20 px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]" />
                      <span className="text-slate-300">{item.label}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <span className="tabular-nums">{item.count}</span>
                      {item.up && <span className="text-emerald-600 text-[10px]">↑</span>}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-slate-700">Delivered Friday 07:00 · next in 5 days</p>
            </div>

            <ul className="mt-4 space-y-2">
              {[
                'Zero hours of manual research',
                'Updated continuously, not when you remember',
                'Ranked by signal strength and recency',
                'Shareable with the whole team',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2 text-xs text-slate-400">
                  <span className="mt-0.5 shrink-0 text-emerald-500">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
