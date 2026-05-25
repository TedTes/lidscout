import { redirect } from 'next/navigation';

export default function LegacyClusterDetailRedirect({
  params,
  searchParams,
}: {
  params: { clusterId: string };
  searchParams: { market?: string };
}) {
  redirect(
    searchParams.market
      ? `/markets/${encodeURIComponent(searchParams.market)}/themes/${encodeURIComponent(params.clusterId)}`
      : '/markets'
  );
}
