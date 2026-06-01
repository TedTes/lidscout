import DashboardNav from '@/components/app/DashboardNav';
import { AuthProvider } from '@/lib/context/AuthContext';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-screen overflow-x-hidden bg-[#07091a]">
        <DashboardNav />
        <main className="w-full min-w-0 overflow-x-hidden pt-12 lg:ml-[260px] lg:w-[calc(100%-260px)] lg:pt-0">
          {children}
        </main>
      </div>
    </AuthProvider>
  );
}
