'use client';

import { useEffect, useState } from 'react';
import {
  InteractionExtractionResponse,
  NegativeSignal,
  PublicInteraction,
} from '@/lib/types/interaction';

type Tab = 'signals' | 'negative' | 'comments' | 'json';

const TABS: { id: Tab; label: string }[] = [
  { id: 'signals', label: 'Signals' },
  { id: 'negative', label: 'Negative' },
  { id: 'comments', label: 'Comments' },
  { id: 'json', label: 'Page JSON' },
];

interface Props {
  results: InteractionExtractionResponse | null;
}

export default function InteractionResults({ results }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('signals');

  useEffect(() => {
    setActiveTab('signals');
  }, [results]);

  if (!results) {
    return (
      <div className="flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed border-gray-200 bg-white p-10 text-center">
        <SearchIllustration />
        <p className="mt-4 text-sm font-medium text-gray-700">No results yet</p>
        <p className="mt-1 max-w-xs text-xs text-gray-400">
          Enter a URL above and click Extract to see page data, comments, and negative signals.
        </p>
      </div>
    );
  }

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lidscout-${Date.now()}.json`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const tabCount = (tab: Tab): number | null => {
    if (tab === 'signals') return results.negative_signals.length;
    if (tab === 'negative') return results.negative_comments.length;
    if (tab === 'comments') return results.interactions.length;
    return null;
  };

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 px-5 py-4">
        <div className="flex flex-wrap items-center gap-5">
          <Stat label="Sources" value={results.total_sources} />
          <div className="h-6 w-px bg-gray-200" />
          <Stat label="Comments" value={results.interactions.length} />
          <Stat label="Negative" value={results.negative_comments.length} color="red" />
          <Stat label="Signals" value={results.negative_signals.length} color="amber" />
        </div>
        <button
          onClick={exportJson}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 transition hover:border-sky-400 hover:text-sky-700"
        >
          Export JSON
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-gray-100 px-2">
        {TABS.map(tab => {
          const count = tabCount(tab.id);
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-1.5 px-3 py-3 text-sm font-medium transition ${
                active ? 'text-sky-700' : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              {tab.label}
              {count !== null && (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-xs font-semibold ${
                    active ? 'bg-sky-100 text-sky-700' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {count}
                </span>
              )}
              {active && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t-sm bg-sky-700" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="p-5">
        {activeTab === 'signals' && (
          <SignalsTab signals={results.negative_signals} />
        )}
        {activeTab === 'negative' && (
          <CommentsTab
            comments={results.negative_comments}
            emptyText="No negative comments were identified in the extracted content."
          />
        )}
        {activeTab === 'comments' && (
          <CommentsTab
            comments={results.interactions}
            emptyText="No comments were found in the extracted content."
          />
        )}
        {activeTab === 'json' && (
          <pre className="max-h-[520px] overflow-auto rounded-lg bg-gray-950 p-4 text-xs leading-5 text-gray-100">
            {JSON.stringify(results.pages, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

// ─── Signals tab ──────────────────────────────────────────────────────────────

const SEVERITY_STYLES = {
  high: {
    card: 'border-red-200 bg-red-50',
    badge: 'border-red-200 bg-red-100 text-red-700',
    dot: 'bg-red-500',
    label: 'High',
  },
  medium: {
    card: 'border-amber-200 bg-amber-50',
    badge: 'border-amber-200 bg-amber-100 text-amber-700',
    dot: 'bg-amber-500',
    label: 'Medium',
  },
  low: {
    card: 'border-blue-200 bg-blue-50',
    badge: 'border-blue-200 bg-blue-100 text-blue-700',
    dot: 'bg-blue-400',
    label: 'Low',
  },
} as const;

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

function SignalsTab({ signals }: { signals: NegativeSignal[] }) {
  if (signals.length === 0) {
    return (
      <EmptyState
        title="No negative signals found"
        description="No recurring negative themes were identified in the extracted content."
      />
    );
  }

  const sorted = [...signals].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3)
  );

  return (
    <div className="space-y-3">
      {sorted.map(signal => (
        <SignalCard key={signal.theme} signal={signal} />
      ))}
    </div>
  );
}

function SignalCard({ signal }: { signal: NegativeSignal }) {
  const [expanded, setExpanded] = useState(false);
  const styles = SEVERITY_STYLES[signal.severity] ?? SEVERITY_STYLES.low;
  const showToggle = signal.excerpts.length > 2;
  const visible = expanded ? signal.excerpts : signal.excerpts.slice(0, 2);

  return (
    <div className={`rounded-lg border p-4 ${styles.card}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${styles.dot}`} />
          <h3 className="font-semibold text-gray-900">{signal.theme}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${styles.badge}`}>
            {styles.label}
          </span>
          <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-600">
            {signal.frequency} {signal.frequency === 1 ? 'mention' : 'mentions'}
          </span>
        </div>
      </div>

      {signal.excerpts.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {visible.map((excerpt, i) => (
            <p key={i} className="text-sm leading-6 text-gray-700 before:mr-1 before:text-gray-400 before:content-['“'] after:ml-0.5 after:text-gray-400 after:content-['”']">
              {excerpt}
            </p>
          ))}
          {showToggle && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="mt-1 text-xs text-sky-700 hover:underline"
            >
              {expanded ? 'Show fewer excerpts' : `+ ${signal.excerpts.length - 2} more excerpts`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Comments tab ─────────────────────────────────────────────────────────────

const SENTIMENT_STYLES: Record<string, { label: string; className: string }> = {
  negative: { label: 'Negative', className: 'border-red-100 bg-red-50 text-red-700' },
  positive: { label: 'Positive', className: 'border-green-100 bg-green-50 text-green-700' },
  neutral: { label: 'Neutral', className: 'border-gray-200 bg-gray-50 text-gray-600' },
  mixed: { label: 'Mixed', className: 'border-amber-100 bg-amber-50 text-amber-700' },
  unknown: { label: 'Unknown', className: 'border-gray-200 bg-gray-50 text-gray-500' },
};

function CommentsTab({ comments, emptyText }: { comments: PublicInteraction[]; emptyText: string }) {
  const [filter, setFilter] = useState('all');

  if (comments.length === 0) {
    return <EmptyState title="No comments found" description={emptyText} />;
  }

  const presentSentiments = Array.from(new Set(comments.map(c => c.sentiment)));
  const showFilter = presentSentiments.length > 1;
  const filtered = filter === 'all' ? comments : comments.filter(c => c.sentiment === filter);

  return (
    <div className="space-y-4">
      {showFilter && (
        <div className="flex flex-wrap gap-1.5">
          <FilterChip label={`All (${comments.length})`} active={filter === 'all'} onClick={() => setFilter('all')} />
          {presentSentiments.map(s => (
            <FilterChip
              key={s}
              label={SENTIMENT_STYLES[s]?.label ?? s}
              active={filter === s}
              onClick={() => setFilter(s)}
            />
          ))}
        </div>
      )}

      <div className="space-y-3">
        {filtered.map(comment => (
          <CommentCard key={comment.interaction_id} comment={comment} />
        ))}
      </div>
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
        active
          ? 'border-sky-500 bg-sky-50 text-sky-700'
          : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:text-gray-800'
      }`}
    >
      {label}
    </button>
  );
}

function CommentCard({ comment }: { comment: PublicInteraction }) {
  const senti = SENTIMENT_STYLES[comment.sentiment] ?? SENTIMENT_STYLES.unknown;

  return (
    <article className="rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${senti.className}`}>
          {senti.label}
        </span>
        {comment.rating != null && (
          <span className="text-xs text-gray-500">{comment.rating.toFixed(1)} / 5</span>
        )}
        {comment.author && (
          <span className="text-xs text-gray-500">{comment.author}</span>
        )}
        {comment.published_at && (
          <span className="text-xs text-gray-400">{formatDate(comment.published_at)}</span>
        )}
      </div>

      {comment.title && (
        <p className="mt-2 text-xs font-semibold text-gray-700">{comment.title}</p>
      )}

      <p className="mt-2 text-sm leading-6 text-gray-700">{comment.body}</p>

      {comment.topics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {comment.topics.map(topic => (
            <span
              key={topic}
              className="rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-500"
            >
              {topic}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

// ─── Shared primitives ────────────────────────────────────────────────────────

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: 'red' | 'amber';
}) {
  const valueColor =
    color === 'red'
      ? 'text-red-600'
      : color === 'amber'
      ? 'text-amber-600'
      : 'text-gray-900';

  return (
    <div>
      <div className={`text-xl font-bold leading-none ${valueColor}`}>{value}</div>
      <div className="mt-0.5 text-xs text-gray-500">{label}</div>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <CheckCircleIcon />
      <p className="mt-3 text-sm font-medium text-gray-700">{title}</p>
      <p className="mt-1 max-w-xs text-xs text-gray-400">{description}</p>
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

function SearchIllustration() {
  return (
    <svg
      width="40"
      height="40"
      viewBox="0 0 40 40"
      fill="none"
      className="text-gray-300"
    >
      <circle cx="18" cy="18" r="12" stroke="currentColor" strokeWidth="2.5" />
      <path d="M27 27l8 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M13 18h10M18 13v10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      className="text-gray-300"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}
