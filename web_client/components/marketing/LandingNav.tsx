import Link from 'next/link';
import { IconRadar, IconArrow } from './icons';

export default function LandingNav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#07091a]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-600 text-white shadow-lg shadow-violet-950">
            <IconRadar />
          </div>
          <span className="text-sm font-bold tracking-tight text-slate-100">LidScout</span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="px-3 py-2 text-xs font-semibold text-slate-400 transition hover:text-slate-200"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-violet-900/50 transition hover:bg-violet-500"
          >
            Get started
            <IconArrow />
          </Link>
        </div>
      </div>
    </header>
  );
}
