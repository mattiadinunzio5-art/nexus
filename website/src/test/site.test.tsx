import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MODULES, MODULES_BY_SLUG } from '../content/modules';
import { CASE_STUDY, CAPABILITIES, WORKFLOW } from '../content/story';
import { passwordProblems, EMAIL_RX } from '../lib/auth';
import { App } from '../App';
import { PAGES, renderHead } from '../../seo.config';
import { MODULES_IT } from '../content/modules.it';
import { CASE_STUDY_IT, CAPABILITIES_IT, WORKFLOW_IT } from '../content/story.it';
import { CASES } from '../content/cases';
import { STRINGS } from '../lib/strings';
import { counterpart, localize } from '../lib/i18n';

describe('content', () => {
  it('has 12 complete modules', () => {
    expect(MODULES).toHaveLength(13);
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
    expect(CAPABILITIES).toHaveLength(8);
    for (const s of [...WORKFLOW, ...CASE_STUDY, ...CAPABILITIES]) expect(MODULES_BY_SLUG[s.slug]).toBeDefined();
  });
  it('contains no placeholder text', () => {
    expect(JSON.stringify([MODULES, WORKFLOW, CASE_STUDY, CAPABILITIES])).not.toMatch(/lorem|ipsum|TODO/i);
  });
});

describe('italian version', () => {
  it('mirrors the english content exactly in structure', () => {
    expect(MODULES_IT.map((m) => m.slug)).toEqual(MODULES.map((m) => m.slug));
    MODULES_IT.forEach((m, i) => {
      const en = MODULES[i];
      expect(m.visual).toBe(en.visual);
      expect(m.connections.map((c) => c.slug)).toEqual(en.connections.map((c) => c.slug));
      expect(m.guide.length).toBe(en.guide.length);
      expect(m.limits.length).toBe(en.limits.length);
    });
    expect(WORKFLOW_IT.map((w) => w.slug)).toEqual(WORKFLOW.map((w) => w.slug));
    expect(CASE_STUDY_IT.map((w) => w.slug)).toEqual(CASE_STUDY.map((w) => w.slug));
    expect(CAPABILITIES_IT.map((w) => w.slug)).toEqual(CAPABILITIES.map((w) => w.slug));
    const keys = (o: object): string[] => Object.entries(o).flatMap(([k, v]) => (v && typeof v === 'object' && !Array.isArray(v) ? keys(v).map((x) => `${k}.${x}`) : [k]));
    expect(keys(STRINGS.it)).toEqual(keys(STRINGS.en));
    for (const c of CASES) expect(c.it.sections.length).toBe(c.en.sections.length);
  });
  it('maps paths between languages', () => {
    expect(localize('/#vision', 'it')).toBe('/it#vision');
    expect(localize('/', 'it')).toBe('/it');
    expect(counterpart('/it/architecture/documents', '')).toBe('/architecture/documents');
    expect(counterpart('/', '#access')).toBe('/it#access');
    expect(counterpart('/it', '')).toBe('/');
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
    expect(PAGES.filter((p) => p.path.startsWith('/architecture/'))).toHaveLength(13);
    expect(PAGES.filter((p) => p.path.startsWith('/it/architecture/'))).toHaveLength(13);
    const itHome = renderHead('<html lang="en"><head><title>x</title></head>', PAGES.find((p) => p.path === '/it')!, 'https://example.com');
    expect(itHome).toContain('<html lang="it">');
    expect(itHome).toContain('hreflang="en" href="https://example.com/"');
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
  it('italian home and module page render in italian', async () => {
    at('/it');
    expect(await screen.findByText(/La registrazione online non è ancora aperta/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /English/ })).toHaveAttribute('href', '/');
  });
  it('italian module page', async () => {
    at('/it/architecture/bibliography');
    expect(await screen.findByRole('heading', { level: 1, name: /Bibliografia/ })).toBeInTheDocument();
    expect(screen.getByText('Funzione principale')).toBeInTheDocument();
  });
  it('cases list and article', async () => {
    at('/cases/reading-2008-without-hindsight');
    expect(await screen.findByRole('heading', { level: 1, name: /Reading 2008 without hindsight/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /ALFRED/ })).toHaveAttribute('href', 'https://alfred.stlouisfed.org/');
  });
  it('unknown route shows 404', async () => {
    at('/does-not-exist');
    expect(await screen.findByText(/404|not found/i)).toBeInTheDocument();
  });
});
