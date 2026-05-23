'use client';

/**
 * Interactive market search for the hero section.
 * Typing a known market filters the gap cards below to that market.
 * Unknown markets get a "get a free report" CTA.
 * Default state shows one gap from several markets to demonstrate breadth.
 */

import { useRef, useState } from 'react';
import Link from 'next/link';
import { sampleGaps } from '../sampleGaps';
import GapCard from '../GapCard';
import { IconArrow } from '../icons';

const MARKETS = ['Workspace tools', 'Product operations', 'Design collaboration', 'Project management'];

const DEFAULT_GAPS = [
  sampleGaps.find((g) => g.company === 'Notion')!,
  sampleGaps.find((g) => g.company === 'Linear')!,
  sampleGaps.find((g) => g.company === 'Figma')!,
];

export default function ProductSearch() {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = MARKETS.filter((p) =>
    query.length > 0 ? p.toLowerCase().includes(query.toLowerCase()) : true
  );
  const noMatch = query.length > 1 && suggestions.length === 0;
  const gaps = selected
    ? sampleGaps.filter((g) => g.market === selected).slice(0, 3)
    : DEFAULT_GAPS;

  function selectMarket(p: string) {
    setSelected(p);
    setQuery(p);
    setOpen(false);
    inputRef.current?.blur();
  }

  function clearSelection() {
    setSelected(null);
    setQuery('');
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  return (
    <div>
      {/* Search row */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative">
          <div className="flex items-center rounded-lg border border-slate-700/60 bg-slate-800/40 focus-within:border-violet-500/50 transition-colors">
            <span className="pl-3 text-slate-600 text-xs shrink-0">↳</span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setSelected(null); setOpen(true); }}
              onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 150)}
              placeholder="Type a market or niche..."
              className="w-52 bg-transparent px-2 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none"
            />
            {(query || selected) && (
              <button
                onClick={clearSelection}
                className="pr-2.5 text-slate-600 hover:text-slate-400 text-sm leading-none"
                aria-label="Clear"
              >
                ×
              </button>
            )}
          </div>

          {/* Dropdown */}
          {open && (
            <div className="absolute top-full left-0 mt-1 z-20 w-full rounded-lg border border-slate-700/60 bg-[#0d1226] py-1 shadow-xl shadow-black/40">
              {suggestions.length > 0 ? (
                suggestions.map((p) => (
                  <button
                    key={p}
                    onMouseDown={() => selectMarket(p)}
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 transition-colors"
                  >
                    <span>{p}</span>
                    <span className="text-[10px] text-slate-700">
                      {sampleGaps.filter((g) => g.market === p).length} gaps
                    </span>
                  </button>
                ))
              ) : (
                <div className="px-3 py-2 text-[11px] text-slate-600">
                  No sample for &ldquo;{query}&rdquo; — we can run a live report
                </div>
              )}
            </div>
          )}
        </div>

        {selected ? (
          <span className="text-[11px] text-slate-700">
            {sampleGaps.filter((g) => g.market === selected).length} gaps found
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-[11px] text-slate-700">
            or try:
            {MARKETS.slice(0, 3).map((p, i) => (
              <span key={p}>
                <button
                  onMouseDown={(e) => { e.preventDefault(); selectMarket(p); }}
                  className="text-slate-600 hover:text-violet-400 transition-colors"
                >
                  {p}
                </button>
                {i < 2 && <span className="text-slate-800 ml-1">·</span>}
              </span>
            ))}
          </span>
        )}
      </div>

      {/* Cards or no-match CTA */}
      {noMatch ? (
        <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 px-5 py-6 text-center">
          <p className="mb-1.5 text-sm font-semibold text-slate-200">
            No sample data for &ldquo;{query}&rdquo;
          </p>
          <p className="mb-4 text-xs text-slate-600">
            We can run a live gap report for any SaaS market within a few days.
          </p>
          <Link
            href="/sources"
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-violet-900/40 transition hover:bg-violet-500"
          >
            Get a free market report for {query}
            <IconArrow />
          </Link>
        </div>
      ) : (
        <>
          <div className="mb-2 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
            <p className="text-xs text-slate-600">
              {selected
                ? `${selected} — gaps surfaced this week`
                : 'Sample output — workspace tools · product ops · design collaboration'}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {gaps.map((gap, i) => (
              <GapCard key={gap.id} gap={gap} dimmed={!selected && i === 2} />
            ))}
          </div>
          {selected && sampleGaps.filter((g) => g.market === selected).length < 3 && (
            <p className="mt-3 text-right text-xs text-slate-700">
              This is a sample — the full {selected} market report covers more gaps →
            </p>
          )}
          {selected && sampleGaps.filter((g) => g.market === selected).length >= 3 && (
            <p className="mt-3 text-right text-xs text-slate-700">
              + 11 more gaps in the full {selected} market report →
            </p>
          )}
          {!selected && (
            <p className="mt-3 text-right text-xs text-slate-700">
              Type a market above to see its gaps →
            </p>
          )}
        </>
      )}
    </div>
  );
}
