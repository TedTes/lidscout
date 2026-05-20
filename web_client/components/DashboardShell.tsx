import DashboardNav from '@/components/DashboardNav';

type Props = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
};

export default function DashboardShell({ title, subtitle, actions, children }: Props) {
  return (
    <div className="min-h-screen bg-[#07091a]">
      <DashboardNav />

      <main className="lg:ml-[220px]">
        <div className="mx-auto max-w-5xl px-5 pb-16 pt-6 lg:px-8 lg:pt-10">
          {/* Page header */}
          <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-100">{title}</h1>
              {subtitle && (
                <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
              )}
            </div>
            {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
          </div>

          {children}
        </div>
      </main>
    </div>
  );
}
