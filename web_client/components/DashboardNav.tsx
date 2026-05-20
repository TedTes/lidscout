'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

function IconRadar() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14" />
    </svg>
  );
}

function IconZap() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

function IconFileText() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

function IconPlay() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

const navItems = [
  {
    href: '/signals',
    label: 'Signals',
    matchPrefixes: ['/signals', '/clusters'],
    icon: <IconZap />,
  },
  {
    href: '/reports/latest',
    label: 'Report',
    matchPrefixes: ['/reports'],
    icon: <IconFileText />,
  },
  {
    href: '/pipeline/run',
    label: 'Pipeline',
    matchPrefixes: ['/pipeline'],
    icon: <IconPlay />,
  },
];

export default function DashboardNav() {
  const pathname = usePathname();

  return (
    <>
      {/* ── Desktop sidebar ─────────────────────────────────────── */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[220px] flex-col border-r border-white/[0.06] bg-[#07091a] lg:flex">

        {/* Logo */}
        <div className="flex h-[62px] items-center gap-3 px-5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white shadow-lg shadow-violet-950">
            <IconRadar />
          </div>
          <div>
            <p className="text-[13px] font-bold tracking-tight text-slate-100">LidScout</p>
            <p className="text-[10px] leading-tight text-slate-600">Signal Intelligence</p>
          </div>
        </div>

        <div className="mx-4 h-px bg-white/[0.06]" />

        {/* Nav items */}
        <nav className="mt-5 flex flex-col gap-0.5 px-3">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
            Workspace
          </p>
          {navItems.map(item => {
            const active = item.matchPrefixes.some(
              prefix => pathname === prefix || pathname.startsWith(prefix + '/'),
            );
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  active
                    ? 'bg-violet-600/[0.13] text-violet-300'
                    : 'text-slate-500 hover:bg-white/[0.04] hover:text-slate-300'
                }`}
              >
                <span
                  className={`shrink-0 transition-colors duration-150 ${
                    active ? 'text-violet-400' : 'text-slate-600 group-hover:text-slate-400'
                  }`}
                >
                  {item.icon}
                </span>
                {item.label}
                {active && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_8px_rgba(167,139,250,0.9)]" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom status indicator */}
        <div className="mt-auto px-3 pb-5">
          <div className="rounded-lg border border-white/[0.05] bg-slate-900/60 px-3 py-2.5">
            <div className="flex items-center gap-2.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_7px_rgba(52,211,153,0.8)]" />
              <span className="text-xs font-medium text-slate-600">API online</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Mobile top bar ───────────────────────────────────────── */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-white/[0.06] bg-[#07091a]/95 px-4 backdrop-blur-md lg:hidden">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-600 text-white">
            <IconRadar />
          </div>
          <span className="text-sm font-bold tracking-tight text-slate-100">LidScout</span>
        </div>
        <nav className="flex items-center gap-0.5">
          {navItems.map(item => {
            const active = item.matchPrefixes.some(
              prefix => pathname === prefix || pathname.startsWith(prefix + '/'),
            );
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  active
                    ? 'bg-violet-600/15 text-violet-300'
                    : 'text-slate-500 hover:text-slate-200'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
    </>
  );
}
