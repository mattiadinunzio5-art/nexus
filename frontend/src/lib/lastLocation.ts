/** Ultimi parametri di ricerca usati in ogni pagina del menu (solo per la sessione del browser). */
const KEY = 'nexus.lastSearch';

function read(): Record<string, string> {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? '{}') as Record<string, string>;
  } catch {
    return {};
  }
}

export function rememberSearch(pathname: string, search: string): void {
  try {
    const m = read();
    if (search) m[pathname] = search;
    else delete m[pathname];
    sessionStorage.setItem(KEY, JSON.stringify(m));
  } catch {
    /* storage non disponibile */
  }
}

export function rememberedSearch(path: string): string {
  if (path === '/') return '';
  const s = read()[path] ?? '';
  // La demo si apre una volta sola: non va riproposta tornando alla pagina.
  return s.includes('demo=') ? '' : s;
}
