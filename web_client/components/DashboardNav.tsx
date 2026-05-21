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

function IconActivity() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function IconTerminal() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
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
    href: '/sources',
    label: 'Sources',
    matchPrefixes: ['/sources'],
    icon: <IconActivity />,
  },
];

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

        {/* Main nav */}
        <nav className="mt-5 flex flex-col gap-0.5 px-3">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
            Workspace
          </p>
          {navItems.map(item => (
            <NavLink key={item.href} {...item} pathname={pathname} />
          ))}
        </nav>

        {/* System / admin section */}
        <div className="mt-auto px-3 pb-2">
          <div className="mb-2 h-px bg-white/[0.04]" />
          <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-800">
            System
          </p>
          <NavLink
            href="/pipeline/run"
            matchPrefixes={['/pipeline']}
            icon={<IconTerminal />}
            label="Pipeline trigger"
            pathname={pathname}
            muted
          />
        </div>

        {/* API status */}
        <div className="px-3 pb-5 pt-2">
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
