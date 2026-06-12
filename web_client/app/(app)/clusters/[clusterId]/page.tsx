import { redirect } from 'next/navigation';

export default function LegacyClusterDetailRedirect({
  searchParams,
}: {
  params: { clusterId: string };
  searchParams: { market?: string };
}) {
  redirect(
    searchParams.market
      ? `/markets/${encodeURIComponent(searchParams.market)}/evidence?view=patterns`
      : '/markets'
  );
}
