import { redirect } from 'next/navigation';

export default function MarketGapsRedirect({ params }: { params: { marketId: string } }) {
  redirect(`/markets/${encodeURIComponent(params.marketId)}`);
}
