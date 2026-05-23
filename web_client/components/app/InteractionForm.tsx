'use client';

import { useState } from 'react';
import { InteractionExtractionRequest, PageSourceInput } from '@/lib/types/interaction';

interface Props {
  onExtract: (request: InteractionExtractionRequest) => void;
  isLoading: boolean;
}

const SAMPLE_TEXT = `Pros: The scheduling view is useful once everything is configured.
Cons: It is expensive for a small team, setup was confusing, and reporting is limited.
Overall: Support was slow to respond when our mobile app sync stopped working.`;

export default function InteractionForm({ onExtract, isLoading }: Props) {
  const [mode, setMode] = useState<'url' | 'text'>('url');
  const [urls, setUrls] = useState<string[]>(['']);
  const [text, setText] = useState('');

  const updateUrl = (i: number, value: string) =>
    setUrls(curr => curr.map((u, j) => (j === i ? value : u)));

  const addUrl = () => setUrls(curr => [...curr, '']);
  const removeUrl = (i: number) => setUrls(curr => curr.filter((_, j) => j !== i));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    let sources: PageSourceInput[];

    if (mode === 'url') {
      sources = urls
        .map(u => u.trim())
        .filter(Boolean)
        .map(url => ({ source_type: 'url' as const, url }));
    } else {
      const trimmed = text.trim();
      if (!trimmed) return;
      sources = [{ source_type: 'text' as const, text: trimmed }];
    }

    if (!sources.length) return;
    onExtract({ sources });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {mode === 'url' ? (
        <>
          <div className="space-y-2">
            {urls.map((url, i) => (
              <div key={i} className="flex gap-2">
                <div className="relative flex-1">
                  <LinkIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="url"
                    value={url}
                    onChange={e => updateUrl(i, e.target.value)}
                    placeholder="https://example.com/page"
                    className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-8 pr-3 text-sm text-gray-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:bg-gray-50 disabled:text-gray-400"
                    disabled={isLoading}
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                    autoFocus={i === 0}
                  />
                </div>
                {urls.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeUrl(i)}
                    aria-label="Remove URL"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-gray-400 transition hover:border-red-200 hover:text-red-500 disabled:opacity-40"
                    disabled={isLoading}
                  >
                    <XIcon />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              {urls.length < 10 && (
                <button
                  type="button"
                  onClick={addUrl}
                  className="text-sky-700 hover:underline disabled:opacity-50"
                  disabled={isLoading}
                >
                  + Add another URL
                </button>
              )}
              <button
                type="button"
                onClick={() => setMode('text')}
                className="text-gray-400 hover:text-gray-600"
                disabled={isLoading}
              >
                Paste text instead
              </button>
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="shrink-0 rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? 'Extracting…' : 'Extract'}
            </button>
          </div>
        </>
      ) : (
        <>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Paste page text, comments, or any public content here."
            rows={8}
            className="w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:bg-gray-50"
            disabled={isLoading}
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus
          />
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <button
                type="button"
                onClick={() => setMode('url')}
                className="text-gray-400 hover:text-gray-600"
                disabled={isLoading}
              >
                Use a URL instead
              </button>
              <button
                type="button"
                onClick={() => setText(SAMPLE_TEXT)}
                className="text-sky-700 hover:underline disabled:opacity-50"
                disabled={isLoading}
              >
                Load sample
              </button>
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="shrink-0 rounded-lg bg-sky-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? 'Extracting…' : 'Extract'}
            </button>
          </div>
        </>
      )}
    </form>
  );
}

function LinkIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
