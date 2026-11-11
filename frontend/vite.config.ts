/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';

const backend = process.env.NEXUS_BACKEND_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  // Runtime JSX di NEXUS: traduce l'interfaccia in inglese quando serve (src/i18n).
  plugins: [react({ jsxImportSource: 'nexus-i18n' }), tailwindcss()],
  resolve: {
    alias: {
      'nexus-i18n/jsx-runtime': fileURLToPath(new URL('./src/i18n/jsx-runtime.ts', import.meta.url)),
      'nexus-i18n/jsx-dev-runtime': fileURLToPath(new URL('./src/i18n/jsx-dev-runtime.ts', import.meta.url)),
    },
  },
  // È codice del progetto, non una dipendenza: niente pre-bundling (altrimenti in sviluppo resterebbe in cache).
  optimizeDeps: { exclude: ['nexus-i18n/jsx-runtime', 'nexus-i18n/jsx-dev-runtime'] },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: { '/api': { target: backend, changeOrigin: false } },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    proxy: { '/api': { target: backend, changeOrigin: false } },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
