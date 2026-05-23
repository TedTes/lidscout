import DashboardNav from '@/components/app/DashboardNav';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#07091a]">
      <DashboardNav />
      <main className="lg:ml-[220px]">
        {children}
      </main>
    </div>
  );
}
