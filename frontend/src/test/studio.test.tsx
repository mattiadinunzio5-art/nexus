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
    await userEvent.selectOptions(within(ins).getByLabelText('Fonte da citare'), '5');
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
