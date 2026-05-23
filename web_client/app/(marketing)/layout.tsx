import LandingNav from '@/components/marketing/LandingNav';
import Footer from '@/components/marketing/Footer';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#07091a]">
      <LandingNav />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
