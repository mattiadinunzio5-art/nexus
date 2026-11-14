import { locale } from '../i18n';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpenText, Play, ChartLine, FolderKanban, GraduationCap, History, Landmark, Network, Radar, Search } from 'lucide-react';
import { api } from '../api/client';
import { LibraryBadge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { useAsync } from '../lib/useAsync';

/** «Inizia da qui»: cosa è NEXUS e come cominciare in tre passi, con i numeri reali della Biblioteca. */

function Go({ to, icon, children }: { to: string; icon: ReactNode; children: ReactNode }) {
  return (
    <Link to={to} className="flex items-center gap-2 rounded-md border border-ink-700 bg-ink-850 px-3 py-2 text-sm text-paper hover:border-gold-500">
      {icon}<span className="min-w-0 flex-1">{children}</span><ArrowRight className="size-3.5 text-steel-500" aria-hidden />
    </Link>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="rounded-lg border border-ink-700 bg-ink-900 p-4">
      <div className="mb-3 flex items-center gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gold-400 text-sm font-semibold text-ink-950" aria-hidden>{n}</span>
        <h2 className="text-base font-medium text-paper">{title}</h2>
      </div>
      {children}
    </li>
  );
}

export function StartPage() {
  const lib = useAsync(() => api.librarySummary(), []);
  const l = lib.data?.available ? lib.data : null;
  const icon = 'size-4 shrink-0 text-gold-400';
  return (
    <>
      <PageHeader eyebrow="Inizia da qui" title="NEXUS in tre passi"
        description="Storia ed economia nello stesso posto: eventi con le loro fonti, dati ufficiali e strumenti per collegarli. Nessun dato inventato, e fatti e ipotesi sempre distinti." />
      <ol className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Step n={1} title="Esplora la Biblioteca NEXUS">
          <p className="mb-3 text-sm text-steel-300">Un archivio di dati aperti già pronto, con fonte e licenza per ogni elemento. È condiviso e in sola lettura: lo vedi accanto ai tuoi dati con l'etichetta <LibraryBadge />.</p>
          {l && (
            <dl className="mb-3 grid grid-cols-3 gap-2 text-center" aria-label="Contenuto della Biblioteca">
              {([['eventi storici', l.events], ['serie di dati', l.series], ['collegamenti', l.relations]] as const).map(([label, v]) => (
                <div key={label} className="rounded-md border border-ink-700 bg-ink-850 p-2">
                  <dd className="text-lg text-paper">{v.toLocaleString(locale())}</dd>
                  <dt className="text-[11px] text-steel-500">{label}</dt>
                </div>
              ))}
            </dl>
          )}
          <div className="space-y-2">
            <Go to="/search?q=panic" icon={<Search className={icon} aria-hidden />}>Cerca un tema, per esempio le crisi finanziarie</Go>
            <Go to="/time-machine" icon={<History className={icon} aria-hidden />}>Time Machine: un anno senza il senno di poi</Go>
            <Go to="/financial" icon={<ChartLine className={icon} aria-hidden />}>Serie ufficiali: World Bank, Eurostat, BCE, Maddison</Go>
            <Go to="/discovery/connections?origin=library" icon={<Radar className={icon} aria-hidden />}>Piste trovate da Discovery sulla Biblioteca</Go>
          </div>
        </Step>
        <Step n={2} title="Crea il tuo progetto">
          <p className="mb-3 text-sm text-steel-300">Un progetto raccoglie il tuo lavoro: una tesi, un corso, una ricerca. I tuoi dati restano privati, a meno che tu non scelga di condividerli.</p>
          <ul className="mb-3 space-y-1.5 text-sm text-steel-300">
            <li>• Aggiungi <strong className="text-paper">eventi</strong> con date, cause, conseguenze e grado di attendibilità.</li>
            <li>• Collega le <strong className="text-paper">fonti</strong> (libri, articoli, DOI): ognuna mostra se è verificata.</li>
            <li>• Importa <strong className="text-paper">serie di dati</strong> dai connettori ufficiali o da un tuo CSV, sempre con la fonte.</li>
          </ul>
          <div className="space-y-2">
            <Go to="/projects" icon={<FolderKanban className={icon} aria-hidden />}>Crea un progetto</Go>
            <Go to="/history" icon={<Landmark className={icon} aria-hidden />}>Aggiungi i tuoi eventi</Go>
          </div>
        </Step>
        <Step n={3} title="Collega, verifica, scrivi">
          <p className="mb-3 text-sm text-steel-300">Metti in relazione eventi e dati, poi controlla le ipotesi. NEXUS propone, tu decidi: una connessione non diventa mai un fatto da sola.</p>
          <div className="space-y-2">
            <Go to="/graph" icon={<Network className={icon} aria-hidden />}>Knowledge Graph: cause e conseguenze, con fonte</Go>
            <Go to="/discovery" icon={<Radar className={icon} aria-hidden />}>Discovery: connessioni e anomalie da verificare</Go>
            <Go to="/studio" icon={<BookOpenText className={icon} aria-hidden />}>Research Studio: un rapporto con citazioni verificabili</Go>
          </div>
        </Step>
      </ol>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Lezioni guidate">
          <Link to="/lessons/crisi-1929" className="group mb-3 block overflow-hidden rounded-md border border-ink-700 hover:border-gold-500">
            <div className="relative">
              <img src="/lessons/crisi-1929.jpg" alt="Anteprima del video della lezione sulla crisi del 1929" className="aspect-video w-full object-cover opacity-80 group-hover:opacity-100" loading="lazy" />
              <span className="absolute inset-0 flex items-center justify-center">
                <span className="flex size-12 items-center justify-center rounded-full bg-gold-400 text-ink-950"><Play className="ml-0.5 size-5" aria-hidden /></span>
              </span>
            </div>
            <p className="px-3 py-2 text-sm text-paper">Video · Il crollo del 1929: dalle fonti al rapporto (2 min e mezzo)</p>
          </Link>
          <p className="mb-3 text-sm text-steel-300">Percorsi passo per passo su casi reali: la crisi del 1929, l'inflazione degli anni Settanta, la crisi del 2008.</p>
          <Go to="/lessons" icon={<GraduationCap className={icon} aria-hidden />}>Tutte le lezioni guidate</Go>
        </Card>
        <Card title="Le regole di NEXUS">
          <ul className="space-y-1.5 text-sm text-steel-300">
            <li>• <strong className="text-paper">Ogni fatto ha una fonte</strong>, con il suo stato di verifica.</li>
            <li>• <strong className="text-paper">Fatti e ipotesi restano separati</strong>: l'AI e Discovery propongono, non decidono.</li>
            <li>• <strong className="text-paper">I buchi restano buchi</strong>: nessun dato stimato o inventato per riempirli.</li>
          </ul>
        </Card>
      </div>
    </>
  );
}
