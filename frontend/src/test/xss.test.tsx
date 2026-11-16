import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { safeHref } from '../lib/safeUrl';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const XSS = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=2</script>';

describe('anti-XSS', () => {
  it('accepts only http(s) links', () => {
    expect(safeHref('https://fred.stlouisfed.org/x')).toBe('https://fred.stlouisfed.org/x');
    for (const bad of ['javascript:alert(1)', ' JaVaScRiPt:alert(1)', 'data:text/html,<script>', 'vbscript:x', '//evil.example', '/relativo']) expect(safeHref(bad)).toBeUndefined();
  });

  it('renders stored text fields as text, never as HTML', async () => {
    mockApi({
      'GET /api/notifications': [], 'GET /api/projects': [], 'GET /api/projects/linked/source/1': [],
      'GET /api/sources': [{ id: 1, title: XSS, citation: XSS, authors: [XSS], verification_status: 'unverified', verification_note: XSS, provenance: XSS, license: XSS }],
    });
    renderApp('/bibliography');
    expect((await screen.findAllByText(XSS, { exact: false })).length).toBeGreaterThan(0);
    expect(document.querySelector('img[src="x"]')).toBeNull();
    expect(document.querySelector('main script')).toBeNull();
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });
});
