import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockApi, project } from './fixtures';
import { renderApp } from './render';

const lesson = {
  id: 'crisi-2008', title: 'La crisi finanziaria del 2008', level: 'Intermedio', duration: 'circa 4 ore', summary: 'Dalla bolla immobiliare a Lehman.',
  goals: ['Ricostruire la sequenza'], key_dates: [{ date: '2008-09-15', event: 'Lehman Brothers presenta istanza di fallimento' }],
  series: [{ label: 'Tasso BCE', category: 'rates', params: { connector: 'ecb', dataset: 'FM', key: 'B.U2.EUR.4F.KR.MRR_FR.LEV' } }],
  readings: [{ title: 'The Financial Crisis Inquiry Report', authors: ['Financial Crisis Inquiry Commission'], year: 2011, publisher: 'U.S. GPO' }],
  steps: [{ title: 'Importa i dati', detail: 'Importa le serie.', module: '/financial' }],
};

describe('guided lessons', () => {
  it('lists lessons, starts one and imports a suggested series', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/lessons/crisi-2008': lesson,
      'GET /api/lessons': [lesson],
      'POST /api/lessons/crisi-2008/start': { project_id: 9, note_id: 1, sources_added: 1 },
      'POST /api/finance/series/import': { id: 4, observation_count: 48 },
    });
    renderApp('/lessons');
    await userEvent.click(await screen.findByRole('link', { name: /La crisi finanziaria del 2008/ }));
    expect(await screen.findByText(/Lehman Brothers presenta/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Inizia la lezione/ }));
    expect(await screen.findByText(/1 letture da verificare/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Importa/ }));
    expect(await screen.findByText('Importata: 48 osservazioni.')).toBeInTheDocument();
    expect(calls.find((c) => c.url === '/api/finance/series/import')?.body).toEqual({ category: 'rates', connector: 'ecb', dataset: 'FM', key: 'B.U2.EUR.4F.KR.MRR_FR.LEV' });
  });
});

describe('project collaboration', () => {
  it('shows comments and history and posts a comment', async () => {
    const comments = [{ id: 1, project_id: 7, body: 'Manca la fonte', created_at: '2026-11-05T10:00:00Z', author: { user_id: 2, display_name: 'Bruno' } }];
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/auth/config': { mode: 'local', allow_registration: false },
      'GET /api/projects/7/comments': comments,
      'GET /api/projects/7/history': [{ id: 3, action: 'project.share', summary: 'Progetto condiviso con bruno@example.org', actor: 'user', created_at: '2026-11-05T09:00:00Z', user: 'Anna' }],
      'POST /api/projects/7/comments': { id: 2, project_id: 7, body: 'Aggiunta', created_at: '2026-11-05T11:00:00Z', author: { user_id: 1, display_name: 'Anna' } },
      'GET /api/projects': [project],
    });
    renderApp('/projects');
    await userEvent.click(await screen.findByRole('button', { name: `Commenti e cronologia di ${project.title}` }));
    expect(await screen.findByText('Manca la fonte')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Nuovo commento'), 'Aggiunta');
    await userEvent.click(screen.getByRole('button', { name: 'Invia' }));
    expect(calls.some((c) => c.method === 'POST' && c.url === '/api/projects/7/comments')).toBe(true);
    await userEvent.click(screen.getByRole('tab', { name: 'Cronologia' }));
    expect(await screen.findByText(/Progetto condiviso con bruno/)).toBeInTheDocument();
  });
});
