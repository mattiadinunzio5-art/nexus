import { describe, expect, it } from 'vitest';
import { reproducibility } from '../pages/Lab';

describe('riproducibilità delle simulazioni', () => {
  it('lists seed, generator, numpy version and data fingerprints', () => {
    expect(reproducibility({ seed: 11, generator: 'numpy.random.default_rng (PCG64)', numpy: '2.5.4', data: { Prezzo: 'abc123' }, note: 'Stessi parametri' }))
      .toEqual(['Seme 11 · numpy.random.default_rng (PCG64)', 'numpy 2.5.4', 'Impronta dei dati «Prezzo»: abc123', 'Stessi parametri']);
    expect(reproducibility(undefined)).toEqual([]);
  });
});
