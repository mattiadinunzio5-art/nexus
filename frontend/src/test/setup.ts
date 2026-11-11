import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { _setLangForTests } from '../i18n';

// I test dell'interfaccia sono scritti in italiano (lingua dei testi nel codice), qualunque sia la lingua del sistema.
_setLangForTests('it');

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// jsdom non implementa ResizeObserver (usato dai grafici Recharts).
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver ??= ResizeObserverStub;
