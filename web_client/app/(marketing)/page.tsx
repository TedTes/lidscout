import Hero from '@/components/marketing/Hero';
import BeforeAfter from '@/components/marketing/BeforeAfter';
import HowItWorks from '@/components/marketing/HowItWorks';
import OutputSamples from '@/components/marketing/OutputSamples';
import Methodology from '@/components/marketing/Methodology';
import Pricing from '@/components/marketing/Pricing';

export default function LandingPage() {
  return (
    <>
      <Hero />
      <BeforeAfter />
      <HowItWorks />
      <OutputSamples />
      <Methodology />
      <Pricing />
    </>
  );
}
