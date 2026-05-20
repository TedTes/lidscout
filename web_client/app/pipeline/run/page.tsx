'use client';

import { FormEvent, useState } from 'react';
import DashboardShell from '@/components/DashboardShell';
import { ErrorPanel, Metric } from '@/components/DashboardPrimitives';
import { signalApi } from '@/lib/api';
import { PipelineRunResult } from '@/lib/types/signals';

export default function PipelineRunPage() {
  const [recipient, setRecipient] = useState('');
  const [subreddit, setSubreddit] = useState('startups');
  const [hnConfig, setHnConfig] = useState('top');
  const [limit, setLimit] = useState(10);
  const [includeReddit, setIncludeReddit] = useState(true);
  const [includeHackerNews, setIncludeHackerNews] = useState(true);
  const [result, setResult] = useState<PipelineRunResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      const data = await signalApi.runPipeline({
        recipient,
        reddit_sources: includeReddit ? [{ subreddit, limit }] : [],
        hackernews_sources: includeHackerNews ? [{ config: hnConfig, limit }] : [],
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
      subtitle={result ? `Last run sent to ${result.email.recipient}` : 'Run the configured signal workflow'}
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,440px)_1fr]">
        <form onSubmit={run} className="space-y-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div>
            <label className="text-sm font-medium text-gray-700" htmlFor="recipient">
              Recipient
            </label>
            <input
              id="recipient"
              type="email"
              required
              value={recipient}
              onChange={event => setRecipient(event.target.value)}
              placeholder="founder@example.com"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            />
          </div>

          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-3">
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
              <input
                type="checkbox"
                checked={includeReddit}
                onChange={event => setIncludeReddit(event.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-sky-700 focus:ring-sky-600"
              />
              Reddit
            </label>
            <div className="grid gap-3 sm:grid-cols-[1fr_120px]">
              <input
                value={subreddit}
                onChange={event => setSubreddit(event.target.value)}
                disabled={!includeReddit}
                placeholder="subreddit"
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:bg-gray-50"
              />
              <NumberInput value={limit} onChange={setLimit} disabled={!includeReddit && !includeHackerNews} />
            </div>
          </fieldset>

          <fieldset className="space-y-3 rounded-lg border border-gray-200 p-3">
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
              <input
                type="checkbox"
                checked={includeHackerNews}
                onChange={event => setIncludeHackerNews(event.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-sky-700 focus:ring-sky-600"
              />
              Hacker News
            </label>
            <select
              value={hnConfig}
              onChange={event => setHnConfig(event.target.value)}
              disabled={!includeHackerNews}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:bg-gray-50"
            >
              <option value="top">Top stories</option>
              <option value="new">New stories</option>
              <option value="ask">Ask HN</option>
              <option value="show">Show HN</option>
              <option value="best">Best stories</option>
            </select>
          </fieldset>

          <button
            type="submit"
            disabled={isRunning || (!includeReddit && !includeHackerNews)}
            className="w-full rounded-lg bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? 'Running pipeline' : 'Run pipeline'}
          </button>

          {error && <ErrorPanel message={error} />}
        </form>

        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-900">Run status</h2>
          {!result && !isRunning && (
            <p className="mt-3 text-sm text-gray-500">No pipeline run in this session.</p>
          )}
          {isRunning && (
            <div className="mt-3 flex items-center gap-3 text-sm text-sky-800">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-sky-200 border-t-sky-700" />
              Running fetch, extraction, scoring, clustering, report, and email steps.
            </div>
          )}
          {result && (
            <div className="mt-4 space-y-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric label="Fetched" value={result.fetched_count} />
                <Metric label="Signals" value={result.extracted_count} />
                <Metric label="Clusters" value={result.clustered_count} />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <StatusRow label="Ingested" value={result.ingestion.inserted_count} />
                <StatusRow label="Duplicates" value={result.ingestion.duplicate_count} />
                <StatusRow label="No signal" value={result.no_signal_count} />
                <StatusRow label="Extraction failed" value={result.extraction_failed_count} />
                <StatusRow label="Scored" value={result.scoring.scored_count} />
                <StatusRow label="Score average" value={result.scoring.average_score.toFixed(2)} />
                <StatusRow label="Embedding failed" value={result.embedding_failed_count} />
                <StatusRow label="Email sent" value={result.email.sent ? 'Yes' : 'No'} />
              </div>

              {result.email.error && <ErrorPanel message={result.email.error} />}
            </div>
          )}
        </section>
      </div>
    </DashboardShell>
  );
}

function NumberInput({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled: boolean;
}) {
  return (
    <input
      type="number"
      min={1}
      max={100}
      value={value}
      onChange={event => onChange(Number(event.target.value))}
      disabled={disabled}
      className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:bg-gray-50"
    />
  );
}

function StatusRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="font-semibold text-gray-900">{value}</span>
    </div>
  );
}
