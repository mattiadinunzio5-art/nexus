import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockApi } from './fixtures';
import { renderApp } from './render';

describe('inizia da qui', () => {
  it('explains the three steps with the real Library numbers and is in the main navigation', async () => {
    mockApi({
      'GET /api/notifications': [],
      'GET /api/library/summary': { available: true, events: 18081, series: 3568, entities: 36193, relations: 18776, sources: 18500, documents: 10 },
    });
    renderApp('/start');
    expect(await screen.findByText('18.081')).toBeInTheDocument();
    expect(screen.getByText('3568')).toBeInTheDocument();
    for (const step of ['Esplora la Biblioteca NEXUS', 'Crea il tuo progetto', 'Collega, verifica, scrivi']) {
      expect(screen.getByRole('heading', { name: step })).toBeInTheDocument();
    }
    expect(screen.getByRole('link', { name: /Crea un progetto/ })).toHaveAttribute('href', '/projects');
    expect(screen.getAllByRole('link', { name: /Inizia da qui/ })[0]).toHaveAttribute('href', '/start');
  });

  it('works without a Library', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/library/summary': { available: false } });
    renderApp('/start');
    expect(await screen.findByRole('heading', { name: 'Crea il tuo progetto' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Contenuto della Biblioteca')).not.toBeInTheDocument();
  });
});
