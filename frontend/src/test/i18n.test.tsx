import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { _setLangForTests, tr } from '../i18n';
import { EN } from '../i18n/en';
import { EN_RITOCCHI } from '../i18n/en-ritocchi';
import { mockApi } from './fixtures';
import { renderApp } from './render';

afterEach(() => _setLangForTests('it'));

describe('interfaccia in inglese', () => {
  it('translates exact texts, patterns with variable parts, and leaves user data alone', () => {
    _setLangForTests('en');
    expect(tr('Nuovo progetto')).toBe('New project');
    expect(tr(' Totale: ')).toBe(' Total: ');
    expect(tr('Sessione #12 · guidata')).toBe('Session #12 · guided');
    expect(tr('Notifiche (3 non lette)')).toBe('Notifications (3 unread)');
    expect(tr('Crollo di Wall Street')).toBe('Crollo di Wall Street');
    _setLangForTests('it');
    expect(tr('Nuovo progetto')).toBe('Nuovo progetto');
  });

  it('has no empty translations', () => {
    for (const [k, v] of Object.entries({ ...EN, ...EN_RITOCCHI })) expect(v.trim(), k).not.toBe('');
  });

  it('translates the texts added after phases 1-3', () => {
    _setLangForTests('en');
    expect(tr('Ambito:')).toBe('Scope:');
    expect(tr('Gratuito')).toBe('Free');
    expect(tr(' · si cambia dalla barra in alto')).toBe(' · change it from the bar at the top');
    expect(tr('ultimo controllo 16/11/2026 (manuale)')).toBe('last check 16/11/2026 (manual)');
    expect(tr('1200 parole · 14 citazioni')).toBe('1200 words · 14 citations');
    expect(tr(' · ripresa dalle fasi già completate (ricerca, analisi): nessun lavoro perso')).toBe(' · resumed from completed phases (ricerca, analisi): no work lost');
  });

  it('renders a whole page in English', async () => {
    _setLangForTests('en');
    mockApi({
      'GET /api/notifications': [],
      'GET /api/library/summary': { available: true, events: 18081, series: 3568, entities: 36193, relations: 18776, sources: 18500, documents: 10 },
    });
    renderApp('/start');
    expect(await screen.findByText('18,081')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Create your project' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Create a project/ })).toHaveAttribute('href', '/projects');
    expect(screen.getAllByText('Start here').length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText('Search projects and modules…')).toBeInTheDocument();
    expect(screen.queryByText(/Crea il tuo progetto/)).not.toBeInTheDocument();
  });
});
