import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const doc = { id: 3, title: 'Relazione 1948', filename: 'r.pdf', kind: 'pdf', category: 'source_material', origin: 'upload', origin_url: '', license_note: '', author: '', year: null,
  sha256: 'x', size_bytes: 100, page_count: 1, char_count: 10, chunk_count: 1, flagged_chunks: 0, project_id: null, source_id: 1, is_demo: false, created_at: '2026-11-01T10:00:00Z' };

describe('documenti: cestino', () => {
  it('moves a document to the trash, says until when it is recoverable and restores it', async () => {
    let trash: unknown[] = [];
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/projects': [],
      'GET /api/documents/trash': () => trash,
      'GET /api/documents': [doc],
      'DELETE /api/documents/3': () => { trash = [{ id: 7, document_id: 3, title: 'Relazione 1948', filename: 'r.pdf', kind: 'pdf', size_bytes: 100, deleted_at: '2026-11-15T10:00:00Z', purge_after: '2026-12-15T10:00:00Z', recoverable: true }];
        return { deleted: true, storage_verified: true, trash_id: 7, recoverable: true, recoverable_until: '2026-12-15T10:00:00Z' }; },
      'POST /api/documents/trash/7/restore': () => { trash = []; return doc; },
    });
    renderApp('/documents');
    await userEvent.click(await screen.findByRole('button', { name: 'Elimina Relazione 1948' }));
    await userEvent.click(screen.getByRole('button', { name: 'Sposta nel cestino' }));
    expect(await screen.findByRole('status')).toHaveTextContent('verificata sullo storage');
    const t = await screen.findByTestId('trash');
    expect(t).toHaveTextContent('recuperabile fino al');
    await userEvent.click(within(t).getByRole('button', { name: 'Ripristina' }));
    expect(await screen.findByText(/ripristinato \(contenuto verificato\)/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'POST' && c.url === '/api/documents/trash/7/restore')).toBe(true);
  });
});
