import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { SearchPicker } from '../components/ui/SearchPicker';
import { mockApi } from './fixtures';

describe('SearchPicker', () => {
  it('lists own items before the library, shows full text and searches the library only with a query', async () => {
    const long = 'Geyer, Roland; Jambeck, Jenna R.; Law, Kara Lavender. (2017). Production, use, and fate of all plastics ever made. Science Advances, 3(7).';
    const { calls } = mockApi({
      'GET /api/sources': (url: string) => (url.includes('origin=library')
        ? [{ id: 9, citation: 'OECD (2022). Global Plastics Outlook.' }]
        : [{ id: 3, citation: long }]),
    });
    const onChange = vi.fn();
    render(<SearchPicker kind="source" ariaLabel="Fonte" value="" onChange={onChange} />);
    const box = screen.getByRole('combobox', { name: 'Fonte' });
    await userEvent.click(box);
    expect(await screen.findByRole('option', { name: long })).toBeInTheDocument();
    expect(calls.some((c) => c.url.includes('origin=library'))).toBe(false);
    await userEvent.type(box, 'pl');
    const lib = await screen.findByRole('option', { name: /Global Plastics Outlook/ });
    const opts = screen.getAllByRole('option');
    expect(opts.indexOf(lib)).toBeGreaterThan(opts.findIndex((o) => o.textContent?.includes('Geyer')));
    await userEvent.click(lib);
    expect(onChange).toHaveBeenCalledWith('9', 'OECD (2022). Global Plastics Outlook.');
  });
});
