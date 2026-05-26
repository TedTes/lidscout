'use client';

import { useEffect, useState } from 'react';
import { sampleGaps } from './sampleGaps';

const THEMES_BY_GAP: Record<string, string> = {
  '1': 'Calendar reliability',
  '2': 'Large workspace performance',
  '3': 'Integration reliability',
  '4': 'Executive reporting',
  '5': 'Design system safety',
  '6': 'Capacity planning',
};

export default function EvidenceTrail() {
  const [active, setActive]   = useState(0);
  const [visible, setVisible] = useState(true);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    setReduced(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  useEffect(() => {
    if (reduced) return;
    const t = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setActive((a) => (a + 1) % sampleGaps.length);
        setVisible(true);
      }, 280);
    }, 5500);
    return () => clearInterval(t);
  }, [reduced]);

  const gap = sampleGaps[active];
  const theme = THEMES_BY_GAP[gap.id] ?? 'Recurring pain';

  const fade: React.CSSProperties = {
    opacity: visible ? 1 : 0,
    transform: visible ? 'translateY(0)' : 'translateY(8px)',
    transition: 'opacity 0.28s ease, transform 0.28s ease',
  };

  return (
    <section className="border-t border-slate-800/40 py-20">
      <div className="mx-auto max-w-5xl px-6">
        {/* Header */}
        <div className="mb-12 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-slate-600">
              Evidence first
            </p>
            <h2 className="text-2xl font-bold text-slate-100">
              Every gap has a source you can read
            </h2>
          </div>
          {/* Dot progress */}
          <div className="flex items-center gap-1.5">
            {sampleGaps.map((_, i) => (
              <button
                key={i}
                onClick={() => { setActive(i); setVisible(true); }}
                className="h-1.5 rounded-full transition-all duration-300"
                style={{
                  width: i === active ? 20 : 6,
                  backgroundColor: i === active ? '#8b5cf6' : '#1e293b',
                }}
                aria-label={`Gap ${i + 1}`}
              />
            ))}
          </div>
        </div>

        {/* Narrative flow */}
        <div style={fade} className="grid gap-0 lg:grid-cols-[1fr_1px_1fr_1px_1fr]">

          {/* 1 — Raw quote */}
          <div className="py-2 lg:pr-10">
            <p className="mb-4 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
              Source · {gap.sourceLabel} · {gap.company}
            </p>
            <blockquote className="text-base font-medium leading-relaxed text-slate-500 italic">
              &ldquo;{gap.evidenceQuote}&rdquo;
            </blockquote>
          </div>

          {/* Divider */}
          <div className="hidden lg:block self-stretch w-px bg-gradient-to-b from-transparent via-slate-800 to-transparent" />

          {/* 2 — Theme */}
          <div className="py-8 lg:py-2 lg:px-10">
            <p className="mb-4 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
              Clustered with {gap.mentions - 1} similar signals into
            </p>
            <p className="text-xl font-bold text-slate-400">{theme}</p>
            <p className="mt-3 text-xs leading-relaxed text-slate-600">{gap.painSummary}</p>
          </div>

          {/* Divider */}
          <div className="hidden lg:block self-stretch w-px bg-gradient-to-b from-transparent via-slate-800 to-transparent" />

          {/* 3 — Gap */}
          <div className="py-2 lg:pl-10">
            <p className="mb-4 text-[10px] font-semibold uppercase tracking-widest text-emerald-700">
              Ranked gap · {gap.strength === 'strong' ? 'strong evidence' : 'moderate evidence'}
            </p>
            <p className="text-xl font-bold leading-snug text-slate-300">{gap.title}</p>
            <p className="mt-3 text-xs leading-relaxed text-slate-600">
              <span className="text-slate-500 font-medium">Wedge → </span>
              {gap.suggestedWedge}
            </p>
          </div>
        </div>

        {/* Mobile dividers */}
        <div className="mt-6 border-t border-slate-800/40 pt-4 text-center lg:hidden">
          <span className="text-[11px] text-slate-700">
            {gap.mentions} mentions · {gap.sourceLabel} · {gap.company}
          </span>
        </div>
      </div>
    </section>
  );
}
