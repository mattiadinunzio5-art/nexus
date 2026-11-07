import { Link } from 'react-router-dom';
import { usePageMeta } from '../lib/meta';
import { useI18n } from '../lib/i18n';

export function NotFound() {
  const { t, p } = useI18n();
  usePageMeta(t.nf.title);
  return (
    <section className="flex min-h-[100svh] flex-col items-center justify-center bg-void px-5 text-center">
      <p className="font-mono text-sm text-copper">404</p>
      <h1 className="mt-4 font-serif text-6xl">{t.nf.heading}</h1>
      <Link to={p('/')} className="mt-10 rounded-full bg-ivory px-6 py-3 text-sm font-medium text-void hover:bg-copper">{t.nf.back}</Link>
    </section>
  );
}
