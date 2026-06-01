'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/context/AuthContext';

function initials(email: string) {
  return email.slice(0, 1).toUpperCase();
}

function IconUser() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21a8 8 0 0 0-16 0" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function IconLogout() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

export default function AccountMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) {
    return (
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-800/80 bg-slate-900/40 text-slate-600">
        <IconUser />
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(value => !value)}
        className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-800/80 bg-slate-900/50 text-sm font-semibold text-slate-300 shadow-sm transition hover:border-slate-700 hover:bg-slate-800/70"
        aria-label="Account"
      >
        {initials(user.email)}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-xl border border-slate-800/80 bg-[#0b0e20] shadow-xl shadow-black/40">
          <div className="border-b border-white/[0.06] px-3 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-700">Account</p>
            <p className="mt-1 truncate text-xs text-slate-400">{user.email}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-xs font-medium text-slate-500 transition hover:bg-white/[0.04] hover:text-slate-200"
          >
            <IconLogout />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
