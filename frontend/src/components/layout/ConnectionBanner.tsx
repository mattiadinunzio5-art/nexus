import { useEffect, useState } from 'react';

/** Avviso mentre l'app riprova a contattare il server (es. riavvio del piano gratuito). */
export function ConnectionBanner() {
  const [retrying, setRetrying] = useState(false);
  useEffect(() => {
    const on = (e: Event) => setRetrying((e as CustomEvent<string>).detail === 'retrying');
    window.addEventListener('nexus:connection', on);
    return () => window.removeEventListener('nexus:connection', on);
  }, []);
  if (!retrying) return null;
  return (
    <div role="status" aria-live="polite" className="border-b border-warn/40 bg-warn/10 px-4 py-1.5 text-center text-xs text-warn">
      Il server non risponde: riprovo automaticamente (sul piano gratuito il riavvio può richiedere fino a un minuto)…
    </div>
  );
}
