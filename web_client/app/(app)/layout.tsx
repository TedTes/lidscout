import DashboardNav from '@/components/app/DashboardNav';
import { AuthProvider } from '@/lib/context/AuthContext';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-[#07091a]">
        <DashboardNav />
        <main className="pt-14 lg:ml-[220px] lg:pt-0">
          {children}
        </main>
      </div>
    </AuthProvider>
  );
}
