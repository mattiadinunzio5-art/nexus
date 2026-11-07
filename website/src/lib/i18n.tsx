import { useLocation } from 'react-router-dom';
import { MODULES, MODULES_BY_SLUG } from '../content/modules';
import { MODULES_BY_SLUG_IT, MODULES_IT } from '../content/modules.it';
import { CAPABILITIES, CASE_STUDY, WORKFLOW } from '../content/story';
import { CAPABILITIES_IT, CASE_STUDY_IT, WORKFLOW_IT } from '../content/story.it';
import { STRINGS } from './strings';

export type Lang = 'en' | 'it';

export const langFromPath = (path: string): Lang => (path === '/it' || path.startsWith('/it/') ? 'it' : 'en');

/** Percorso nella lingua scelta: '/architecture/x' -> '/it/architecture/x', '/#vision' -> '/it#vision'. */
export function localize(path: string, lang: Lang): string {
  if (lang === 'en') return path;
  if (path === '/') return '/it';
  if (path.startsWith('/#')) return `/it${path.slice(1)}`;
  return `/it${path}`;
}

/** Stessa pagina nell'altra lingua. */
export function counterpart(pathname: string, hash: string): string {
  const lang = langFromPath(pathname);
  const bare = lang === 'it' ? pathname.slice(3) || '/' : pathname;
  return localize(bare, lang === 'it' ? 'en' : 'it') + hash;
}

const CONTENT = {
  en: { modules: MODULES, modulesBySlug: MODULES_BY_SLUG, workflow: WORKFLOW, caseStudy: CASE_STUDY, capabilities: CAPABILITIES },
  it: { modules: MODULES_IT, modulesBySlug: MODULES_BY_SLUG_IT, workflow: WORKFLOW_IT, caseStudy: CASE_STUDY_IT, capabilities: CAPABILITIES_IT },
};

export function useI18n() {
  const { pathname } = useLocation();
  const lang = langFromPath(pathname);
  return { lang, t: STRINGS[lang], p: (path: string) => localize(path, lang), ...CONTENT[lang] };
}
