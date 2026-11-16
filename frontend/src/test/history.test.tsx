import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { GraphData, Timeline } from '../api/types';
import { EventForm } from '../pages/History';
import { mockApi } from './fixtures';
import { renderApp } from './render';

describe('event form', () => {
  it('requires a start year and sends BCE years and lists correctly', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<EventForm onSubmit={onSubmit} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText('Titolo'), 'Idi di marzo');
    const year = screen.getByLabelText(/Anno inizio/);
    await userEvent.clear(year);
    await userEvent.click(screen.getByRole('button', { name: 'Salva evento' }));
    expect(screen.getByRole('alert')).toHaveTextContent("L'anno iniziale è obbligatorio");
    await userEvent.type(year, '-44');
    await userEvent.type(screen.getByLabelText(/Paesi/), 'Roma, Italia');
    await userEvent.click(screen.getByLabelText('Imperi e potenze economiche'));
    await userEvent.click(screen.getByRole('button', { name: 'Salva evento' }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ start_year: -44, countries: ['Roma', 'Italia'], categories: ['empires'], end_year: null }));
  });
});

const timeline: Timeline = {
  as_of_year: 1931,
  hindsight: false,
  hidden_future_events: 2,
  notes: ['Vista rigorosa al 1931: nascosti eventi successivi.'],
  indicators: [],
  events: [{
    id: 1, title: 'Crollo di Wall Street', date_label: '24 ott 1929', start_year: 1929, end_year: 1929, status_at_date: 'concluded',
    countries: [], categories: [], reliability: 'established', description: 'Crollo della borsa.', consequences: null, consequences_hidden: true,
    known_then: [{ id: 1, content: 'Vendite di panico.', known_since_year: 1929, kind: 'contemporary', source_id: null }], known_later: [], hidden_later_count: 1, is_demo: false,
  }],
};

describe('time machine', () => {
  it('shows only contemporary knowledge and declares what is hidden', async () => {
    const { calls } = mockApi({ 'GET /api/notifications': [], 'GET /api/history/timeline': timeline });
    renderApp('/time-machine?year=1931');
    expect(await screen.findByText('Crollo di Wall Street')).toBeInTheDocument();
    expect(screen.getByText('Vendite di panico.')).toBeInTheDocument();
    expect(screen.getByText(/Nascosto: conseguenze, 1 informazioni successive/)).toBeInTheDocument();
    expect(screen.getByText(/2 eventi successivi alla data sono nascosti/)).toBeInTheDocument();
    expect(calls.find((c) => c.url.startsWith('/api/history/timeline'))?.url).toContain('as_of_year=1931');
  });

  it('separates event, publication and availability dates and shows the completeness of the reconstruction', async () => {
    const t: Timeline = {
      ...timeline,
      indicators: [{ series_id: 3, name: 'PIL USA', unit: 'mld', source: 'BEA', last_date: '1930-01-01', last_value: 92, caveat: 'Ricostruzione a posteriori', retrospective: true, published: 2023, retrieved_at: '2026-01-01T00:00:00Z', availability: 'retrospective' }],
      events: [{ ...timeline.events[0],
        known_then: [{ id: 1, content: 'Vendite di panico.', known_since_year: 1929, kind: 'contemporary', source_id: 4, refers_to: '1929-10-24', published_on: '1929-10-25', available_on: '1929-10-25', source_citation: 'New York Times (1929).', availability: 'then' }],
        sources: [{ source_id: 4, citation: 'New York Times (1929).', year: 1929, pages: '1', evidence_class: 'primary', published_after: false }], date_precision: 'day' }],
      completeness: { score: 0.5, level: 'medium', method: 'Media di quattro componenti.', gaps: ['1 eventi senza informazioni datate.'],
        components: [{ key: 'sources', label: "Eventi con una fonte disponibile all'epoca", ok: 1, total: 2, ratio: 0.5 }] },
    };
    mockApi({ 'GET /api/notifications': [], 'GET /api/history/timeline': t });
    renderApp('/time-machine?year=1931');
    expect(await screen.findByText(/fatto: 1929-10-24 · pubblicata: 1929-10-25 · disponibile dal 1929-10-25/)).toBeInTheDocument();
    expect(screen.getAllByText(/New York Times \(1929\)/).length).toBeGreaterThan(0);
    const c = screen.getByTestId('completeness');
    expect(c).toHaveTextContent('50%');
    expect(c).toHaveTextContent('Ricostruzione parziale');
    expect(c).toHaveTextContent("Eventi con una fonte disponibile all'epoca: 1/2");
    expect(c).toHaveTextContent('1 eventi senza informazioni datate.');
    expect(screen.getByText(/dato del 1930-01-01, pubblicato nel 2023, scaricato il 2026-01-01/)).toBeInTheDocument();
  });
});

const graph: GraphData = {
  nodes: [
    { id: 1, name: 'Keynes', entity_type: 'person', x: -1, y: 0, degree: 1, betweenness: 0, is_focus: false },
    { id: 2, name: 'FMI', entity_type: 'institution', x: 1, y: 0, degree: 1, betweenness: 0, is_focus: false },
  ],
  edges: [{ id: 9, source_entity_id: 1, target_entity_id: 2, relation_type: 'influenced', provenance: 'ai_hypothesis', source_id: null, chunk_id: null, evidence_note: '', confidence: 'low', start_year: null, ai_run_id: 3, evidence_label: '', created_at: '' }],
  stats: { entities: 2, relations: 1, shown_nodes: 2, shown_edges: 1, components: 1, by_provenance: { sourced: 0, user_hypothesis: 0, ai_hypothesis: 1 } },
};

describe('knowledge graph', () => {
  it('renders nodes and edges with provenance stats', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/graph/entities': [], 'GET /api/sources': [], 'GET /api/graph': graph });
    renderApp('/graph');
    expect(await screen.findByRole('img', { name: 'Grafo con 2 entità e 1 relazioni' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Keynes' })).toBeInTheDocument();
    expect(screen.getByText(/ipotesi AI 1/)).toBeInTheDocument();
  });

  it('shows an explicit empty state', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/graph/entities': [], 'GET /api/sources': [], 'GET /api/graph': { ...graph, nodes: [], edges: [] } });
    renderApp('/graph');
    expect(await screen.findByText(/Il grafo è vuoto/)).toBeInTheDocument();
  });
});
