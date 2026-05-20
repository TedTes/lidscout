import DashboardNav from '@/components/DashboardNav';

type Props = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
};

export default function DashboardShell({ title, subtitle, actions, children }: Props) {
  return (
    <main className="min-h-screen bg-gray-50">
      <DashboardNav />
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal text-gray-950">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
        {children}
      </div>
    </main>
  );
}
