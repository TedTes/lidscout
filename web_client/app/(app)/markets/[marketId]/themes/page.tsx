import { redirect } from 'next/navigation';

type Props = { params: { marketId: string } };

export default function ThemesRedirect({ params }: Props) {
  redirect(`/markets/${encodeURIComponent(params.marketId)}/evidence?view=patterns`);
}
