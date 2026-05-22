'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { signalApi } from '@/lib/api';
import { Competitor } from '@/lib/types/signals';

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconRadar() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14" />
    </svg>
  );
}

function IconTarget() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function IconLayers() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
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

function IconActivity() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function IconCaret() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// ── Nav items ─────────────────────────────────────────────────────────────────

const navItems = [
  {
    href: '/gaps',
    label: 'Gaps',
    matchPrefixes: ['/gaps'],
    icon: <IconTarget />,
  },
  {
    href: '/themes',
    label: 'Themes',
    matchPrefixes: ['/themes', '/clusters'],
    icon: <IconLayers />,
  },
  {
    href: '/findings',
    label: 'Findings',
    matchPrefixes: ['/findings', '/signals'],
    icon: <IconZap />,
  },
  {
    href: '/reports/latest',
    label: 'Reports',
    matchPrefixes: ['/reports'],
    icon: <IconFileText />,
  },
  {
    href: '/sources',
    label: 'Sources',
    matchPrefixes: ['/sources'],
    icon: <IconActivity />,
  },
];

// ── Company selector ──────────────────────────────────────────────────────────

function CompanySelector() {
  const [companies, setCompanies] = useState<Competitor[]>([]);
  const [selected, setSelected] = useState<Competitor | null>(null);
  const [open, setOpen] = useState(false);
  const dropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    signalApi.getCompetitors()
      .then(r => setCompanies(r.competitors))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={dropRef} className="relative mx-3 mb-3">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center gap-2 rounded-lg border border-slate-800/60 bg-slate-900/40 px-3 py-2 text-left text-xs transition hover:border-slate-700/60 hover:bg-slate-800/40"
      >
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${selected ? 'bg-violet-500' : 'bg-slate-700'}`}
        />
        <span className="flex-1 truncate font-medium text-slate-400">
          {selected ? selected.name : 'All companies'}
        </span>
        <span className={`shrink-0 text-slate-700 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}>
          <IconCaret />
        </span>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-full overflow-hidden rounded-lg border border-slate-700/60 bg-[#0b0e24] py-1 shadow-xl shadow-black/50">
          <button
            onClick={() => { setSelected(null); setOpen(false); }}
            className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition hover:bg-white/[0.04] ${!selected ? 'text-violet-300' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${!selected ? 'bg-violet-400' : 'bg-slate-800'}`} />
            All companies
          </button>

          {companies.length > 0 && <div className="mx-2 my-1 h-px bg-slate-800/60" />}

          {companies.map(c => (
            <button
              key={c.id}
              onClick={() => { setSelected(c); setOpen(false); }}
              className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition hover:bg-white/[0.04] ${selected?.id === c.id ? 'text-violet-300' : 'text-slate-500 hover:text-slate-300'}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${selected?.id === c.id ? 'bg-violet-400' : 'bg-slate-700'}`} />
              <span className="flex-1 truncate">{c.name}</span>
              {c.category && (
                <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[9px] text-slate-600">
                  {c.category}
                </span>
              )}
            </button>
          ))}

          <div className="mx-2 my-1 h-px bg-slate-800/60" />
          <Link
            href="/sources"
            onClick={() => setOpen(false)}
            className="flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-xs text-slate-700 transition hover:text-slate-500"
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add company
          </Link>
        </div>
      )}
    </div>
  );
}

// ── NavLink ───────────────────────────────────────────────────────────────────

function NavLink({
  href,
  matchPrefixes,
  icon,
  label,
  pathname,
  muted,
}: {
  href: string;
  matchPrefixes: string[];
  icon: React.ReactNode;
  label: string;
  pathname: string;
  muted?: boolean;
}) {
  const active = matchPrefixes.some(
    prefix => pathname === prefix || pathname.startsWith(prefix + '/'),
  );

  if (muted) {
    return (
      <Link
        href={href}
        className={`group flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-all duration-150 ${
          active
            ? 'bg-slate-800/60 text-slate-400'
            : 'text-slate-700 hover:bg-white/[0.03] hover:text-slate-500'
        }`}
      >
        <span className={`shrink-0 transition-colors duration-150 ${active ? 'text-slate-500' : 'text-slate-700 group-hover:text-slate-600'}`}>
          {icon}
        </span>
        {label}
      </Link>
    );
  }

  return (
    <Link
      href={href}
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
        {icon}
      </span>
      {label}
      {active && (
        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_8px_rgba(167,139,250,0.9)]" />
      )}
    </Link>
  );
}

// ── DashboardNav ──────────────────────────────────────────────────────────────

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
            <p className="text-[10px] leading-tight text-slate-600">Competitor pain intelligence</p>
          </div>
        </div>

        <div className="mx-4 h-px bg-white/[0.06]" />

        {/* Company selector */}
        <div className="mt-3">
          <CompanySelector />
        </div>

        {/* Main nav */}
        <nav className="flex flex-col gap-0.5 px-3">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
            Workspace
          </p>
          {navItems.map(item => (
            <NavLink key={item.href} {...item} pathname={pathname} />
          ))}
        </nav>

        {/* API status */}
        <div className="mt-auto px-3 pb-5 pt-2">
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
