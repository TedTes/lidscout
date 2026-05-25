import { redirect } from 'next/navigation';

export default function LegacyFindingsRedirect({
  searchParams,
}: {
  searchParams: { market?: string };
}) {
  redirect(searchParams.market ? `/markets/${encodeURIComponent(searchParams.market)}/findings` : '/markets');
}
