import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const conn = {
  id: 4, session_id: 1, kind: 'shared_actors', kind_label: 'Attori condivisi', title: 'Fine di Bretton Woods ↔ Crisi del dollaro',
  elements: [{ type: 'event', id: 1, label: 'Fine di Bretton Woods' }, { type: 'event', id: 2, label: 'Crisi del dollaro' }], period: '1971–1973',
  evidence: [{ kind: 'actors', label: 'Attori comuni', detail: 'Federal Reserve' }], sources: [3], reliability: 'medium',
  reliability_reasons: ['1 fonti, 1 indipendenti'], explanation: 'Gli stessi attori compaiono in entrambi gli eventi.',
  caveats: ['La connessione non dimostra un rapporto di causa-effetto: va verificata.'], score: 3, status: 'new', graph_relation_id: null, created_at: '2026-11-07T10:00:00Z',
};
const hyp = {
  id: 9, session_id: 1, connection_id: 4, title: 'Bretton Woods e crisi del dollaro sono collegati', description: 'Ipotesi.\n\nNon è una scoperta dimostrata.',
  phenomena: ['Fine di Bretton Woods', 'Crisi del dollaro'], motivation: 'Connessione', supporting: ['Attori comuni: Federal Reserve'], contrary: ['Fonte unica'],
  missing: ['Una fonte esplicita'], method: ['Cercare passaggi nei documenti'], confidence: 'low', status: 'verifying', archived: false,
  verification: [{ at: '2026-11-07T10:00:00Z', suggested: 'inconclusive', checks: [{ check: 'Passaggi nei documenti', outcome: 'nothing_found', detail: 'Nessun passaggio.' }] }],
  decision_note: '', decided_at: null, origin: 'rules', graph_entity_id: null, created_at: '2026-11-07T10:00:00Z',
};

describe('discovery intelligence', () => {
  it('dashboard warns honestly when the archive is empty and starts an autonomous session', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/discovery/overview': {
        connections: 0, connections_new: 0, hypotheses: 0, hypotheses_by_status: { to_verify: 0, verifying: 0, confirmed: 0, rejected: 0, inconclusive: 0 },
        anomalies_open: 0, running: [], latest_connections: [], latest_hypotheses: [], latest_anomalies: [], archive: { events: 0, series: 0, entities: 0 },
      },
      'POST /api/discovery/sessions': { id: 5, mode: 'autonomous', status: 'queued' },
      'GET /api/discovery/sessions/5': {
        id: 5, mode: 'autonomous', query: '', status: 'completed', cursor: 7, steps_total: 7, plan: ['Esame delle conoscenze disponibili'], scope: {},
        steps: [{ ordinal: 1, step: 'survey', label: 'Esame delle conoscenze disponibili', status: 'executed', executor: 'local', summary: 'Archivio: 0 eventi', counts: {}, error: null, duration_ms: 3, model: '' }],
        result: { synthesis: { text: 'L’archivio non contiene ancora abbastanza materiale.', executor: 'local', references: [] }, leads: [] },
        limits: { max_seconds: 120, max_items: 60, max_llm_calls: 0, provider: 'none' }, llm_calls: 0, elapsed_ms: 10, error: null, created_at: '2026-11-07T10:00:00Z',
      },
      'GET /api/discovery/sessions': [],
    });
    renderApp('/discovery');
    expect(await screen.findByText(/L'archivio è vuoto/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Discovery autonoma/ }));
    expect(await screen.findByText(/non contiene ancora abbastanza materiale/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST' && c.url === '/api/discovery/sessions')?.body).toEqual({ mode: 'autonomous', query: '' });
    expect(screen.getByText(/AI non configurata: sintesi locale/)).toBeInTheDocument();
  });

  it('connection detail shows evidence and caveats and saves to the graph only as a hypothesis', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/discovery/connections/4': conn,
      'POST /api/discovery/connections/4/status': { ...conn, status: 'accepted', graph_relation_id: 12 },
    });
    renderApp('/discovery/connections/4');
    expect(await screen.findByText('Federal Reserve')).toBeInTheDocument();
    expect(screen.getByText(/non dimostra un rapporto di causa-effetto/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Accetta/ }));
    expect(await screen.findByText(/come ipotesi \(non come relazione documentata\)/)).toBeInTheDocument();
    expect(calls.find((c) => c.url.endsWith('/status'))?.body).toEqual({ status: 'accepted' });
  });

  it('hypothesis decision requires the user and shows the verification checks', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/discovery/hypotheses/9': hyp,
      'POST /api/discovery/hypotheses/9/decision': { ...hyp, status: 'inconclusive', decision_note: 'Mancano fonti', decided_at: '2026-11-07T11:00:00Z' },
    });
    renderApp('/discovery/hypotheses/9');
    expect(await screen.findByText('Nessun passaggio.')).toBeInTheDocument();
    expect(screen.getByText(/solo un suggerimento/)).toBeInTheDocument();
    const card = screen.getByRole('heading', { name: /Esito \(deciso da te\)/ }).closest('section')!;
    await userEvent.type(within(card).getByLabelText(/Motivazione/), 'Mancano fonti');
    await userEvent.click(within(card).getByRole('button', { name: 'Registra' }));
    expect(await screen.findByText('Esito registrato.')).toBeInTheDocument();
    expect(calls.find((c) => c.url.endsWith('/decision'))?.body).toEqual({ status: 'inconclusive', note: 'Mancano fonti' });
  });

  it('is reachable from the main navigation', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/discovery/overview': new Response('{}', { status: 500 }) });
    renderApp('/discovery/anomalies');
    expect(screen.getAllByRole('link', { name: /Discovery Intelligence/ })[0]).toHaveAttribute('href', '/discovery');
  });
});
