'use client';

import { useRouter } from 'next/navigation';
import DashboardShell from '@/components/app/DashboardShell';
import { AddMarketPanel } from '@/components/app/AddMarketPanel';
import { Market } from '@/lib/types/signals';

export default function NewNichePage() {
  const router = useRouter();

  const handleAdd = (market: Market) => {
    router.replace(`/markets/${encodeURIComponent(market.id)}/gaps`);
  };

  return (
    <DashboardShell
      title="New niche"
      subtitle="Add a niche to the sidebar, then attach companies and sources from its Sources view."
    >
      <AddMarketPanel onAdd={handleAdd} onCancel={() => router.back()} />
    </DashboardShell>
  );
}
