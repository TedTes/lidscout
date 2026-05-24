import Hero from '@/components/marketing/Hero';
import BeforeAfter from '@/components/marketing/BeforeAfter';
import EvidenceTrail from '@/components/marketing/EvidenceTrail';
import HowItWorks from '@/components/marketing/HowItWorks';
import UseCases from '@/components/marketing/UseCases';
import Pricing from '@/components/marketing/Pricing';

export default function LandingPage() {
  return (
    <>
      <Hero />
      <BeforeAfter />
      <EvidenceTrail />
      <HowItWorks />
      <UseCases />
      <Pricing />
    </>
  );
}
