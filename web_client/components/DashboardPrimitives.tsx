import Link from 'next/link';

export function EmptyPanel({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-200 bg-white px-5 py-10 text-center">
      <p className="text-sm font-semibold text-gray-800">{title}</p>
      {detail && <p className="mx-auto mt-1 max-w-md text-sm text-gray-500">{detail}</p>}
    </div>
  );
}

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {message}
    </div>
  );
}

export function LoadingPanel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-900">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-sky-200 border-t-sky-700" />
      {label}
    </div>
  );
}

export function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
      <p className="text-xs font-medium uppercase text-gray-400">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-950">{value}</p>
    </div>
  );
}

export function ScoreBadge({ value }: { value: number }) {
  const tone =
    value >= 8
      ? 'border-green-200 bg-green-50 text-green-700'
      : value >= 6
        ? 'border-amber-200 bg-amber-50 text-amber-700'
        : 'border-gray-200 bg-gray-50 text-gray-600';

  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${tone}`}>
      {value.toFixed(1)}
    </span>
  );
}

export function ClusterLink({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <Link href={`/clusters/${encodeURIComponent(id)}`} className="text-sky-700 hover:underline">
      {children}
    </Link>
  );
}
