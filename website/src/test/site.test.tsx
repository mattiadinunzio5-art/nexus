import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MODULES, MODULES_BY_SLUG } from '../content/modules';
import { CASE_STUDY, CAPABILITIES, WORKFLOW } from '../content/story';
import { passwordProblems, EMAIL_RX } from '../lib/auth';
import { App } from '../App';
import { PAGES, renderHead } from '../../seo.config';

describe('content', () => {
  it('has 12 complete modules', () => {
    expect(MODULES).toHaveLength(12);
    for (const m of MODULES) {
      expect(m.description.length).toBeGreaterThan(40);
      expect(m.mainFunction).toBeTruthy();
      expect(m.whyUseful.length).toBeGreaterThan(0);
      expect(m.guide.length).toBeGreaterThan(0);
      expect(m.inputs.length).toBeGreaterThan(0);
      expect(m.outputs.length).toBeGreaterThan(0);
      expect(m.example.steps.length).toBeGreaterThan(0);
      expect(m.connections.length).toBeGreaterThan(0);
      for (const c of m.connections) expect(MODULES_BY_SLUG[c.slug]).toBeDefined();
    }
  });
  it('workflow, case study and capabilities match the spec', () => {
    expect(WORKFLOW).toHaveLength(11);
    expect(CASE_STUDY).toHaveLength(9);
    expect(CAPABILITIES).toHaveLength(7);
    for (const s of [...WORKFLOW, ...CASE_STUDY, ...CAPABILITIES]) expect(MODULES_BY_SLUG[s.slug]).toBeDefined();
  });
  it('contains no placeholder text', () => {
    expect(JSON.stringify([MODULES, WORKFLOW, CASE_STUDY, CAPABILITIES])).not.toMatch(/lorem|ipsum|TODO/i);
  });
});

describe('auth helpers', () => {
  it('validates email and password', () => {
    expect(EMAIL_RX.test('a@b.co')).toBe(true);
    expect(EMAIL_RX.test('nope')).toBe(false);
    expect(passwordProblems('short1')).not.toHaveLength(0);
    expect(passwordProblems('onlyletterslong')).not.toHaveLength(0);
    expect(passwordProblems('goodpassword7')).toHaveLength(0);
  });
});

describe('seo', () => {
  it('has a page per module and renders head', () => {
    expect(PAGES.filter((p) => p.path.startsWith('/architecture/'))).toHaveLength(12);
    const html = '<title>x</title><meta name="description" content="y"><meta property="og:title" content="t"><meta property="og:description" content="d"></head>';
    const out = renderHead(html, PAGES[1], 'https://example.com');
    expect(out).toContain(`<title>${PAGES[1].title.replace(/&/g, '&amp;')}</title>`);
    expect(out).toContain('https://example.com' + PAGES[1].path);
  });
});

describe('routes', () => {
  const at = (path: string) => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
  it('home shows hero and honest access state without Supabase', async () => {
    at('/');
    expect(await screen.findByText(/Online registration is not open yet/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Into Intelligence/i).length).toBeGreaterThan(0);
  });
  it('module page renders', async () => {
    at('/architecture/time-machine');
    expect(await screen.findByRole('heading', { level: 1, name: /Time Machine/i })).toBeInTheDocument();
  });
  it('unknown route shows 404', async () => {
    at('/does-not-exist');
    expect(await screen.findByText(/404|not found/i)).toBeInTheDocument();
  });
});
