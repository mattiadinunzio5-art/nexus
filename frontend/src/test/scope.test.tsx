import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockApi, project } from './fixtures';
import { renderApp } from './render';

describe('ambito di progetto', () => {
  it('filters lists by the active project and links items to it', async () => {
    let linked: number[] = [];
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/projects': [project],
      'GET /api/sources': [{ id: 5, title: 'Plastics', citation: 'Geyer (2017). Plastics.', verification_status: 'unverified', library: true }],
      'GET /api/projects/linked/source/5': () => linked,
      'POST /api/projects/7/items': () => { linked = [7]; return { linked: true }; },
    });
    renderApp('/bibliography');
    await screen.findByRole('option', { name: project.title });
    await userEvent.selectOptions(screen.getByLabelText('Progetto attivo'), '7');
    await waitFor(() => expect(calls.some((c) => c.url.startsWith('/api/sources') && c.url.includes('project_id=7'))).toBe(true));
    expect(screen.getByRole('radio', { name: 'Solo progetto' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByTestId('scope-note')).toHaveTextContent(`Solo il progetto «${project.title}»`);
    await userEvent.click(await screen.findByRole('button', { name: /Aggiungi al progetto/ }));
    expect(calls.find((c) => c.method === 'POST' && c.url === '/api/projects/7/items')?.body).toEqual({ item_type: 'source', item_id: 5 });
    expect(await screen.findByRole('button', { name: /Nel progetto/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: 'Solo Biblioteca' }));
    await waitFor(() => expect(calls.some((c) => c.url.startsWith('/api/sources') && c.url.includes('origin=library'))).toBe(true));
  });
});
