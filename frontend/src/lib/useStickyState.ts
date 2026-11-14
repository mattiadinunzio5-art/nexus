import { useCallback, useEffect, useRef, useState, type Dispatch, type RefObject, type SetStateAction } from 'react';

/**
 * Come useState, ma il valore resta salvato per la sessione del browser (sessionStorage):
 * passando da un modulo all'altro e tornando indietro ricerche e filtri non si perdono.
 * Se lo storage non è disponibile (navigazione privata, test) si comporta come useState.
 */
export function useStickyState<T>(key: string, initial: T): [T, Dispatch<SetStateAction<T>>] {
  const k = `nexus.sticky.${key}`;
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = sessionStorage.getItem(k);
      return raw === null ? initial : (JSON.parse(raw) as T);
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      if (value === undefined) sessionStorage.removeItem(k);
      else sessionStorage.setItem(k, JSON.stringify(value));
    } catch {
      /* storage pieno o non disponibile: si continua senza salvare */
    }
  }, [k, value]);
  return [value, setValue];
}

/** Valore che si aggiorna solo dopo una pausa nella digitazione (una richiesta, non una per lettera). */
export function useDebounced<T>(value: T, ms = 400): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/**
 * Bozza di un modulo: come useStickyState, ma con una funzione `clear` da chiamare dopo il salvataggio
 * (o con «Annulla»). Così il testo scritto non si perde cambiando sezione, e sparisce quando è stato salvato.
 * Non usarla per password o chiavi: sessionStorage è leggibile dagli script della pagina.
 */
export function useDraft<T>(key: string, initial: T): [T, Dispatch<SetStateAction<T>>, () => void] {
  const [value, setValue] = useStickyState<T>(`draft.${key}`, initial);
  const init = useRef(initial);
  init.current = initial;
  const clear = useCallback(() => {
    setValue(init.current);
    try { sessionStorage.removeItem(`nexus.sticky.draft.${key}`); } catch { /* storage non disponibile */ }
  }, [key, setValue]);
  return [value, setValue, clear];
}

/** File scelti in un modulo: restano in memoria finché la scheda è aperta, anche cambiando sezione. */
const pendingFiles = new Map<string, File>();

export function rememberFile(key: string, file: File | undefined | null): void {
  if (file) pendingFiles.set(key, file);
  else pendingFiles.delete(key);
}

export function recalledFile(key: string): File | undefined {
  return pendingFiles.get(key);
}

/** Rimette nel campo <input type="file"> il file scelto prima di cambiare sezione (dove il browser lo consente). */
export function useFileDraft(key: string, ref: RefObject<HTMLInputElement>): void {
  useEffect(() => {
    const f = pendingFiles.get(key);
    const el = ref.current;
    if (!f || !el || el.files?.length) return;
    try {
      const dt = new DataTransfer();
      dt.items.add(f);
      el.files = dt.files;
    } catch {
      /* DataTransfer non disponibile: il file resta comunque in memoria (recalledFile) */
    }
  }, [key, ref]);
}
