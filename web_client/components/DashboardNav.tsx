'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const items = [
  { href: '/signals', label: 'Signals' },
  { href: '/reports/latest', label: 'Latest report' },
  { href: '/pipeline/run', label: 'Pipeline run' },
];

export default function DashboardNav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/signals" className="text-sm font-bold uppercase tracking-widest text-sky-700">
          LidScout
        </Link>
        <nav className="flex flex-wrap gap-1 rounded-lg bg-gray-100 p-1">
          {items.map(item => {
            const active = pathname === item.href || (item.href === '/signals' && pathname.startsWith('/clusters'));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                  active ? 'bg-white text-gray-950 shadow-sm' : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
