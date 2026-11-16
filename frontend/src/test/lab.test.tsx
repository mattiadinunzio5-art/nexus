import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { SimulationRun } from '../api/types';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const sim: SimulationRun = {
  id: 9, kind: 'debt', title: 'Dinamica del debito pubblico', params: {}, counterfactual: true, created_at: '2026-11-03T10:00:00Z',
  result: {
    kind: 'debt', title: 'Dinamica del debito pubblico', hypotheses: ['Nessun effetto di retroazione'], variables: { d: 'debito/PIL' }, parameters: { d0: 135 },
    method: 'd(t+1) = d(t)·(1+r)/(1+g) − pb', data_used: ["Parametri inseriti dall'utente"], limitations: ['Modello contabile'], counterfactual: true,
    label: 'Scenario ipotetico (controfattuale): non è una ricostruzione della storia.', warnings: [],
    results: { years: [0, 1], baseline: { debt: [135, 136] }, debt_stabilizing_primary_balance: 1.3 },
  },
};

describe('economic lab', () => {
  it('shows the counterfactual label and the full methodological record', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/lab/simulations/9': sim });
    renderApp('/lab/simulations/9');
    expect(await screen.findByRole('note')).toHaveTextContent('controfattuale');
    for (const t of ['Nessun effetto di retroazione', 'd(t+1) = d(t)·(1+r)/(1+g) − pb', "Parametri inseriti dall'utente", 'Modello contabile']) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
    expect(screen.getByText(/1,3% del PIL/)).toBeInTheDocument();
  });

  it('submits a debt simulation with an explicit rate shock', async () => {
    const { calls } = mockApi({ 'GET /api/notifications': [], 'GET /api/lab/simulations': [], 'GET /api/finance/series': [], 'POST /api/lab/simulations/debt': sim, 'GET /api/lab/simulations/9': sim });
    renderApp('/lab');
    await userEvent.click(await screen.findByRole('button', { name: /Esegui/ }));
    expect(await screen.findByRole('note')).toBeInTheDocument();
    const body = calls.find((c) => c.method === 'POST')?.body as Record<string, unknown>;
    expect(body).toMatchObject({ d0: 135, rate_shock: 0.01, crisis: null, stochastic: null, counterfactual: false });
  });

  it('runs a sector model with base, optimistic and pessimistic scenarios', async () => {
    const out: SimulationRun = { ...sim, id: 11, kind: 'employment', counterfactual: false, result: { ...sim.result, kind: 'employment', counterfactual: false, label: 'Simulazione', warnings: [],
      results: { years: [0, 1], headline: 'Occupati', unit: 'milioni',
        scenarios: { Base: { Occupati: [24, 24.1] }, Ottimistico: { Occupati: [24, 24.3] }, Pessimistico: { Occupati: [24, 23.8] } },
        comparison: [{ scenario: 'Base', key: 'base', end_value: 24.1, delta_vs_base: 0, changed: {} }, { scenario: 'Ottimistico', key: 'optimistic', end_value: 24.3, delta_vs_base: 0.2, changed: { gdp_growth: 0.02 } },
          { scenario: 'Pessimistico', key: 'pessimistic', end_value: 23.8, delta_vs_base: -0.3, changed: { gdp_growth: -0.01 } }] } } };
    const { calls } = mockApi({ 'GET /api/notifications': [], 'GET /api/lab/simulations': [], 'GET /api/finance/series': [], 'POST /api/lab/simulations/employment': out, 'GET /api/lab/simulations/11': out });
    renderApp('/lab');
    await userEvent.selectOptions(await screen.findByLabelText('Tipo di analisi'), 'employment');
    for (const [label, v] of [['Forze di lavoro iniziali', '25.9'], ['Disoccupazione iniziale', '0.07'], ['Crescita del PIL reale', '0.01'], ['Crescita potenziale', '0.007'], ['Coefficiente di Okun (β)', '0.4'], ['Crescita forze di lavoro', '0']]) {
      await userEvent.type(screen.getByLabelText(label), v);
    }
    await userEvent.type(screen.getByLabelText(/Scenario ottimistico/), 'gdp_growth: 0.02');
    await userEvent.type(screen.getByLabelText(/Scenario pessimistico/), 'gdp_growth: -0.01');
    await userEvent.click(screen.getByRole('button', { name: /Esegui/ }));
    expect(await screen.findByTestId('scenario-comparison')).toHaveTextContent('gdp_growth=0.02');
    const body = calls.find((c) => c.method === 'POST')?.body as Record<string, unknown>;
    expect(body).toMatchObject({ labour_force0: 25.9, okun_beta: 0.4, years: 10, optimistic: { gdp_growth: 0.02 }, pessimistic: { gdp_growth: -0.01 } });
  });
});
