import ScanPanelLive from './animations/ScanPanelLive';

const STEPS = [
  {
    title: 'Define your market once',
    body: 'Set your scope: the product or category to watch, the companies you care about, and the public sources that actually work today.',
    aside: 'GitHub issues · HN · Discourse · Stack Overflow · community forums',
  },
  {
    title: 'The agent loop runs continuously',
    body: 'Every day, the agent fetches sources, strips noise with rules then LLM relevance, extracts structured pain signals, and clusters them into themes. No prompting required.',
    aside: '~80% of posts are discarded before a finding is extracted.',
  },
  {
    title: 'Ranked with receipts',
    body: 'The output is a short list of recurring complaints, each backed by a real quote and a link to the original public post.',
    aside: 'Finding → theme → ranked gap → source link',
  },
  {
    title: 'Feedback trains future runs',
    body: 'Save a gap, dismiss noise — every action is stored. The next run adjusts its ranking, source weights, and priorities based on what you\'ve already signaled matters.',
    aside: 'The agent learns which sources and themes are worth prioritizing.',
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
          An agent loop, not a one-shot search
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
