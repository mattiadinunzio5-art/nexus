/** Solo link http(s): un URL salvato nei dati (fonte, serie, licenza) non deve poter eseguire codice (javascript:, data:…). */
export function safeHref(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  try {
    const u = new URL(url.trim(), 'https://invalid.local');
    return (u.protocol === 'https:' || u.protocol === 'http:') && /^https?:\/\//i.test(url.trim()) ? url.trim() : undefined;
  } catch {
    return undefined;
  }
}
