import { redirect } from 'next/navigation';

export default function NicheIndexRedirect({ params }: { params: { marketId: string } }) {
  redirect(`/markets/${encodeURIComponent(params.marketId)}/gaps`);
}
