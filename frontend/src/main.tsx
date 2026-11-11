import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';
import { App } from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </BrowserRouter>
    {/* Statistiche di visita aggregate e senza cookie (Vercel Web Analytics): attive solo sul sito pubblicato. */}
    <Analytics />
  </StrictMode>,
);

// App installabile: il service worker si registra solo nella build di produzione e in contesto sicuro
// (HTTPS o localhost), come richiesto dai browser.
if (import.meta.env.PROD && 'serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => undefined);
  });
}
