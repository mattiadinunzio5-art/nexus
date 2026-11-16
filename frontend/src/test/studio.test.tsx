import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { Briefing, Report } from '../api/types';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const keys = ['abstract', 'introduction', 'methodology', 'analysis', 'evidence', 'counterarguments', 'conclusions', 'limitations'];
const report: Report = {
  id: 2, title: 'Debito pubblico', subtitle: '', author: '', status: 'draft', project_id: null, source_ids: [], origin: 'manual', contains_ai_text: false, citation_style: 'footnotes', template: 'thesis',
  created_at: '', updated_at: '2026-11-03T10:00:00Z',
  sections: keys.map((k, i) => ({ id: i + 1, ordinal: i, key: k, title: k, body: k === 'analysis' ? 'Testo [@1]' : '', embeds: [] })),
};
const check = { ready: false, checklist: [
  { key: 'sections', label: 'Tutte le sezioni sono compilate', ok: false, blocking: true, detail: 'abstract' },
  { key: 'cited', label: 'Il testo cita le fonti', ok: true, blocking: false, detail: '1 fonti citate' },
], empty_sections: ['abstract'], invalid_citations: [7], unverified_sources: [], cited_sources: 1, bibliography_size: 1, embed_problems: [], warnings: [] };

describe('research studio', () => {
  it('reviews a section and shows the quoted sentences', async () => {
    const long = { ...report, sections: report.sections.map((x) => (x.key === 'analysis' ? { ...x, body: 'La produzione è cresciuta da 2 a 400 milioni di tonnellate. Questo dimostra tutto.' } : x)) };
    mockApi({
      'GET /api/notifications': [], 'GET /api/sources': [], 'GET /api/reports/2/check': check, 'GET /api/reports/2': long,
      'POST /api/reports/2/sections/4/review': { mode: 'local', provider: 'none', note: 'Controlli locali.', issues: [
        { kind: 'uncited', quote: 'La produzione è cresciuta da 2 a 400 milioni di tonnellate.', comment: 'Dato senza fonte.' }] },
    });
    renderApp('/studio/reports/2');
    const analysis = await screen.findByTestId('section-analysis');
    await userEvent.click(within(analysis).getByText('Revisione'));
    const panel = await within(analysis).findByTestId('review-panel');
    expect(panel).toHaveTextContent('Senza citazione');
    expect(panel).toHaveTextContent('Dato senza fonte.');
  });

  it('shows the delivery checklist, layout settings and inserts a citation at the cursor', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/reports/2/check': check, 'GET /api/reports/2': report,
      'GET /api/sources': [{ id: 5, citation: 'Tarnoff, Curt. (2018). The Marshall Plan.', verification_status: 'verified_user' }],
      'PATCH /api/reports/2': { ...report, citation_style: 'author_date' },
    });
    renderApp('/studio/reports/2');
    const list = await screen.findByTestId('checklist');
    expect(within(list).getByText('Tutte le sezioni sono compilate')).toBeInTheDocument();
    expect(screen.getByText(/Prima della consegna · 1\/2/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Stile delle citazioni'), 'author_date');
    expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ citation_style: 'author_date' });
    const analysis = screen.getByTestId('section-analysis');
    await userEvent.click(within(analysis).getByText('Inserisci citazione'));
    const ins = within(analysis).getByTestId('cite-inserter');
    await userEvent.type(within(ins).getByRole('combobox', { name: 'Fonte da citare' }), 'Tarn');
    await userEvent.click((await within(ins).findAllByRole('option', { name: /The Marshall Plan/ }))[0]);
    await userEvent.type(within(ins).getByLabelText('Pagina'), 'p. 9');
    await userEvent.click(within(ins).getByRole('button', { name: /Inserisci/ }));
    expect(within(analysis).getByLabelText('Testo: analysis')).toHaveValue('Testo [@1] [@5, p. 9]');
  });


  it('saves an edited section and blocks approval with a readable error', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/sources': [], 'GET /api/reports/2/check': check, 'GET /api/reports/2': report,
      'PUT /api/reports/2/sections/1': { ...report, sections: report.sections.map((s) => (s.id === 1 ? { ...s, body: 'Nuovo abstract' } : s)) },
      'POST /api/reports/2/status': new Response(JSON.stringify({ error: { code: 'validation_error', message: 'Il rapporto non può essere approvato.' } }), { status: 422 }),
    });
    renderApp('/studio/reports/2');
    const abstract = await screen.findByTestId('section-abstract');
    await userEvent.type(within(abstract).getByRole('textbox'), 'Nuovo abstract');
    await userEvent.click(within(abstract).getByRole('button', { name: 'Salva sezione' }));
    expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({ body: 'Nuovo abstract', embeds: [] });
    await userEvent.click(screen.getByRole('button', { name: 'Approva' }));
    expect(await screen.findByText('Il rapporto non può essere approvato.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /PDF/ })).toBeInTheDocument();
  });

  it('renders a briefing with dates, sources and explicit empty sections', async () => {
    const b: Briefing = { id: 1, trigger: 'manual', created_at: '', content: { date: '2026-11-03', generated_at: '', refresh: [], notes: [], sections: [
      { key: 'macro', title: 'Indicatori macroeconomici', empty_reason: null, items: [{ title: 'Inflazione Italia', value: 1.5, unit: '%', date: '2025-01-01', source: 'World Bank', flags: ['Ultimo dato del 2025-01-01: la serie potrebbe non essere aggiornata.'] }] },
      { key: 'geopolitics', title: 'Eventi geopolitici', items: [], empty_reason: 'NEXUS non dispone di una fonte di notizie correnti.' },
    ] } };
    mockApi({ 'GET /api/notifications': [], 'GET /api/briefings': [b] });
    renderApp('/briefing');
    const el = await screen.findByTestId('briefing');
    expect(within(el).getByText(/Fonte: World Bank/)).toBeInTheDocument();
    expect(within(el).getByText(/Data: 2025-01-01/)).toBeInTheDocument();
    expect(within(el).getByText(/potrebbe non essere aggiornata/)).toBeInTheDocument();
    expect(within(el).getByText('NEXUS non dispone di una fonte di notizie correnti.')).toBeInTheDocument();
  });
});

describe('research studio: tracciabilità e versioni', () => {
  const trace = {
    report_id: 2,
    summary: { claims: 3, supported: 1, paragraph: 1, unsupported: 1, invalid: 0, exempt: 0, with_page: 1, citations: 2, primary_cited: 1, secondary_cited: 0, unclassified_cited: 0, unused: 1 },
    sections: [{ section_id: 4, key: 'analysis', title: 'analysis', claims: [
      { paragraph: 0, text: 'Gli aiuti furono 1.204 milioni.', status: 'supported', citations: [{ source_id: 1, locator: 'p. 12', has_page: true, valid: true, evidence_class: 'primary' }] },
      { paragraph: 0, text: 'La produzione crebbe del 40% nel 1952.', status: 'unsupported', citations: [] },
    ] }],
    bibliography: [
      { source_id: 1, number: 1, citation: 'Rossi (1950). Archivio.', status: 'cited', evidence_class: 'primary', verification_status: 'verified_user', verified: true, locators: ['p. 12'] },
      { source_id: 6, number: 2, citation: 'Bianchi (1990). Sintesi.', status: 'unused', evidence_class: 'secondary', verification_status: 'unverified', verified: false, locators: [] },
    ],
    invalid_citations: [],
    coherence: [{ section: 'analysis', kind: 'value', detail: 'Nel testo 1951: 62; nel grafico «Debito»: 58.4.' }],
  };

  it('highlights unsupported claims, coherence issues and marks a source as consulted', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/sources': [], 'GET /api/reports/2/check': check, 'GET /api/reports/2/trace': trace, 'GET /api/reports/2': report,
      'PATCH /api/reports/2': { ...report, source_ids: [6], consulted_ids: [6] },
    });
    renderApp('/studio/reports/2');
    expect(await screen.findByTestId('trace-summary')).toHaveTextContent('1 senza supporto');
    const claims = screen.getByTestId('trace-claims');
    expect(claims).toHaveTextContent('La produzione crebbe del 40% nel 1952.');
    expect(claims).not.toHaveTextContent('1.204 milioni');
    await userEvent.click(screen.getByLabelText('Mostra anche le affermazioni supportate'));
    expect(screen.getByTestId('trace-claims')).toHaveTextContent('@1, p. 12 · primaria');
    expect(screen.getByTestId('trace-coherence')).toHaveTextContent('58.4');
    const bib = screen.getByTestId('trace-bibliography');
    expect(bib).toHaveTextContent('Né citata né consultata');
    await userEvent.click(within(bib).getByLabelText('consultata'));
    expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ consulted_ids: [6] });
  });

  it('lists section versions and restores one', async () => {
    const restored = { ...report, sections: report.sections.map((x) => (x.key === 'analysis' ? { ...x, body: 'Prima stesura.' } : x)) };
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/sources': [], 'GET /api/reports/2/check': check, 'GET /api/reports/2/trace': trace,
      'GET /api/reports/2/sections/4/versions': [{ id: 11, created_at: '2026-11-14T09:00:00Z', reason: 'edit', title: 'analysis', body: 'Prima stesura.', embeds: [], words: 2, author: 'Anna' }],
      'POST /api/reports/2/sections/4/versions/11/restore': restored,
      'GET /api/reports/2': report,
    });
    renderApp('/studio/reports/2');
    const analysis = await screen.findByTestId('section-analysis');
    await userEvent.click(within(analysis).getByText('Cronologia'));
    const versions = await within(analysis).findByTestId('versions');
    expect(versions).toHaveTextContent('modifica · 2 parole · Anna');
    await userEvent.click(within(versions).getByText('Ripristina'));
    expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/versions/11/restore'))).toBe(true);
    expect(await within(analysis).findByDisplayValue('Prima stesura.')).toBeInTheDocument();
  });
});
