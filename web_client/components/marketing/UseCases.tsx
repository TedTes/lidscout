const CASES = [
  {
    audience: 'Product teams',
    statement: 'See where the niche is weakest before your roadmap is locked.',
    body: 'Track named companies in your niche. Recurring complaints become ranked gaps with source quotes attached — ready to bring into planning without a research detour.',
    signals: ['Competitor-scoped findings', 'Weekly cadence', 'Evidence links on every claim'],
  },
  {
    audience: 'Founders',
    statement: 'Validate a space by reading what users already say in public.',
    body: 'Monitor a niche across companies and surface patterns that keep appearing. Skip the assumptions — the niche is already documenting its own pain.',
    signals: ['Niche-level themes', 'Cross-company signals', 'Suggested wedge per gap'],
  },
];

export default function UseCases() {
  return (
    <section className="border-t border-slate-800/40 py-20">
      <div className="mx-auto max-w-5xl px-6">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
          Use cases
        </p>
        <h2 className="mb-14 text-2xl font-bold text-slate-100">
          Two ways to read the same signal
        </h2>

        <div className="divide-y divide-slate-800/50">
          {CASES.map((c, i) => (
            <div
              key={c.audience}
              className={`py-10 grid items-center gap-8 md:grid-cols-[1fr_1.4fr] ${
                i % 2 === 1 ? 'md:[direction:rtl]' : ''
              }`}
            >
              {/* Statement side */}
              <div className={i % 2 === 1 ? 'md:[direction:ltr]' : ''}>
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-violet-500">
                  {c.audience}
                </p>
                <p className="text-2xl font-bold leading-snug text-slate-100">
                  {c.statement}
                </p>
              </div>

              {/* Evidence side */}
              <div className={i % 2 === 1 ? 'md:[direction:ltr]' : ''}>
                <p className="mb-5 text-sm leading-relaxed text-slate-500">{c.body}</p>
                <div className="flex flex-wrap gap-x-5 gap-y-1.5">
                  {c.signals.map((s) => (
                    <span key={s} className="flex items-center gap-1.5 text-[11px] text-slate-600">
                      <span className="h-1 w-1 rounded-full bg-violet-500/50" />
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
