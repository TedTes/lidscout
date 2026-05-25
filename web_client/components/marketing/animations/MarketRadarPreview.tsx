'use client';

import { useEffect, useMemo, useState } from 'react';
import { sampleGaps } from '../sampleGaps';

const MARKETS = [
  {
    name: 'Workspace tools',
    companies: ['Notion', 'Linear', 'Figma', 'Asana'],
    sources: 23, findings: 147, themes: 12, gaps: 4,
  },
  {
    name: 'AI devtools',
    companies: ['Cursor', 'Replit', 'Vercel', 'GitHub'],
    sources: 18, findings: 96, themes: 9, gaps: 3,
  },
  {
    name: 'CRM tools',
    companies: ['HubSpot', 'Pipedrive', 'Attio', 'Salesforce'],
    sources: 31, findings: 182, themes: 16, gaps: 5,
  },
];

const THEME_BY_GAP: Record<string, string> = {
  '1': 'Calendar reliability',
  '2': 'Workspace performance',
  '3': 'Integration limits',
  '4': 'Executive reporting',
  '5': 'Design safety',
  '6': 'Capacity planning',
};

const EVIDENCE_STEPS = ['Quote', 'Finding', 'Theme', 'Gap'] as const;

export default function MarketRadarPreview() {
  const [marketIndex, setMarketIndex]   = useState(0);
  const [visible, setVisible]           = useState(true);
  const [activeStep, setActiveStep]     = useState(0);
  const [activeSnippet, setActiveSnippet] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  const market = MARKETS[marketIndex];
  const marketGaps = useMemo(() => {
    const matching = sampleGaps.filter((g) => g.market === market.name);
    return matching.length > 0 ? matching : sampleGaps;
  }, [market.name]);
  const gap = marketGaps[0];

  // Market rotation with crossfade
  useEffect(() => {
    if (reducedMotion) return;
    const timer = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setMarketIndex((i) => (i + 1) % MARKETS.length);
        setActiveStep(0);
        setActiveSnippet(0);
        setVisible(true);
      }, 220);
    }, 6500);
    return () => clearInterval(timer);
  }, [reducedMotion]);

  // Evidence path: advance one step at a time (~1.3s each), reset when market changes
  useEffect(() => {
    setActiveStep(0);
  }, [marketIndex]);

  useEffect(() => {
    if (reducedMotion || activeStep >= EVIDENCE_STEPS.length - 1) return;
    const t = setTimeout(() => setActiveStep((s) => s + 1), 1300);
    return () => clearTimeout(t);
  }, [activeStep, reducedMotion]);

  // Evidence snippets alternate which one glows
  useEffect(() => {
    if (reducedMotion) return;
    const timer = setInterval(() => setActiveSnippet((s) => (s + 1) % 2), 2800);
    return () => clearInterval(timer);
  }, [reducedMotion]);

  const fadeStyle: React.CSSProperties = {
    opacity: visible ? 1 : 0,
    transform: visible ? 'translateY(0)' : 'translateY(5px)',
    transition: 'opacity 0.22s ease, transform 0.22s ease',
  };

  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-900/40 p-4 shadow-2xl shadow-black/30">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between gap-4">
        <div style={fadeStyle}>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
            Niche radar
          </p>
          <h2 className="text-lg font-bold text-slate-100">{market.name}</h2>
        </div>
        <LiveScanBadge reduced={reducedMotion} />
      </div>

      {/* Company chips */}
      <div className="mb-4 flex flex-wrap gap-1.5" style={fadeStyle}>
        {market.companies.map((c) => (
          <span key={c} className="rounded-md bg-slate-800/60 px-2 py-1 text-[11px] text-slate-400">
            {c}
          </span>
        ))}
      </div>

      {/* Metrics — key forces remount → re-triggers count-flash animation */}
      <div className="mb-4 grid grid-cols-4 gap-2">
        <Metric key={`${marketIndex}-s`} label="sources"  value={market.sources}  />
        <Metric key={`${marketIndex}-f`} label="findings" value={market.findings} />
        <Metric key={`${marketIndex}-t`} label="themes"   value={market.themes}   />
        <Metric key={`${marketIndex}-g`} label="gaps"     value={market.gaps}     highlight />
      </div>

      {/* Gap card */}
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.04] p-4" style={fadeStyle}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="rounded-md border border-emerald-500/20 bg-emerald-500/[0.07] px-2 py-0.5 text-[11px] font-medium text-emerald-400">
            {gap.strength === 'strong' ? 'Strong evidence' : 'Moderate evidence'}
          </span>
          <span className="text-[11px] tabular-nums text-slate-600">{gap.mentions} mentions</span>
        </div>
        <h3 className="mb-2 text-base font-semibold leading-snug text-slate-100">{gap.title}</h3>
        <p className="mb-3 line-clamp-2 text-xs leading-relaxed text-slate-500">{gap.painSummary}</p>

        <div className="grid gap-2 sm:grid-cols-2">
          <EvidenceSnippet
            quote={gap.evidenceQuote}
            source={gap.sourceLabel}
            label={gap.company}
            active={activeSnippet === 0}
          />
          <EvidenceSnippet
            quote={gap.suggestedWedge}
            source={THEME_BY_GAP[gap.id] ?? 'Recurring theme'}
            label="Suggested wedge"
            active={activeSnippet === 1}
          />
        </div>

        {/* Evidence path progress */}
        <div className="mt-4 flex flex-wrap items-center gap-1.5 text-[11px]">
          {EVIDENCE_STEPS.map((step, i) => (
            <span key={step} className="flex items-center gap-1.5">
              <span
                className="transition-colors duration-500"
                style={{
                  color:
                    i < activeStep  ? '#475569' :  // passed: slate-600
                    i === activeStep ? '#a78bfa' :  // active: violet-400
                    '#1e293b',                       // future: slate-800
                  fontWeight: i === activeStep ? 600 : 400,
                }}
              >
                {step}
              </span>
              {i < EVIDENCE_STEPS.length - 1 && (
                <span
                  className="transition-colors duration-500"
                  style={{ color: i < activeStep ? '#334155' : '#0f172a' }}
                >
                  →
                </span>
              )}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function LiveScanBadge({ reduced }: { reduced: boolean }) {
  return (
    <span className="flex shrink-0 items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-500/[0.06] px-2 py-1 text-[11px] font-semibold text-emerald-400">
      <span className="relative flex h-1.5 w-1.5">
        {!reduced && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
        )}
        <span className="relative h-1.5 w-1.5 rounded-full bg-emerald-400" />
      </span>
      Live scan
    </span>
  );
}

function Metric({
  label, value, highlight = false,
}: {
  label: string; value: number; highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-2 py-2 ${
        highlight ? 'border-violet-500/20 bg-violet-500/[0.06]' : 'border-slate-800/60 bg-slate-950/25'
      }`}
    >
      <p
        className={`text-sm font-bold tabular-nums ${highlight ? 'text-violet-300' : 'text-slate-200'}`}
        style={{ animation: 'count-flash 0.5s ease' }}
      >
        {value}
      </p>
      <p className="text-[10px] text-slate-700">{label}</p>
    </div>
  );
}

function EvidenceSnippet({
  quote, source, label, active,
}: {
  quote: string; source: string; label: string; active: boolean;
}) {
  return (
    <div
      className="rounded-lg bg-slate-950/30 p-3 transition-all duration-500"
      style={{
        border: `1px solid ${active ? 'rgba(139,92,246,0.25)' : 'rgba(30,41,59,0.5)'}`,
      }}
    >
      <p className="mb-2 line-clamp-3 text-xs italic leading-relaxed text-slate-500">
        &ldquo;{quote}&rdquo;
      </p>
      <div className="flex items-center justify-between gap-2 text-[10px]">
        <span className="flex items-center gap-1 text-slate-700">
          <span
            className="h-1 w-1 rounded-full bg-violet-400 transition-opacity duration-500"
            style={{ opacity: active ? 0.8 : 0 }}
          />
          {source}
        </span>
        <span className="rounded bg-slate-800/70 px-1.5 py-0.5 text-slate-500">{label}</span>
      </div>
    </div>
  );
}
