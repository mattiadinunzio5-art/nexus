import { useEffect, useId, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { api } from '../../api/client';
import { inputCls } from './Form';

export type PickerKind = 'entity' | 'event' | 'source';
interface Item { id: number; label: string; detail?: string; mine: boolean }

const MIN_LIBRARY_QUERY = 2;

/** Cerca prima tra le voci dell'utente, poi (con almeno 2 caratteri) nella Biblioteca: decine di migliaia di voci. */
async function find(kind: PickerKind, q: string): Promise<Item[]> {
  const term = q.trim() || undefined;
  const lib = (term?.length ?? 0) >= MIN_LIBRARY_QUERY;
  if (kind === 'entity') {
    const [mine, other] = await Promise.all([
      api.findEntities({ q: term, origin: 'mine', limit: 30 }),
      lib ? api.findEntities({ q: term, origin: 'library', limit: 30 }) : Promise.resolve([]),
    ]);
    const map = (mineFlag: boolean) => (e: (typeof mine)[number]) => ({
      id: e.id, label: e.name, mine: mineFlag,
      detail: [e.entity_type, e.start_year != null ? `${e.start_year}${e.end_year != null ? `–${e.end_year}` : ''}` : ''].filter(Boolean).join(' · '),
    });
    return [...mine.map(map(true)), ...other.map(map(false))];
  }
  if (kind === 'event') {
    const [mine, other] = await Promise.all([
      api.events({ q: term, origin: 'mine', limit: 30 }),
      lib ? api.events({ q: term, origin: 'library', limit: 30 }) : Promise.resolve([]),
    ]);
    const map = (mineFlag: boolean) => (e: (typeof mine)[number]) => ({ id: e.id, label: e.title, detail: e.date_label, mine: mineFlag });
    return [...mine.map(map(true)), ...other.map(map(false))];
  }
  const [mine, other] = await Promise.all([
    api.findSources({ q: term, origin: 'mine', limit: 30 }),
    lib ? api.findSources({ q: term, origin: 'library', limit: 30 }) : Promise.resolve([]),
  ]);
  const map = (mineFlag: boolean) => (s: (typeof mine)[number]) => ({ id: s.id, label: s.citation, mine: mineFlag });
  return [...mine.map(map(true)), ...other.map(map(false))];
}

async function labelOf(kind: PickerKind, id: number): Promise<string> {
  if (kind === 'entity') return (await api.entity(id)).name;
  if (kind === 'event') return (await api.event(id)).title;
  return (await api.source(id)).citation;
}

/**
 * Campo di ricerca al posto di un menu a tendina: mostra il testo completo (nessun troncamento),
 * le voci dell'utente prima di quelle della Biblioteca, e cerca nell'intero archivio.
 */
export function SearchPicker({
  kind, value, onChange, ariaLabel, placeholder, exclude = [], className = '',
}: {
  kind: PickerKind;
  value: string;
  onChange: (id: string, label?: string) => void;
  ariaLabel?: string;
  placeholder?: string;
  exclude?: number[];
  className?: string;
}) {
  const [label, setLabel] = useState('');
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [active, setActive] = useState(0);
  const listId = useId();
  const seq = useRef(0);

  // Etichetta della voce scelta (anche quando il valore arriva da una bozza salvata).
  useEffect(() => {
    if (!value) { setLabel(''); return; }
    let alive = true;
    labelOf(kind, Number(value)).then((l) => alive && setLabel(l)).catch(() => alive && setLabel(`#${value}`));
    return () => { alive = false; };
  }, [kind, value]);

  useEffect(() => {
    if (!open) return;
    const n = ++seq.current;
    setBusy(true);
    const t = setTimeout(() => {
      find(kind, q)
        .then((r) => { if (n === seq.current) { setItems(r.filter((x) => !exclude.includes(x.id))); setActive(0); setErr(undefined); } })
        .catch(() => n === seq.current && setErr('Ricerca non riuscita: riprova.'))
        .finally(() => n === seq.current && setBusy(false));
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, q, open, exclude.join(',')]);

  function pick(it: Item) {
    setLabel(it.label);
    setOpen(false);
    setQ('');
    onChange(String(it.id), it.label);
  }

  const libHint = q.trim().length < MIN_LIBRARY_QUERY;
  const mine = items.filter((i) => i.mine);
  const other = items.filter((i) => !i.mine);
  const option = (it: Item, idx: number) => (
    <li key={`${it.mine ? 'm' : 'l'}${it.id}`} id={`${listId}-${idx}`} role="option" aria-selected={idx === active}
      onMouseDown={(e) => { e.preventDefault(); pick(it); }} onMouseEnter={() => setActive(idx)}
      className={`cursor-pointer px-3 py-1.5 text-sm ${idx === active ? 'bg-ink-800 text-paper' : 'text-steel-300'}`}>
      <span className="whitespace-normal break-words">{it.label}</span>
      {it.detail && <span className="ml-2 text-[11px] text-steel-500">{it.detail}</span>}
    </li>
  );

  return (
    <div className={`relative ${className}`}>
      <div className="flex gap-1">
        <input
          role="combobox" aria-label={ariaLabel} aria-expanded={open} aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={open && items.length ? `${listId}-${active}` : undefined}
          className={inputCls}
          value={open ? q : label}
          placeholder={placeholder ?? (kind === 'source' ? 'Cerca per titolo o autore…' : kind === 'event' ? 'Cerca un evento o un anno…' : 'Cerca un\'entità…')}
          onFocus={() => { setOpen(true); setQ(''); }}
          onBlur={() => setOpen(false)}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            else if (e.key === 'Enter' && open && items[active]) { e.preventDefault(); pick(items[active]); }
            else if (e.key === 'Escape') setOpen(false);
          }}
        />
        {value && !open && (
          <button type="button" aria-label="Svuota selezione" className="rounded-md px-2 text-steel-400 hover:text-paper"
            onClick={() => { setLabel(''); onChange(''); }}><X className="size-4" /></button>
        )}
      </div>
      {open && (
        <ul id={listId} role="listbox" aria-label={ariaLabel ? `Risultati: ${ariaLabel}` : 'Risultati'}
          className="absolute z-30 mt-1 max-h-72 w-full min-w-[18rem] overflow-auto rounded-md border border-ink-700 bg-ink-900 py-1 shadow-lg">
          {err && <li className="px-3 py-1.5 text-sm text-bad">{err}</li>}
          {!err && busy && items.length === 0 && <li className="px-3 py-1.5 text-sm text-steel-500">Ricerca…</li>}
          {mine.length > 0 && <li role="presentation" className="px-3 pt-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-steel-500">Le tue voci</li>}
          {mine.map((it, i) => option(it, i))}
          {other.length > 0 && <li role="presentation" className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-steel-500">Biblioteca NEXUS</li>}
          {other.map((it, i) => option(it, mine.length + i))}
          {!busy && !err && items.length === 0 && <li className="px-3 py-1.5 text-sm text-steel-500">Nessun risultato{libHint ? ' tra le tue voci' : ''}.</li>}
          {libHint && <li role="presentation" className="px-3 py-1.5 text-[11px] text-steel-500">Scrivi almeno {MIN_LIBRARY_QUERY} caratteri per cercare anche nella Biblioteca.</li>}
        </ul>
      )}
    </div>
  );
}
