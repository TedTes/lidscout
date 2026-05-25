import { redirect } from 'next/navigation';

export default function LegacySourcesRedirect({
  searchParams,
}: {
  searchParams: { market?: string };
}) {
  redirect(searchParams.market ? `/markets/${encodeURIComponent(searchParams.market)}/sources` : '/markets');
}
