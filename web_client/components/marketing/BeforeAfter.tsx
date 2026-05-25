const NOISE: Array<{ time: string; text: string; state: 'normal' | 'crossed' | 'faded' }> = [
  { time: '09:14', text: 'r/notion — "timezone sync still broken after update"', state: 'normal' },
  { time: '09:31', text: 'Linear roadmap export thread — bookmark for later', state: 'crossed' },
  { time: '10:02', text: '47 tabs open ← review before standup', state: 'crossed' },
  { time: '11:48', text: 'Figma silent data loss HN thread (find again?)', state: 'faded' },
  { time: '14:20', text: 'G2 reviews Asana — something about meetings + workload', state: 'normal' },
  { time: '14:55', text: 'Ask Sarah what she found on Notion calendar', state: 'crossed' },
  { time: 'Fri',   text: 'Roadmap meeting was yesterday. Start again Monday.', state: 'faded' },
];

export default function BeforeAfter() {
  return (
    <section className="border-t border-slate-800/40 py-20">
      <div className="mx-auto max-w-5xl px-6">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
          The alternative
        </p>
        <h2 className="mb-14 max-w-xl text-3xl font-bold leading-snug text-slate-100">
          The market is already talking.{' '}
          <br className="hidden sm:block" />
          You need an agent that never stops listening.
        </h2>

        <div className="grid items-start gap-14 lg:grid-cols-2">
          {/* Left — research pile */}
          <div>
            <p className="mb-5 text-[11px] font-semibold uppercase tracking-widest text-slate-700">
              Manual research — last week
            </p>
            <div className="space-y-3 font-mono text-[11px] leading-relaxed">
              {NOISE.map((item, i) => (
                <div key={i} className="flex items-baseline gap-3">
                  <span className="w-9 shrink-0 text-right text-slate-800">{item.time}</span>
                  <span
                    className={
                      item.state === 'crossed'
                        ? 'text-slate-700 line-through'
                        : item.state === 'faded'
                        ? 'text-slate-800'
                        : 'text-slate-500'
                    }
                  >
                    {item.text}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-6 pl-12 text-[11px] italic text-slate-800">
              Next week: start again.
            </p>
          </div>

          {/* Right — product output */}
          <div>
            <p className="mb-5 text-[11px] font-semibold uppercase tracking-widest text-slate-700">
              LidScout agent — this Friday
            </p>

            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-emerald-600">
              Strong evidence · 14 mentions
            </p>
            <h3 className="mb-3 text-xl font-bold leading-snug text-slate-100">
              Calendar reliability blocks team adoption
            </h3>

            <blockquote className="mb-5 border-l-2 border-slate-700 pl-4 text-xs italic leading-relaxed text-slate-500">
              &ldquo;We tried to move our whole team to Notion Calendar but the timezone sync
              issues made it unusable after two weeks. Back to Google Calendar.&rdquo;
              <footer className="mt-1.5 not-italic text-slate-700">r/Notion</footer>
            </blockquote>

            <p className="text-xs text-slate-600">
              <span className="font-medium text-slate-500">Suggested wedge — </span>
              A lightweight timezone-aware sync layer that treats Notion as the source of truth
              while resolving conflicts server-side.
            </p>

            <div className="mt-8 flex gap-8 border-t border-slate-800/50 pt-5">
              {[
                { n: '147', label: 'findings scanned' },
                { n: '12',  label: 'themes grouped'   },
                { n: '4',   label: 'gaps ranked'       },
              ].map(({ n, label }) => (
                <div key={label}>
                  <p className="text-2xl font-black tabular-nums text-violet-400">{n}</p>
                  <p className="text-[10px] text-slate-700">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
