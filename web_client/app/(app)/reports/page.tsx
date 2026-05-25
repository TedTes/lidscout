import { redirect } from 'next/navigation';

export default function LegacyReportsRedirect({
  searchParams,
}: {
  searchParams: { market?: string };
}) {
  redirect(searchParams.market ? `/markets/${encodeURIComponent(searchParams.market)}/reports` : '/markets');
}
