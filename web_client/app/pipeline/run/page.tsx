'use client';

import { FormEvent, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import { ErrorPanel, Metric, SectionCard } from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { PipelineRunResult } from '@/lib/types/signals';

const PIPELINE_STEPS = [
  'Fetch posts',
  'Ingest & deduplicate',
  'Extract signals',
  'Score signals',
  'Embed & cluster',
  'Generate report',
  'Send email',
];

function CheckIcon() {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default function PipelineRunPage() {
  const [recipient, setRecipient] = useState('');
  const [sourceLocators, setSourceLocators] = useState('');
  const [limit, setLimit] = useState(10);
  const [result, setResult] = useState<PipelineRunResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      const sources = sourceLocators
        .split('\n')
        .map(locator => locator.trim())
        .filter(Boolean)
        .map(locator => ({ locator, limit }));
      const data = await signalApi.runPipeline({
        recipient,
        sources,
        default_limit: limit,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline run failed');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <DashboardShell
      title="Pipeline run"
      subtitle={result ? `Last run sent to ${result.email.recipient}` : 'Configure and trigger the signal detection workflow'}
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,420px)_1fr]">
        {/* ── Config form ────────────────────────────────────────── */}
        <form
          onSubmit={run}
          className="space-y-4 rounded-xl border border-slate-800/80 bg-slate-900/40 p-5"
        >
          <h2 className="text-sm font-semibold text-slate-200">Configuration</h2>

          {/* Recipient */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400" htmlFor="recipient">
              Report recipient
            </label>
            <input
              id="recipient"
              type="email"
              required
              value={recipient}
              onChange={e => setRecipient(e.target.value)}
              placeholder="founder@example.com"
              className="w-full rounded-lg border border-slate-700/80 bg-slate-800/60 px-3 py-2.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10"
            />
          </div>

          {/* Generic sources */}
          <fieldset className="rounded-lg border border-slate-800/80 p-4">
            <label className="mb-1.5 block text-sm font-semibold text-slate-300" htmlFor="source-locators">
              Source locators
            </label>
            <textarea
              id="source-locators"
              value={sourceLocators}
              onChange={e => setSourceLocators(e.target.value)}
              rows={4}
              placeholder={'https://example.com/reviews\nhttps://example.com/thread.json\nhttps://example.com/customer-feedback'}
              className="w-full resize-none rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-300 outline-none placeholder:text-slate-600 transition focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10"
            />
          </fieldset>

          <fieldset className="rounded-lg border border-slate-800/80 p-4">
            <div>
              <label className="mb-1 block text-xs text-slate-600" htmlFor="limit">
                Limit per locator
              </label>
              <input
                id="limit"
                type="number"
                min={1}
                max={100}
                value={limit}
                onChange={e => setLimit(Number(e.target.value))}
                className="w-full rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-300 outline-none transition focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/10 disabled:opacity-40"
              />
            </div>
          </fieldset>

          {/* Submit */}
          <button
            type="submit"
            disabled={isRunning || !sourceLocators.trim()}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-950 transition hover:bg-violet-500 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-violet-400/30 border-t-white" />
                Running pipeline…
              </>
            ) : (
              <>
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="opacity-90"
                >
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Run pipeline
              </>
            )}
          </button>

          {error && <ErrorPanel message={error} />}
        </form>

        {/* ── Run status ──────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* Step progress */}
          <SectionCard title="Pipeline steps">
            <div className="space-y-2">
              {PIPELINE_STEPS.map((step, i) => {
                const done = result != null;
                const running = isRunning;
                return (
                  <div key={step} className="flex items-center gap-3">
                    <div
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold transition-all duration-300 ${
                        done
                          ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-400'
                          : running
                            ? 'border-violet-500/40 bg-violet-500/10 text-violet-400'
                            : 'border-slate-700/60 bg-slate-800/50 text-slate-600'
                      }`}
                    >
                      {done ? <CheckIcon /> : i + 1}
                    </div>
                    <span
                      className={`text-sm transition-colors ${
                        done
                          ? 'text-slate-300'
                          : running
                            ? 'text-slate-400'
                            : 'text-slate-600'
                      }`}
                    >
                      {step}
                    </span>
                    {running && i === 0 && (
                      <span className="ml-auto h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />
                    )}
                  </div>
                );
              })}
            </div>
          </SectionCard>

          {/* Results */}
          {result && (
            <div className="space-y-4 animate-fade-in">
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric label="Fetched" value={result.fetched_count} />
                <Metric label="Signals" value={result.extracted_count} />
                <Metric label="Clusters" value={result.clustered_count} accent />
              </div>

              <SectionCard title="Run details">
                <div className="grid gap-2 sm:grid-cols-2">
                  <StatRow label="Ingested" value={result.ingestion.inserted_count} />
                  <StatRow label="Duplicates" value={result.ingestion.duplicate_count} />
                  <StatRow label="No signal" value={result.no_signal_count} />
                  <StatRow label="Extract failed" value={result.extraction_failed_count} />
                  <StatRow label="Scored" value={result.scoring.scored_count} />
                  <StatRow
                    label="Avg score"
                    value={result.scoring.average_score.toFixed(2)}
                  />
                  <StatRow label="Embed failed" value={result.embedding_failed_count} />
                  <StatRow
                    label="Email sent"
                    value={result.email.sent ? 'Yes' : 'No'}
                    highlight={result.email.sent}
                  />
                </div>
                {result.email.error && (
                  <div className="mt-3">
                    <ErrorPanel message={result.email.error} />
                  </div>
                )}
              </SectionCard>
            </div>
          )}

          {!result && !isRunning && (
            <div className="rounded-xl border border-dashed border-slate-800 px-6 py-10 text-center">
              <p className="text-sm text-slate-600">No pipeline run in this session.</p>
              <p className="mt-1 text-xs text-slate-700">Configure and run the pipeline to see results here.</p>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}

function StatRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-800/60 bg-slate-800/30 px-3 py-2">
      <span className="text-xs text-slate-500">{label}</span>
      <span
        className={`text-xs font-semibold tabular-nums ${
          highlight ? 'text-emerald-400' : 'text-slate-300'
        }`}
      >
        {value}
      </span>
    </div>
  );
}
