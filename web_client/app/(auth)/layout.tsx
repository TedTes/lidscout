import Link from 'next/link';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { IconRadar } from '@/components/marketing/icons';
import { AuthProvider } from '@/lib/context/AuthContext';

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? ''}>
    <AuthProvider>
    <div className="min-h-screen bg-[#07091a] flex flex-col">
      <header className="flex h-14 shrink-0 items-center px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-600 text-white shadow-lg shadow-violet-950">
            <IconRadar />
          </div>
          <span className="text-sm font-bold tracking-tight text-slate-100">LidScout</span>
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        {children}
      </main>
    </div>
    </AuthProvider>
    </GoogleOAuthProvider>
  );
}
