import { ExternalLink } from 'lucide-react';
import { LicenseFacts, loadLicenses } from '../components/License';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { useAsync } from '../lib/useAsync';
import { locale, tr } from '../i18n';

/** NEXUS Copyright & Data Policy: principi e registro delle licenze di ogni fonte, con i conteggi reali della Biblioteca. */

const COUNT_LABEL: Record<string, string> = { series: 'serie', documents: 'documenti', events: 'eventi', entities: 'entità', relations: 'relazioni' };

export function DataPolicyPage() {
  const reg = useAsync(() => loadLicenses(), []);
  const nf = new Intl.NumberFormat(locale());
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Policy"
        title="Copyright & Data Policy"
        description="Da dove viene ogni dato di NEXUS, con quale licenza e a quali condizioni si può riutilizzare."
      />
      <Card title="Principi">
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-steel-300">
          <li>Nella Biblioteca NEXUS entrano solo dati aperti con una licenza registrata: senza scheda di licenza, l'importazione viene bloccata.</li>
          <li>Per ogni elemento NEXUS conserva fonte originale, URL e data di acquisizione; la licenza, l'attribuzione e le condizioni d'uso sono nella scheda della fonte.</li>
          <li>Dei libri e degli articoli protetti da copyright NEXUS conserva solo i riferimenti bibliografici (autore, titolo, anno, DOI), mai il testo.</li>
          <li>Gli unici testi integrali sono opere di pubblico dominio, libere anche in Italia e nell'Unione europea.</li>
          <li>I documenti e i dati caricati da un utente restano privati nel suo account e non entrano nella Biblioteca.</li>
          <li>NEXUS non modifica i valori delle fonti: i dati mancanti restano mancanti, e ogni trasformazione calcolata è dichiarata come tale.</li>
        </ul>
        <p className="mt-3 text-xs text-steel-500">
          Le condizioni sono riassunte dalle pagine ufficiali di ciascuna fonte, indicate in ogni scheda con la data di verifica. Questa pagina non costituisce parere legale: in caso di dubbio fa fede il testo della licenza originale.
        </p>
        {reg.data && <p className="mt-2 text-xs text-steel-500">Versione {reg.data.version} · aggiornata il {reg.data.updated}</p>}
      </Card>
      {reg.loading && !reg.data && <Loading />}
      {reg.error && <ErrorBox error={reg.error} onRetry={reg.reload} />}
      {reg.data && (
        <div className="space-y-4">
          {reg.data.licenses.map((e) => {
            const counts = Object.entries(e.library_counts).filter(([, n]) => n);
            return (
              <Card key={e.id} title={e.name}>
                <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-steel-400">
                  <span>{e.publisher}</span>
                  <a href={e.homepage} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-gold-300 hover:underline">sito <ExternalLink className="size-3" aria-hidden /></a>
                  {reg.data!.library_licenses.includes(e.id) ? <Badge tone="gold">LIBRARY</Badge> : <Badge>fuori dalla Biblioteca</Badge>}
                  {e.status === 'per_item' && <Badge tone="warn">da verificare serie per serie</Badge>}
                </div>
                <p className="mb-2 text-sm text-steel-300">{e.applies_to}</p>
                {counts.length > 0 && (
                  <p className="mb-3 text-xs text-steel-400">
                    Nella Biblioteca: {counts.map(([k, n]) => `${nf.format(n!)} ${tr(COUNT_LABEL[k] ?? k)}`).join(' · ')}
                  </p>
                )}
                <LicenseFacts e={e} />
                {e.notes && <p className="mt-3 text-xs text-steel-500">{e.notes}</p>}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
