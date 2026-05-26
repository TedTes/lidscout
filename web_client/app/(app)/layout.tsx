import DashboardNav from '@/components/app/DashboardNav';
import { AuthProvider } from '@/lib/context/AuthContext';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-[#07091a]">
        <DashboardNav />
        <main className="lg:ml-[220px]">
          {children}
        </main>
      </div>
    </AuthProvider>
  );
}
