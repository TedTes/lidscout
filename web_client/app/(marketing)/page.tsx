import Hero from '@/components/marketing/Hero';
import BeforeAfter from '@/components/marketing/BeforeAfter';
import EvidenceTrail from '@/components/marketing/EvidenceTrail';
import HowItWorks from '@/components/marketing/HowItWorks';
import DashboardDemo from '@/components/marketing/DashboardDemo';
import UseCases from '@/components/marketing/UseCases';
import Pricing from '@/components/marketing/Pricing';

export default function LandingPage() {
  return (
    <>
      <Hero />
      <BeforeAfter />
      <DashboardDemo />
      <EvidenceTrail />
      <HowItWorks />
      <UseCases />
      <Pricing />
    </>
  );
}
