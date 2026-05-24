import ScanPanelLive from './animations/ScanPanelLive';

const STEPS = [
  {
    title: 'Watch a market',
    body: 'Define a niche, add the companies you care about, and attach their public sources — Reddit threads, review pages, HN, changelogs.',
    aside: 'Workspace tools · AI devtools · vertical SaaS',
  },
  {
    title: 'Filter real pain',
    body: 'Every post passes a two-stage filter. Rules strip noise instantly. An LLM confirms only posts that express genuine product frustration.',
    aside: 'Roughly 80% of incoming posts are discarded before clustering.',
  },
  {
    title: 'Read the ranked gaps',
    body: 'Surviving signals cluster into themes. Themes become gaps with a title, evidence count, source links, and a suggested wedge. Delivered Friday.',
    aside: 'Ranked by evidence count, recency, source diversity, and specificity.',
  },
];

export default function HowItWorks() {
  return (
    <section className="border-t border-slate-800/40 py-20">
      <div className="mx-auto max-w-5xl px-6">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
          How it works
        </p>
        <h2 className="mb-16 text-2xl font-bold text-slate-100">
          From market noise to ranked gaps
        </h2>

        <div className="grid items-start gap-14 lg:grid-cols-[1fr_320px]">
          {/* Steps — no card borders, large number anchors */}
          <div className="space-y-14">
            {STEPS.map((step, i) => (
              <div key={i} className="flex items-start gap-5">
                <span
                  className="select-none tabular-nums text-[72px] font-black leading-none text-slate-800/70 lg:text-[88px]"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <div className="pt-3">
                  <h3 className="mb-2 text-base font-bold text-slate-100">{step.title}</h3>
                  <p className="mb-2 text-sm leading-relaxed text-slate-500">{step.body}</p>
                  <p className="text-[11px] text-slate-700">{step.aside}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Scan panel */}
          <div className="lg:sticky lg:top-24">
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
              Live — step 2 in action
            </p>
            <ScanPanelLive />
          </div>
        </div>
      </div>
    </section>
  );
}
