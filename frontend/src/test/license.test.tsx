import { screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import type { LicenseRegistry } from '../api/types';
import { _resetLicenseCache } from '../components/License';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const registry: LicenseRegistry = {
  version: '1.0', updated: '2026-11-11', library_licenses: ['world_bank_wdi'],
  licenses: [{
    id: 'world_bank_wdi', name: 'World Development Indicators', publisher: 'World Bank', homepage: 'https://data.worldbank.org',
    applies_to: 'Biblioteca: serie annuali per paese.', license: 'Creative Commons Attribution 4.0 International (CC BY 4.0)',
    license_url: 'https://creativecommons.org/licenses/by/4.0/', attribution: 'Obbligatoria: «World Bank, World Development Indicators».',
    commercial: 'yes', commercial_note: 'Consentito con attribuzione.', redistribution: 'yes', redistribution_note: 'Consentita con attribuzione.',
    territorial: 'Nessuna limitazione territoriale indicata dalla fonte.', modifications: 'Nessuna modifica dei valori.',
    terms_url: 'https://datacatalog.worldbank.org/search/dataset/0037712', verified_on: '2026-11-11', status: 'verified', notes: '',
    library_counts: { series: 2843 },
  }],
};

describe('copyright & data policy', () => {
  beforeEach(() => _resetLicenseCache());

  it('lists every source with the nine policy fields and the library counts', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/licenses': registry });
    renderApp('/data-policy');
    expect(await screen.findByRole('heading', { name: 'Copyright & Data Policy' })).toBeInTheDocument();
    const card = (await screen.findByText('World Development Indicators')).closest('section')!;
    expect(within(card).getByText('Attribuzione obbligatoria')).toBeInTheDocument();
    expect(within(card).getByText('Uso commerciale')).toBeInTheDocument();
    expect(within(card).getByText('Limitazioni territoriali')).toBeInTheDocument();
    expect(within(card).getByText('Modifiche effettuate da NEXUS')).toBeInTheDocument();
    expect(within(card).getByText(/2\.?843 serie/)).toBeInTheDocument();
    expect(within(card).getByRole('link', { name: /CC BY 4\.0/ })).toHaveAttribute('href', 'https://creativecommons.org/licenses/by/4.0/');
  });
});
