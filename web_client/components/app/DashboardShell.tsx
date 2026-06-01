import AccountMenu from '@/components/app/AccountMenu';

type Props = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
};

export default function DashboardShell({ title, subtitle, actions, children }: Props) {
  const titleBlock = (
    <div className="min-w-0">
      <h1 className="max-w-2xl text-2xl font-semibold leading-tight tracking-tight text-slate-100">{title}</h1>
      {subtitle && <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">{subtitle}</p>}
    </div>
  );

  return (
    <div className="mx-auto max-w-6xl px-5 pb-16 pt-6 lg:px-9 lg:pt-9">
      <div className="mb-8">
        {actions ? (
          <>
            <div className="flex min-w-0 items-start justify-between gap-4">
              <div className="min-w-0 flex-1">{actions}</div>
              <AccountMenu />
            </div>
          </>
        ) : (
          <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
            {titleBlock}
            <AccountMenu />
          </div>
        )}
      </div>
      {children}
    </div>
  );
}
