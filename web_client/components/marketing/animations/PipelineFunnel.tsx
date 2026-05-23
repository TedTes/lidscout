'use client';

/**
 * Ambient pipeline funnel visualization.
 * Canvas particles flow top→bottom, narrowing at each filter stage.
 * Particles whose random lane exceeds a stage's threshold fade out there.
 * Survivors reaching the bottom represent a surfaced gap (briefly turn emerald).
 * All numbers are simulated — no backend data.
 */

import { useEffect, useRef, useState } from 'react';

const W = 220;
const H = 360;
const CX = W / 2;

// Gates: y-fraction where filter happens, and the surviving lane half-width (0–1)
const GATES = [
  { yFrac: 0.26, halfFrac: 0.72, label: 'Posts fetched',  color: '#475569' },
  { yFrac: 0.46, halfFrac: 0.38, label: 'Rule filter',    color: '#475569' },
  { yFrac: 0.64, halfFrac: 0.18, label: 'LLM filter',     color: '#6d28d9' },
  { yFrac: 0.80, halfFrac: 0.07, label: 'Clustered',      color: '#7c3aed' },
  { yFrac: 0.95, halfFrac: 0.03, label: 'Gap surfaced',   color: '#10b981' },
];

// How wide the funnel mouth is at each gate (pixels from centre)
function halfWidthAt(y: number): number {
  const frac = y / H;
  // Piecewise linear between gate thresholds
  for (let i = 0; i < GATES.length - 1; i++) {
    const a = GATES[i], b = GATES[i + 1];
    if (frac >= a.yFrac && frac <= b.yFrac) {
      const t = (frac - a.yFrac) / (b.yFrac - a.yFrac);
      return (a.halfFrac + (b.halfFrac - a.halfFrac) * t) * (W / 2 - 10);
    }
  }
  if (frac < GATES[0].yFrac) return (W / 2 - 10);
  return GATES[GATES.length - 1].halfFrac * (W / 2 - 10);
}

type Particle = {
  lane: number;   // −1 to 1, random at spawn; determines which gates it survives
  y: number;
  speed: number;
  opacity: number;
  dying: boolean;
  diedAt: number; // the gate y where it was filtered out
  gap: boolean;   // turned emerald at the bottom
};

function spawnParticle(): Particle {
  return {
    lane: (Math.random() * 2 - 1),
    y: -4 - Math.random() * 20,
    speed: 0.55 + Math.random() * 0.45,
    opacity: 0.55 + Math.random() * 0.45,
    dying: false,
    diedAt: 0,
    gap: false,
  };
}

export default function PipelineFunnel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Evaluate after mount to avoid SSR/hydration mismatch
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }, []);

  // Incrementing stage counters shown as overlays
  const [stageCounts, setStageCounts] = useState([1247, 891, 312, 47, 3]);

  useEffect(() => {
    if (reducedMotion) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const particles: Particle[] = [];
    let rafId: number;
    let frameCount = 0;

    // Spawn initial batch
    for (let i = 0; i < 28; i++) {
      const p = spawnParticle();
      p.y = Math.random() * H; // spread them across canvas at start
      particles.push(p);
    }

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, W, H);

      // Draw funnel outline
      ctx.beginPath();
      ctx.moveTo(10, 0);
      GATES.forEach((g) => {
        const y = g.yFrac * H;
        const hw = g.halfFrac * (W / 2 - 10);
        ctx.lineTo(CX - hw, y);
      });
      GATES.slice().reverse().forEach((g) => {
        const y = g.yFrac * H;
        const hw = g.halfFrac * (W / 2 - 10);
        ctx.lineTo(CX + hw, y);
      });
      ctx.lineTo(W - 10, 0);
      ctx.closePath();
      ctx.fillStyle = 'rgba(139,92,246,0.025)';
      ctx.fill();

      // Draw gate lines
      GATES.forEach((g, i) => {
        const y = g.yFrac * H;
        const hw = g.halfFrac * (W / 2 - 10);
        ctx.beginPath();
        ctx.moveTo(CX - hw, y);
        ctx.lineTo(CX + hw, y);
        ctx.strokeStyle = i === GATES.length - 1
          ? 'rgba(16,185,129,0.25)'
          : 'rgba(139,92,246,0.18)';
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Update and draw particles
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];

        if (!p.dying) {
          p.y += p.speed;

          // Check each gate crossing
          for (const g of GATES) {
            const gy = g.yFrac * H;
            if (p.y > gy && p.y - p.speed <= gy) {
              if (Math.abs(p.lane) > g.halfFrac) {
                p.dying = true;
                p.diedAt = gy;
                break;
              }
              // Last gate: survivor becomes a gap
              if (g === GATES[GATES.length - 1]) {
                p.gap = true;
              }
            }
          }
        } else {
          p.opacity -= 0.025;
        }

        // Remove when done
        if (p.opacity <= 0 || p.y > H + 10) {
          particles.splice(i, 1);
          continue;
        }

        const x = CX + p.lane * halfWidthAt(p.y);
        const r = p.gap ? 2.2 : 1.4;

        ctx.beginPath();
        ctx.arc(x, p.y, r, 0, Math.PI * 2);

        if (p.gap) {
          ctx.fillStyle = `rgba(16,185,129,${p.opacity * 0.9})`;
          // soft glow for gaps
          ctx.shadowColor = 'rgba(16,185,129,0.5)';
          ctx.shadowBlur = 6;
        } else if (p.y > GATES[2].yFrac * H) {
          ctx.fillStyle = `rgba(139,92,246,${p.opacity * 0.85})`;
          ctx.shadowBlur = 0;
        } else {
          ctx.fillStyle = `rgba(100,116,139,${p.opacity * 0.6})`;
          ctx.shadowBlur = 0;
        }
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Spawn new particles periodically
      frameCount++;
      if (frameCount % 18 === 0 && particles.length < 55) {
        particles.push(spawnParticle());
      }

      rafId = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(rafId);
  }, [reducedMotion]);

  // Slowly increment stage counters
  useEffect(() => {
    if (reducedMotion) return;
    const intervals = [
      setInterval(() => setStageCounts((c) => { const n=[...c]; n[0]++; return n; }), 6500),
      setInterval(() => setStageCounts((c) => { const n=[...c]; n[1]++; return n; }), 9000),
      setInterval(() => setStageCounts((c) => { const n=[...c]; n[2]++; return n; }), 18000),
      setInterval(() => setStageCounts((c) => { const n=[...c]; n[3]++; return n; }), 55000),
      setInterval(() => setStageCounts((c) => { const n=[...c]; n[4]++; return n; }), 300000),
    ];
    return () => intervals.forEach(clearInterval);
  }, [reducedMotion]);

  return (
    <div className="relative hidden lg:flex flex-col items-center select-none" style={{ width: W, minHeight: H }}>
      {/* Stage labels — overlaid left of canvas */}
      <div className="absolute inset-0 pointer-events-none">
        {GATES.map((g, i) => (
          <div
            key={i}
            className="absolute right-full pr-3 flex flex-col items-end"
            style={{ top: g.yFrac * H - 9 }}
          >
            <span className="text-[9px] uppercase tracking-widest text-slate-700 whitespace-nowrap">
              {g.label}
            </span>
            <span
              className="tabular-nums text-[10px] font-semibold"
              style={{ color: i === GATES.length - 1 ? '#10b981' : '#6d28d9' }}
            >
              {stageCounts[i].toLocaleString()}
            </span>
          </div>
        ))}
      </div>

      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        className="opacity-90"
        aria-hidden="true"
      />

      {/* Static fallback for reduced-motion */}
      {reducedMotion && (
        <div className="flex flex-col gap-3 px-2 py-4 text-[10px] text-slate-600">
          {GATES.map((g, i) => (
            <div key={i} className="flex justify-between gap-4">
              <span>{g.label}</span>
              <span className="tabular-nums text-slate-500">{stageCounts[i].toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
