import { lang, setLang } from '../../i18n';

/** Selettore della lingua dell'interfaccia (IT / EN). Le etichette non passano dal dizionario. */
export function LangSwitch({ className = '' }: { className?: string }) {
  const current = lang();
  return (
    <div role="group" aria-label={current === 'en' ? 'Language' : 'Lingua'} className={`inline-flex shrink-0 rounded-md border border-ink-700 p-0.5 text-[11px] font-semibold ${className}`}>
      {(['it', 'en'] as const).map((l) => (
        <button key={l} type="button" aria-pressed={current === l} onClick={() => { if (l !== current) setLang(l); }}
          className={`rounded px-1.5 py-0.5 ${current === l ? 'bg-ink-700 text-paper' : 'text-steel-400 hover:text-paper'}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
