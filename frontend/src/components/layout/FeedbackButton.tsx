import { MessageSquarePlus } from 'lucide-react';
import { useLocation } from 'react-router-dom';

export const FEEDBACK_EMAIL = 'mattiadinunzio5@gmail.com';

/** «Suggerisci / Segnala»: apre una email precompilata con la pagina corrente. */
export function feedbackHref(path: string): string {
  const subject = 'NEXUS — suggerimento o segnalazione';
  const body = `Pagina: ${path}\n\nCosa hai notato (errore, dato da correggere, idea)?\n\n`;
  return `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function FeedbackButton() {
  const { pathname } = useLocation();
  return (
    <a
      href={feedbackHref(pathname)}
      className="flex items-center gap-1.5 rounded p-1.5 text-xs text-steel-300 hover:bg-ink-800 hover:text-paper"
      title="Suggerisci un miglioramento o segnala un errore"
    >
      <MessageSquarePlus className="size-5" aria-hidden />
      <span className="hidden md:inline">Suggerisci</span>
      <span className="sr-only md:hidden">Suggerisci o segnala</span>
    </a>
  );
}
