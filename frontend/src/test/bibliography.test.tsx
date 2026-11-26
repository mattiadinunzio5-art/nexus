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

  it('explains the assessment of a source only when opened', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/projects': [], 'GET /api/sources': [mismatch], 'GET /api/projects/linked/source/9': [],
      'GET /api/sources/9/assessment': {
        source_id: 9, authority: 'medium', originality: 'secondary', identity: 'doubtful', timing: null, verified: false, qualified: false,
        doubtful: true, aggregator: null, year: 2000,
        reasons: ["Metadati: DOI trovato ma i metadati del registro non corrispondono alla scheda: identità dell'opera dubbia",
          'Autorevolezza: pubblicazione editoriale o accademica (editore non riconosciuto come istituzionale)'],
        content_note: "Contenuto: NEXUS non controlla che le fonti sostengano l'affermazione.",
      },
    });
    renderApp('/bibliography');
    const box = await screen.findByTestId('source-assessment');
    expect(calls.some((c) => c.url.includes('/assessment'))).toBe(false);
    await userEvent.click(within(box).getByText('Valutazione della fonte: perché'));
    expect(await within(box).findByText(/identità dell'opera dubbia/)).toBeInTheDocument();
    expect(within(box).getByText(/NEXUS non controlla che le fonti sostengano/)).toBeInTheDocument();
  });

  it('does not crash on a source with empty verification details', async () => {
    const empty = { id: 11, title: 'Address at Harvard University', citation: 'Marshall (1947). Address at Harvard University.', verification_status: 'unverified',
      verification_note: '', doi: '', authors: ['George C. Marshall'], verification_details: {} };
    mockApi({ 'GET /api/notifications': [], 'GET /api/projects': [], 'GET /api/sources': [empty, mismatch], 'GET /api/projects/linked/source': [] });
    renderApp('/bibliography');
    expect(await screen.findByText('Marshall (1947). Address at Harvard University.')).toBeInTheDocument();
    expect(screen.getByText('Pomeranz (2011). Titolo sbagliato.')).toBeInTheDocument();
    expect(screen.getAllByTestId('verification-details')).toHaveLength(1);
  });

  it('shows the result of a verification next to the source', async () => {
    const plain = { id: 12, title: 'CRS R45079', citation: 'CRS (2018). The Marshall Plan.', verification_status: 'unverified', verification_note: '', doi: '', authors: [] };
    const { calls } = mockApi({ 'GET /api/notifications': [], 'GET /api/projects': [], 'GET /api/sources': [plain], 'GET /api/projects/linked/source': [],
      'POST /api/sources/12/verify': { ...plain, verification_status: 'verified_user' } });
    renderApp('/bibliography');
    const item = (await screen.findByText('CRS (2018). The Marshall Plan.')).closest('li')!;
    await userEvent.click(within(item).getByRole('button', { name: /verificato l'originale/i }));
    expect(await within(item).findByText(/fonte segnata come controllata/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'POST' && c.url.includes('/sources/12/verify'))).toBe(true);
  });

  it('shows a verification error next to the source', async () => {
    const plain = { id: 13, title: 'X', citation: 'X (2000). Una fonte.', verification_status: 'unverified', verification_note: '', doi: '', authors: [] };
    mockApi({ 'GET /api/notifications': [], 'GET /api/projects': [], 'GET /api/sources': [plain], 'GET /api/projects/linked/source': [],
      'POST /api/sources/13/verify': () => new Response(JSON.stringify({ error: { code: 'validation_failed', message: 'Non permesso.' } }), { status: 422 }) });
    renderApp('/bibliography');
    const item = (await screen.findByText('X (2000). Una fonte.')).closest('li')!;
    await userEvent.click(within(item).getByRole('button', { name: /verificato l'originale/i }));
    expect(await within(item).findByRole('alert')).toBeInTheDocument();
  });
});
