import { redirect } from 'next/navigation';

export default function LegacyThemeDetailRedirect({
  params,
  searchParams,
}: {
  params: { themeId: string };
  searchParams: { market?: string };
}) {
  redirect(
    searchParams.market
      ? `/markets/${encodeURIComponent(searchParams.market)}/themes?theme=${encodeURIComponent(params.themeId)}`
      : '/markets'
  );
}
