import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';

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
