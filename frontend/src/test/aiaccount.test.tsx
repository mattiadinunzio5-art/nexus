import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AIAccountCard } from '../components/AIAccount';
import { mockApi } from './fixtures';

describe('AIAccountCard', () => {
  it('checks the key, lists the models and connects the account', async () => {
    const { calls } = mockApi({
      'GET /api/credentials/ai-accounts': [{ id: 'gemini', name: 'Google Gemini', key_url: 'https://aistudio.google.com/apikey', free: 'Piano gratuito.' }],
      'GET /api/credentials': [],
      'POST /api/credentials/ai-accounts/models': ['gemini-x-pro', 'gemini-x-flash'],
      'POST /api/credentials/ai-accounts/connect': { service: 'gemini', name: 'Google Gemini', model: 'gemini-x-flash' },
    });
    const onChange = vi.fn();
    render(<AIAccountCard onChange={onChange} />);
    await userEvent.click(await screen.findByRole('radio', { name: 'Google Gemini' }));
    await userEvent.type(screen.getByLabelText('2. Incolla la chiave API'), 'abc');
    await userEvent.click(screen.getByRole('button', { name: 'Verifica la chiave' }));
    await userEvent.selectOptions(await screen.findByLabelText('3. Scegli il modello'), 'gemini-x-flash');
    await userEvent.click(screen.getByRole('button', { name: 'Collega e usa' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Google Gemini collegato');
    expect(calls.find((c) => c.url.endsWith('/connect'))?.body).toEqual({ service: 'gemini', key: 'abc', model: 'gemini-x-flash' });
    expect(onChange).toHaveBeenCalled();
  });
});
