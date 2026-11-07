import { Hero } from '../components/sections/Hero';
import { Vision } from '../components/sections/Vision';
import { What } from '../components/sections/What';
import { Architecture } from '../components/sections/Architecture';
import { Workflow } from '../components/sections/Workflow';
import { CaseStudy } from '../components/sections/CaseStudy';
import { Capabilities } from '../components/sections/Capabilities';
import { Access } from '../components/sections/Access';
import { usePageMeta } from '../lib/meta';
import { CasesTeaser } from './Cases';

export function Home() {
  usePageMeta(null);
  return (
    <>
      <Hero />
      <Vision />
      <What />
      <Architecture />
      <Workflow />
      <CaseStudy />
      <Capabilities />
      <CasesTeaser />
      <Access />
    </>
  );
}
