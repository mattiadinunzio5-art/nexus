import { useState, type ReactNode } from 'react';
import { downloadFile } from '../../api/client';
import { errorText } from '../../lib/forms';

/** Pulsante di download: scarica con le credenziali dell'account (funziona anche nella versione online). */
export function DownloadButton({ path, fallbackName, className = '', children, label, title }: {
  path: string; fallbackName?: string; className?: string; children: ReactNode; label?: string; title?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  return (
    <>
      <button type="button" disabled={busy} aria-label={label} title={err ?? title} className={`${className} ${busy ? 'opacity-60' : ''}`}
        onClick={async () => {
          setBusy(true);
          setErr(undefined);
          try { await downloadFile(path, fallbackName); } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
        }}>
        {children}
      </button>
      {err && <span role="alert" className="text-xs text-bad">{err}</span>}
    </>
  );
}
