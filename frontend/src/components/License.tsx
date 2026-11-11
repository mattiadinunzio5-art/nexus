import { Link } from 'react-router-dom';
import { ExternalLink, Scale } from 'lucide-react';
import { api } from '../api/client';
import type { LicenseEntry, LicenseRegistry, Permission } from '../api/types';
import { useAsync } from '../lib/useAsync';
import { lang as currentLang } from '../i18n';
import { Badge, type BadgeTone } from './ui/Badge';

/** NEXUS Copyright & Data Policy: riquadro della licenza di un elemento (serie, documento, evento). */

let cache: Promise<LicenseRegistry> | null = null;
let cacheLang = '';

/** Il registro cambia raramente: una sola richiesta per lingua e sessione. */
export function loadLicenses(lang: string = currentLang()): Promise<LicenseRegistry> {
  if (!cache || cacheLang !== lang) {
    cacheLang = lang;
    cache = api.licenses().catch((e) => { cache = null; throw e; });
  }
  return cache;
}

/** Solo per i test. */
export function _resetLicenseCache(): void {
  cache = null;
}

export const PERMISSION: Record<Permission, { label: string; tone: BadgeTone }> = {
  yes: { label: 'Sì', tone: 'ok' },
  conditional: { label: 'Con condizioni', tone: 'warn' },
  no: { label: 'No', tone: 'bad' },
};

export function LicenseFacts({ e }: { e: LicenseEntry }) {
  return (
    <dl className="grid gap-x-4 gap-y-2 text-xs sm:grid-cols-[11rem_1fr]">
      <dt className="text-steel-500">Licenza</dt>
      <dd className="text-paper"><a href={e.license_url} target="_blank" rel="noreferrer noopener" className="hover:underline">{e.license}</a></dd>
      <dt className="text-steel-500">Attribuzione obbligatoria</dt>
      <dd className="text-steel-300">{e.attribution}</dd>
      <dt className="text-steel-500">Uso commerciale</dt>
      <dd className="text-steel-300"><Badge tone={PERMISSION[e.commercial].tone}>{PERMISSION[e.commercial].label}</Badge> {e.commercial_note}</dd>
      <dt className="text-steel-500">Redistribuzione</dt>
      <dd className="text-steel-300"><Badge tone={PERMISSION[e.redistribution].tone}>{PERMISSION[e.redistribution].label}</Badge> {e.redistribution_note}</dd>
      <dt className="text-steel-500">Limitazioni territoriali</dt>
      <dd className="text-steel-300">{e.territorial}</dd>
      <dt className="text-steel-500">Modifiche effettuate da NEXUS</dt>
      <dd className="text-steel-300">{e.modifications}</dd>
      <dt className="text-steel-500">Condizioni verificate il</dt>
      <dd className="text-steel-300">
        {e.verified_on} · <a href={e.terms_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-gold-300 hover:underline">pagina ufficiale <ExternalLink className="size-3" aria-hidden /></a>
        {e.status === 'per_item' && <span className="ml-2 text-warn">da verificare serie per serie</span>}
      </dd>
    </dl>
  );
}

/** Riquadro compatto: mostra le schede indicate; nulla se l'elemento non ha una fonte registrata (es. dati propri). */
export function LicenseBox({ ids }: { ids: (string | null | undefined)[] }) {
  const reg = useAsync(() => loadLicenses(), []);
  const wanted = ids.filter((x): x is string => !!x);
  if (!wanted.length || !reg.data) return null;
  const entries = wanted.map((id) => reg.data!.licenses.find((l) => l.id === id)).filter((x): x is LicenseEntry => !!x);
  if (!entries.length) return null;
  return (
    <section className="mt-3 rounded-md border border-ink-700 bg-ink-850 p-3" aria-label="Licenza della fonte">
      <p className="mb-2 flex items-center gap-2 text-xs font-medium text-paper">
        <Scale className="size-3.5 text-gold-400" aria-hidden /> Licenza e condizioni d'uso
        <Link to="/data-policy" className="ml-auto text-[11px] font-normal text-gold-300 hover:underline">Copyright & Data Policy</Link>
      </p>
      <div className="space-y-3">
        {entries.map((e) => (
          <div key={e.id}>
            <p className="mb-1 text-xs text-steel-400">{e.name} — {e.publisher}</p>
            <LicenseFacts e={e} />
          </div>
        ))}
      </div>
    </section>
  );
}
