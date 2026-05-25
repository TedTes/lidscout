import { redirect } from 'next/navigation';

export default function LegacySignalsRedirect({
  searchParams,
}: {
  searchParams: { market?: string };
}) {
  redirect(searchParams.market ? `/markets/${encodeURIComponent(searchParams.market)}/findings` : '/markets');
}
