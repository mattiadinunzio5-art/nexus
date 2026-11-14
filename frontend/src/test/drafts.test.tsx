import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { Report } from '../api/types';
import { mockApi } from './fixtures';
import { renderApp } from './render';

// Ciò che si scrive in un modulo non deve perdersi passando a un'altra sezione e tornando indietro.
describe('drafts survive navigation', () => {
  it('keeps the document title and author typed before switching module', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/documents': [], 'GET /api/sources': [] });
    renderApp('/documents');
    await userEvent.type(await screen.findByLabelText('Titolo (facoltativo)'), 'Rapporto CRS');
    await userEvent.type(screen.getByLabelText('Autore (facoltativo)'), 'Tarnoff');
    await userEvent.click(screen.getByRole('link', { name: 'Bibliography' }));
    expect(await screen.findByRole('heading', { name: 'Bibliography' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('link', { name: 'Documents' }));
    expect(await screen.findByLabelText('Titolo (facoltativo)')).toHaveValue('Rapporto CRS');
    expect(screen.getByLabelText('Autore (facoltativo)')).toHaveValue('Tarnoff');
  });

  it('keeps an unsaved report section until it is saved', async () => {
    const report: Report = {
      id: 3, title: 'R', subtitle: '', author: '', status: 'draft', project_id: null, source_ids: [], origin: 'manual', contains_ai_text: false,
      citation_style: 'numeric', template: 'standard', created_at: '', updated_at: '',
      sections: [{ id: 1, ordinal: 0, key: 'abstract', title: 'Abstract', body: '', embeds: [] }],
    };
    const check = { ready: false, checklist: [], empty_sections: [], invalid_citations: [], unverified_sources: [], cited_sources: 0, bibliography_size: 0, embed_problems: [], warnings: [] };
    mockApi({ 'GET /api/notifications': [], 'GET /api/sources': [], 'GET /api/reports/3': report, 'GET /api/reports/3/check': check, 'GET /api/documents': [] });
    const first = renderApp('/studio/reports/3');
    const sec = await screen.findByTestId('section-abstract');
    await userEvent.type(within(sec).getByLabelText('Testo: Abstract'), 'Bozza non salvata');
    expect(within(sec).getByText(/Modifiche non salvate/)).toBeInTheDocument();
    first.unmount(); // come uscire dalla pagina
    renderApp('/studio/reports/3');
    const again = await screen.findByTestId('section-abstract');
    expect(within(again).getByLabelText('Testo: Abstract')).toHaveValue('Bozza non salvata');
  });
});
