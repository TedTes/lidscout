import { redirect } from 'next/navigation';

export default function LegacyThemesRedirect({
  searchParams,
}: {
  searchParams: { market?: string };
}) {
  redirect(searchParams.market ? `/markets/${encodeURIComponent(searchParams.market)}/themes` : '/markets');
}
