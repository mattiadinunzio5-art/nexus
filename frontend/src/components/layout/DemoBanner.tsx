import { useAuth } from '../../state/Auth';

/** Striscia visibile durante la demo pubblica: ricorda che è in sola lettura e invita a creare un account. */
export function DemoBanner() {
  const { isDemo, demoLang, siteUrl, logout } = useAuth();
  if (!isDemo) return null;
  const site = siteUrl?.replace(/\/+$/, '');
  const en = demoLang === 'en';
  return (
    <div role="note" className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-b border-gold-500/40 bg-gold-500/10 px-4 py-2 text-center text-xs text-gold-300">
      <span>
        {en
          ? <><strong className="font-semibold">Read-only demo</strong> · sample project “The Great Depression 1929–1933” with real data (FRED/NBER) and sources.</>
          : <><strong className="font-semibold">Demo in sola lettura</strong> · progetto di esempio «La Grande Depressione 1929–1933» con dati reali (FRED/NBER) e fonti.</>}
      </span>
      <span className="flex gap-3">
        {site && <a className="font-medium text-gold-300 underline hover:text-paper" href={en ? `${site}/signup` : `${site}/it/signup`}>{en ? 'Create a free account' : 'Crea un account gratuito'}</a>}
        <button type="button" className="text-steel-300 underline hover:text-paper" onClick={() => void logout()}>{en ? 'Exit demo' : 'Esci dalla demo'}</button>
      </span>
    </div>
  );
}
