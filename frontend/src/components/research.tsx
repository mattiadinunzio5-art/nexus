import { ShieldAlert } from 'lucide-react';
import type { ClaimType, RetrievalHit, Support, VerificationStatus } from '../api/types';
import { Badge, type BadgeTone } from './ui/Badge';

export const SUPPORT: Record<Support, { label: string; tone: BadgeTone }> = {
  strong: { label: 'Supporto forte', tone: 'ok' },
  partial: { label: 'Supporto parziale', tone: 'gold' },
  weak: { label: 'Supporto debole', tone: 'warn' },
  none: { label: 'Nessun supporto', tone: 'bad' },
};

export const CLAIM: Record<ClaimType, { label: string; tone: BadgeTone }> = {
  documented_fact: { label: 'Fatto documentato', tone: 'ok' },
  interpretation: { label: 'Interpretazione', tone: 'gold' },
  hypothesis: { label: 'Ipotesi', tone: 'warn' },
  estimate: { label: 'Stima', tone: 'warn' },
  missing: { label: 'Dato mancante', tone: 'bad' },
};

export const VERIFICATION: Record<VerificationStatus, { label: string; tone: BadgeTone }> = {
  unverified: { label: 'Non verificata', tone: 'warn' },
  verified_user: { label: "Controllata sull'originale", tone: 'ok' },
  verified_registry: { label: 'Metadati confermati', tone: 'ok' },
  registry_mismatch: { label: 'DOI trovato, metadati discordanti', tone: 'bad' },
  registry_incomplete: { label: 'DOI trovato, scheda incompleta', tone: 'warn' },
  not_found: { label: 'Non trovata nel registro', tone: 'bad' },
};

export function InjectionWarning() {
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-warn" title="Il testo contiene frasi simili a istruzioni per un'AI. Viene trattato solo come dato.">
      <ShieldAlert className="size-3.5" aria-hidden /> Possibili istruzioni nel testo (trattate come dato)
    </span>
  );
}

const pct = (v: number | undefined) => `${Math.round((v ?? 0) * 100)}%`;

/** I tre indicatori, separati: rilevanza ≠ copertura ≠ supporto. */
export function Indicators({ hit }: { hit: RetrievalHit }) {
  return (
    <dl className="mt-2 grid grid-cols-1 gap-2 text-[11px] sm:grid-cols-3" data-testid="indicators">
      <div title="Posizione del passaggio nella classifica della ricerca, rispetto al primo risultato. Non dice se il passaggio risponde.">
        <dt className="text-steel-500">Rilevanza</dt><dd className="text-paper">{pct(hit.relevance)}</dd>
      </div>
      <div title="Quota dei concetti della domanda (anche tradotti) presenti nel passaggio.">
        <dt className="text-steel-500">Copertura della domanda</dt>
        <dd className="text-paper">{pct(hit.coverage)}{hit.missing_terms && hit.missing_terms.length > 0 && <span className="text-steel-500"> · mancano: {hit.missing_terms.join(', ')}</span>}</dd>
      </div>
      <div title="I concetti devono comparire insieme nella stessa frase. Stima lessicale: il significato va verificato leggendo la frase.">
        <dt className="text-steel-500">Supporto (stessa frase)</dt>
        <dd><Badge tone={SUPPORT[hit.support].tone}>{SUPPORT[hit.support].label}</Badge></dd>
      </div>
    </dl>
  );
}

export function PassageCard({ hit, index }: { hit: RetrievalHit; index?: number }) {
  return (
    <article className="rounded-lg border border-ink-700 bg-ink-900 p-3" data-testid="passage">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {index !== undefined && <span className="font-mono text-steel-500">[{index}]</span>}
        <span className="font-medium text-paper">{hit.citation || hit.document_title}</span>
        {!hit.citation && hit.locator && <span className="text-steel-400">{hit.locator}</span>}
        {hit.injection_flag && <InjectionWarning />}
      </div>
      <Indicators hit={hit} />
      <p className="mt-2 whitespace-pre-line text-sm text-steel-300">{hit.text}</p>
      <p className="mt-2 text-[11px] text-steel-500">Fonte: {hit.source_label}</p>
    </article>
  );
}
