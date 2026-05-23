'use client';

/**
 * Wraps the GapCard grid with ambient "recently updated" indicators.
 * One card at a time pulses (border glow + "+N mentions" badge) on a slow loop.
 * Timestamps are relative to a simulated last-updated time.
 * No backend data — purely cosmetic.
 */

import { useEffect, useRef, useState } from 'react';
import GapCard from '../GapCard';
import type { SampleGap } from '../sampleGaps';

// Simulated hours-since-update per card index
const STALE_HOURS = [4, 11, 2, 18, 7, 27];

function formatAge(hours: number): string {
  if (hours < 1) return 'updated just now';
  if (hours < 24) return `updated ${hours}h ago`;
  const d = Math.floor(hours / 24);
  return `updated ${d}d ago`;
}

export default function GapCardPulse({ gaps }: { gaps: SampleGap[] }) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [mentionBonus, setMentionBonus] = useState<number>(0);
  const [staleHours, setStaleHours] = useState(STALE_HOURS);
  const pulseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  useEffect(() => {
    if (reducedMotion) return;

    function triggerPulse() {
      const idx = Math.floor(Math.random() * gaps.length);
      const bonus = Math.random() < 0.5 ? 1 : 2;

      setActiveIdx(idx);
      setMentionBonus(bonus);

      // Update this card's age to "just now" and its stale hours
      setStaleHours((prev) => {
        const next = [...prev];
        next[idx] = 0;
        return next;
      });

      // Clear the pulse after animation completes
      const clear = setTimeout(() => {
        setActiveIdx(null);
        // Slowly age it back so it doesn't stay "just now" forever
        setTimeout(() => {
          setStaleHours((prev) => {
            const next = [...prev];
            next[idx] = 1;
            return next;
          });
        }, 30000);
      }, 3200);

      // Schedule next pulse (8–14 seconds later)
      const nextDelay = 8000 + Math.random() * 6000;
      pulseTimerRef.current = setTimeout(triggerPulse, nextDelay + 3200);

      return () => clearTimeout(clear);
    }

    // Initial delay before first pulse
    pulseTimerRef.current = setTimeout(triggerPulse, 3500);

    return () => {
      if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current);
    };
  }, [gaps.length, reducedMotion]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {gaps.map((gap, i) => {
        const isActive = i === activeIdx;
        return (
          <div
            key={gap.id}
            className="relative"
            style={
              isActive
                ? { animation: 'card-pulse-glow 2.8s ease-in-out' }
                : undefined
            }
          >
            <GapCard gap={gap} />

            {/* Timestamp footer */}
            <div className="mt-1.5 flex items-center justify-between px-1">
              <span className="text-[10px] text-slate-700">
                {formatAge(staleHours[i] ?? STALE_HOURS[i])}
              </span>
              {isActive && (
                <span
                  className="anim-badge-pop rounded-md border border-emerald-500/20 bg-emerald-500/[0.07] px-1.5 py-0.5 text-[10px] font-medium text-emerald-400"
                  style={{ animation: 'badge-pop 3s ease-out forwards' }}
                >
                  +{mentionBonus} mention{mentionBonus > 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
