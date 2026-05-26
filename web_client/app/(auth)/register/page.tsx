'use client';

import Link from 'next/link';
import { useState } from 'react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      // TODO: wire to auth backend
      await new Promise(r => setTimeout(r, 800));
      window.location.href = '/markets';
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-slate-100">Get started</h1>
        <p className="mt-1.5 text-sm text-slate-500">
          Free until Q3 · No credit card required
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-400" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-slate-700/70 bg-slate-900/60 px-3.5 py-2.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-400" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="new-password"
            minLength={8}
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Min. 8 characters"
            className="w-full rounded-lg border border-slate-700/70 bg-slate-900/60 px-3.5 py-2.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition"
          />
        </div>

        {error && (
          <p className="rounded-lg border border-rose-500/20 bg-rose-500/[0.06] px-3 py-2 text-xs text-rose-400">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-900/40 transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-700">
        By creating an account you agree to our{' '}
        <Link href="#" className="text-slate-600 hover:text-slate-400 transition">Terms</Link>
        {' '}and{' '}
        <Link href="#" className="text-slate-600 hover:text-slate-400 transition">Privacy Policy</Link>.
      </p>

      <p className="mt-4 text-center text-xs text-slate-600">
        Already have an account?{' '}
        <Link href="/login" className="font-medium text-violet-400 hover:text-violet-300 transition">
          Sign in
        </Link>
      </p>
    </div>
  );
}
