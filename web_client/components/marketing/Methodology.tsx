export default function Methodology() {
  return (
    <section className="py-20 border-t border-slate-800/40">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mb-10 max-w-xl">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
            Under the hood
          </p>
          <h2 className="text-2xl font-bold text-slate-100">
            How we turn market noise into ranked gaps
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-500">
            Signal quality is everything. LidScout runs a multi-stage pipeline for every watched
            market before anything reaches your report — so what you see is evidence, not noise.
          </p>
        </div>

        <div className="relative">
          {/* Vertical connector */}
          <div className="absolute left-[19px] top-8 bottom-8 hidden w-px bg-slate-800/60 sm:block" />

          <div className="space-y-6">
            {[
              {
                step: '01',
                label: 'Fetch',
                heading: 'Daily crawl of every market source',
                body: 'LidScout pulls the latest posts from Reddit communities, review pages, Hacker News threads, forums, feeds, and product changelogs across every company in the market.',
                detail: 'Sources are polled every 24 hours. New sources can be added per market or per company.',
              },
              {
                step: '02',
                label: 'Rule filter',
                heading: 'Fast rejection of structural noise',
                body: 'Job listings, tutorial reposts, promotional content, and bot-generated posts are filtered out with deterministic rules before any LLM is involved. This removes roughly 60% of incoming volume immediately.',
                detail: 'No LLM cost, no latency — just pattern matching on post structure and metadata.',
              },
              {
                step: '03',
                label: 'LLM classifier',
                heading: 'Confirm genuine product pain',
                body: 'Each remaining post is sent to an LLM with a structured prompt: is this about the watched market or company, and does it express a real pain, request, workaround, or switching signal? Off-topic discussions are discarded.',
                detail: '~20% of posts survive to this stage; ~half of those are confirmed pain signals.',
              },
              {
                step: '04',
                label: 'Cluster',
                heading: 'Group signals by theme',
                body: 'Surviving findings are embedded and clustered by semantic similarity inside the market. Posts about calendar sync issues, event conflicts, and timezone bugs resolve to the same theme regardless of wording.',
                detail: 'Clusters are re-evaluated weekly so trends are always relative to prior state.',
              },
              {
                step: '05',
                label: 'Synthesise',
                heading: 'Generate the gap card',
                body: 'Each theme is passed to an LLM with the full pain statements, user types, company context, and evidence count. The model produces a structured gap card: title, affected user, pain summary, and suggested wedge.',
                detail: 'Output is validated against a strict schema. Malformed responses fall back to templated summaries — the pipeline never stalls.',
              },
              {
                step: '06',
                label: 'Rank + deliver',
                heading: 'Friday report, ranked by signal strength',
                body: 'Gaps are scored by evidence count, source diversity, recency, and user specificity. The top gaps land in your inbox Friday morning — with direct links to the source posts so you can read the raw evidence yourself.',
                detail: 'Email + in-app. Raw finding links preserved for every gap.',
              },
            ].map(({ step, label, heading, body, detail }) => (
              <div key={step} className="flex gap-5 sm:gap-8">
                <div className="flex flex-col items-center">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-800/60 bg-slate-900/60 text-[11px] font-bold tabular-nums text-slate-500">
                    {step}
                  </div>
                </div>
                <div className="pb-2">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="rounded-md border border-slate-800/50 bg-slate-800/30 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      {label}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-100">{heading}</h3>
                  </div>
                  <p className="mb-1.5 text-xs leading-relaxed text-slate-500">{body}</p>
                  <p className="text-[11px] leading-relaxed text-slate-700 italic">{detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
