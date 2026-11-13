import { Hero } from '../components/sections/Hero';
import { Case1929, HowItWorks, Modules, TrustLink, Why } from '../components/sections/Essentials';
import { Access } from '../components/sections/Access';
import { usePageMeta } from '../lib/meta';

/** Home in sei sezioni: breve, per essere letta fino in fondo. I dettagli restano nelle guide dei moduli. */
export function Home() {
  usePageMeta(null);
  return (
    <>
      <Hero />
      <Why />
      <Modules />
      <HowItWorks />
      <Case1929 />
      <Access />
      <TrustLink />
    </>
  );
}
