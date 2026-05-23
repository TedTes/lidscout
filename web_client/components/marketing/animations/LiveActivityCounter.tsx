'use client';

/**
 * Simulates a live pipeline activity counter.
 * Numbers are deterministic from wall-clock time so every visitor sees
 * a plausible "current" value. localStorage persists the session baseline
 * so revisits don't reset to zero. No backend connection.
 *
 * Counts are initialised entirely in useEffect (client-only) to avoid
 * SSR/hydration mismatches — Date.now() on the server and on the client
 * will always differ by at least a few milliseconds.
 */

import { useEffect, useRef, useState } from 'react';

const RATES = {
  scanned: 0.14,
  filtered: 0.10,
  signals: 0.022,
  gaps: 0.0033,
};

function weekBaseline() {
  const nowSec = Date.now() / 1000;
  const secPerWeek = 7 * 24 * 3600;
  const weekStart = Math.floor(nowSec / secPerWeek) * secPerWeek;
  const elapsed = nowSec - weekStart;
  return {
    scanned:  Math.floor(800  + elapsed * RATES.scanned),
    filtered: Math.floor(580  + elapsed * RATES.filtered),
    signals:  Math.floor(12   + elapsed * RATES.signals),
    gaps:     Math.floor(2    + elapsed * RATES.gaps),
  };
}

function lsGet(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? Number(v) : fallback;
  } catch { return fallback; }
}

function lsSet(key: string, val: number) {
  try { localStorage.setItem(key, String(val)); } catch {}
}

type Counts = { scanned: number; filtered: number; signals: number; gaps: number };

export default function LiveActivityCounter() {
  // null = not yet mounted; avoids any SSR render of time-dependent numbers
  const [counts, setCounts] = useState<Counts | null>(null);
  const [ticking, setTicking] = useState<keyof Counts | null>(null);
  const tickRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const base = weekBaseline();
    const initial: Counts = {
      scanned:  Math.max(lsGet('ls_scanned',  base.scanned),  base.scanned),
      filtered: Math.max(lsGet('ls_filtered', base.filtered), base.filtered),
      signals:  Math.max(lsGet('ls_signals',  base.signals),  base.signals),
      gaps:     Math.max(lsGet('ls_gaps',     base.gaps),     base.gaps),
    };
    setCounts(initial);

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;

    const schedule: Array<{ key: keyof Counts; minMs: number; maxMs: number }> = [
      { key: 'scanned',  minMs: 4000,  maxMs: 9000   },
      { key: 'filtered', minMs: 6000,  maxMs: 12000  },
      { key: 'signals',  minMs: 30000, maxMs: 60000  },
      { key: 'gaps',     minMs: 90000, maxMs: 240000 },
    ];

    const timers: ReturnType<typeof setTimeout>[] = [];

    function scheduleNext(entry: typeof schedule[number]) {
      const delay = entry.minMs + Math.random() * (entry.maxMs - entry.minMs);
      const t = setTimeout(() => {
        setCounts((c) => {
          if (!c) return c;
          const next = { ...c, [entry.key]: c[entry.key] + 1 };
          lsSet(`ls_${entry.key}`, next[entry.key]);
          return next;
        });
        setTicking(entry.key);
        if (tickRef.current) clearTimeout(tickRef.current);
        tickRef.current = setTimeout(() => setTicking(null), 600);
        scheduleNext(entry);
      }, delay);
      timers.push(t);
    }

    schedule.forEach(scheduleNext);
    return () => { timers.forEach(clearTimeout); };
  }, []);

  // Render nothing on the server / before mount — no hydration mismatch possible
  if (!counts) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-600">
      <span className="flex items-center gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_5px_rgba(52,211,153,0.7)]" />
        <span className="font-medium text-slate-500">Live</span>
      </span>
      <span className="text-slate-700">·</span>
      <StatItem label="posts scanned"   value={counts.scanned}  active={ticking === 'scanned'}  />
      <span className="text-slate-700">·</span>
      <StatItem label="filtered as noise" value={counts.filtered} active={ticking === 'filtered'} />
      <span className="text-slate-700">·</span>
      <StatItem label="new signals"     value={counts.signals}  active={ticking === 'signals'}  />
      <span className="text-slate-700">·</span>
      <StatItem label="new gaps"        value={counts.gaps}     active={ticking === 'gaps'}     />
    </div>
  );
}

function StatItem({ label, value, active }: { label: string; value: number; active: boolean }) {
  return (
    <span>
      <span
        className="anim-counter-tick inline-block tabular-nums"
        style={active ? { animation: 'counter-tick 0.45s ease-in-out' } : undefined}
      >
        {value.toLocaleString()}
      </span>
      {' '}{label}
    </span>
  );
}
