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
    <div className="w-full min-w-0 px-4 pb-16 pt-1 sm:px-5 lg:mx-auto lg:max-w-6xl lg:px-9 lg:pt-9">
      <div className="mb-3 lg:mb-8">
        {actions ? (
          <>
            <div className="flex min-w-0 items-start justify-between gap-3">
              <div className="min-w-0 flex-1">{actions}</div>
              <div className="hidden lg:block">
                <AccountMenu />
              </div>
            </div>
          </>
        ) : (
          <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
            {titleBlock}
            <div className="hidden lg:block">
              <AccountMenu />
            </div>
          </div>
        )}
      </div>
      {children}
    </div>
  );
}
