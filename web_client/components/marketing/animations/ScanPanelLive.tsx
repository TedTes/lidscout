'use client';

/**
 * Animated scan panel for HowItWorks.
 * Cycles through source rows, showing a "checking" phase before updating counts.
 * The indicator dot is always rendered (opacity toggled) to avoid layout shift.
 * No backend connection — purely simulated.
 */

import { useEffect, useRef, useState } from 'react';

type Row = { text: string; kept: number; filtered: number };

const INITIAL_ROWS: Row[] = [
  { text: 'Reddit searches', kept: 4,  filtered: 20 },
  { text: 'Review pages',    kept: 3,  filtered: 8  },
  { text: 'HN + changelogs', kept: 1,  filtered: 7  },
];

export default function ScanPanelLive() {
  const [rows, setRows]             = useState<Row[]>(INITIAL_ROWS);
  const [scanningIdx, setScanningIdx] = useState<number | null>(null); // checking phase
  const [doneIdx, setDoneIdx]       = useState<number | null>(null);   // briefly after update
  const timerRef                    = useRef<ReturnType<typeof setTimeout> | null>(null);
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

      // Phase 1: highlight row as "checking"
      setScanningIdx(current);
      setDoneIdx(null);

      // Phase 2: after 900ms, update counts and show "done" briefly
      const updateTimer = setTimeout(() => {
        setRows((prev) =>
          prev.map((r, i) => {
            if (i !== current) return r;
            const newFiltered = r.filtered + 1;
            const newKept = newFiltered % 5 === 0 ? r.kept + 1 : r.kept;
            return { ...r, filtered: newFiltered, kept: newKept };
          })
        );
        setScanningIdx(null);
        setDoneIdx(current);

        // Phase 3: clear done state after 1.2s
        setTimeout(() => setDoneIdx(null), 1200);
      }, 900);

      // Schedule next scan: 5–7s after this one starts
      const nextDelay = 5000 + Math.random() * 2000;
      timerRef.current = setTimeout(scan, nextDelay);

      return () => clearTimeout(updateTimer);
    }

    timerRef.current = setTimeout(scan, 1800);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [reducedMotion]);

  return (
    <div className="rounded-xl border border-slate-800/50 bg-[#0a0c1e] p-4 text-xs">
      <p className="mb-3 text-[10px] uppercase tracking-wider text-slate-700">
        Today&apos;s scan — Workspace tools
      </p>
      <div className="space-y-2">
        {rows.map((row, i) => {
          const isScanning = i === scanningIdx;
          const isDone     = i === doneIdx;
          return (
            <div
              key={row.text}
              className="flex items-center justify-between rounded-lg border border-slate-800/40 px-3 py-2"
              style={{
                backgroundColor: isScanning
                  ? 'rgba(139,92,246,0.06)'
                  : isDone
                  ? 'rgba(16,185,129,0.04)'
                  : 'transparent',
                transition: 'background-color 0.4s ease',
              }}
            >
              {/* Left: dot + label */}
              <span className="flex items-center gap-2 text-slate-500">
                {/* Always-rendered dot — opacity toggles to avoid layout shift */}
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full transition-all duration-300"
                  style={{
                    opacity: isScanning ? 1 : isDone ? 0.5 : 0,
                    backgroundColor: isScanning ? '#8b5cf6' : '#10b981',
                    boxShadow: isScanning
                      ? '0 0 5px rgba(139,92,246,0.7)'
                      : isDone
                      ? '0 0 4px rgba(16,185,129,0.5)'
                      : 'none',
                  }}
                />
                <span
                  style={{
                    color: isScanning ? '#94a3b8' : isDone ? '#64748b' : '#64748b',
                    transition: 'color 0.3s ease',
                  }}
                >
                  {row.text}
                </span>
              </span>

              {/* Right: counts or checking indicator */}
              <div className="flex items-center gap-2 tabular-nums">
                {isScanning ? (
                  <span className="text-slate-700 italic">checking…</span>
                ) : (
                  <>
                    <span
                      className="text-emerald-600 transition-colors duration-300"
                      style={isDone ? { color: '#34d399' } : undefined}
                    >
                      {row.kept} kept
                    </span>
                    <span className="text-slate-700">{row.filtered} filtered</span>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
