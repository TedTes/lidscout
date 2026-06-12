import { redirect } from 'next/navigation';

export default function LegacyThemeDetailRedirect({
  searchParams,
}: {
  params: { themeId: string };
  searchParams: { market?: string };
}) {
  redirect(
    searchParams.market
      ? `/markets/${encodeURIComponent(searchParams.market)}/evidence?view=patterns`
      : '/markets'
  );
}
