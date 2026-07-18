import { redirect } from 'next/navigation';

type Props = { params: { marketId: string } };

export default function FindingsRedirect({ params }: Props) {
  redirect(`/markets/${encodeURIComponent(params.marketId)}/evidence`);
}
