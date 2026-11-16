import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const mismatch = {
  id: 9, title: 'Titolo sbagliato', citation: 'Pomeranz (2011). Titolo sbagliato.', verification_status: 'registry_mismatch',
  verification_note: 'DOI trovato ma metadati discordanti: titolo, anno.', doi: '10.1000/abc', authors: ['Kenneth Pomeranz'],
  evidence_class: 'secondary', license: 'CC BY 4.0', provenance: "Inserita manualmente dall'utente",
  verification_details: {
    registry: 'Crossref', registry_url: 'https://api.crossref.org/works/10.1000/abc', checked_at: '2026-11-15T10:00:00Z', doi_exists: true,
    fields: {
      doi: { status: 'match', local: '10.1000/abc', registry: '10.1000/abc', label: 'DOI' },
      title: { status: 'mismatch', local: 'Titolo sbagliato', registry: 'The Great Divergence', label: 'titolo' },
      year: { status: 'mismatch', local: 2011, registry: 2000, label: 'anno' },
    },
  },
};

describe('bibliografia: verifica campo per campo', () => {
  it('distinguishes an existing DOI from a matching reference', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/projects': [], 'GET /api/sources': [mismatch], 'GET /api/projects/linked/source/9': [] });
    renderApp('/bibliography');
    expect(await screen.findByText('DOI trovato, metadati discordanti')).toBeInTheDocument();
    const d = screen.getByTestId('verification-details');
    expect(d).toHaveTextContent('DOI esistente · confronto con Crossref del 2026-11-15');
    await userEvent.click(within(d).getByText(/DOI esistente/));
    const row = within(d).getByText('anno').closest('tr')!;
    expect(row).toHaveTextContent('2011');
    expect(row).toHaveTextContent('2000');
    expect(row).toHaveTextContent('discordante');
    expect(screen.getByText(/Fonte secondaria/)).toBeInTheDocument();
    expect(screen.getByText(/Licenza: CC BY 4.0/)).toBeInTheDocument();
  });
});
