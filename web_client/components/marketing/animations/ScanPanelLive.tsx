'use client';

/**
 * Animated version of the "Today's scan" panel in HowItWorks.
 * One source row at a time briefly highlights as if currently being scanned
 * and its post count increments. Pure simulation — no backend connection.
 */

import { useEffect, useRef, useState } from 'react';

type Row = { text: string; kept: number; filtered: number };

const INITIAL_ROWS: Row[] = [
  { text: 'r/Notion',    kept: 4,  filtered: 20 },
  { text: 'G2',          kept: 3,  filtered: 0  },
  { text: 'Hacker News', kept: 1,  filtered: 7  },
];

export default function ScanPanelLive() {
  const [rows, setRows] = useState<Row[]>(INITIAL_ROWS);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  useEffect(() => {
    if (reducedMotion) return;

    let idx = 0;

    function scan() {
      const current = idx % INITIAL_ROWS.length;
      idx++;

      setActiveIdx(current);

      // Increment the scanned count and occasionally the kept/filtered
      setRows((prev) => {
        const next = prev.map((r, i) => {
          if (i !== current) return r;
          const newFiltered = r.filtered + 1;
          // Every 5th increment also bumps kept
          const newKept = newFiltered % 5 === 0 ? r.kept + 1 : r.kept;
          return { ...r, filtered: newFiltered, kept: newKept };
        });
        return next;
      });

      // Clear highlight after animation duration
      const clearTimer = setTimeout(() => setActiveIdx(null), 2000);

      // Next scan: 5–8 seconds
      const nextDelay = 5000 + Math.random() * 3000;
      timerRef.current = setTimeout(scan, nextDelay);

      return () => clearTimeout(clearTimer);
    }

    // Start after a short delay so the user has time to see the static state first
    timerRef.current = setTimeout(scan, 2000);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [reducedMotion]);

  return (
    <div className="rounded-xl border border-slate-800/50 bg-[#0a0c1e] p-4 text-xs space-y-2">
      <p className="text-slate-700 text-[10px] uppercase tracking-wider mb-3">
        Today&apos;s scan — Notion
      </p>
      {rows.map((row, i) => {
        const isActive = i === activeIdx;
        return (
          <div
            key={row.text}
            className="flex items-center justify-between rounded-lg border border-slate-800/40 px-3 py-2 transition-colors"
            style={
              isActive
                ? { animation: 'scan-row-flash 2s ease-in-out' }
                : undefined
            }
          >
            <span className="flex items-center gap-2 text-slate-500">
              {isActive && (
                <span className="h-1.5 w-1.5 rounded-full bg-violet-500 shadow-[0_0_4px_rgba(139,92,246,0.7)] shrink-0" />
              )}
              {row.text}
            </span>
            <div className="flex items-center gap-2 tabular-nums">
              <span className="text-emerald-600">{row.kept} kept</span>
              <span className="text-slate-700">{row.filtered} filtered</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
