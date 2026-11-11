import { AnimatePresence, motion, MotionConfig } from 'framer-motion';
import { Route, Routes, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ScrollManager } from './components/ScrollManager';
import { AuthProvider } from './lib/auth';
import { Home } from './pages/Home';
import { lazy, Suspense } from 'react';
import { useI18n } from './lib/i18n';

// Le pagine secondarie si caricano solo quando servono.
const ModulePage = lazy(() => import('./pages/ModulePage').then((m) => ({ default: m.ModulePage })));
const Privacy = lazy(() => import('./pages/Privacy').then((m) => ({ default: m.Privacy })));
const DataPolicy = lazy(() => import('./pages/DataPolicy').then((m) => ({ default: m.DataPolicy })));
const NotFound = lazy(() => import('./pages/NotFound').then((m) => ({ default: m.NotFound })));
const auth = () => import('./pages/Auth');
const SignIn = lazy(() => auth().then((m) => ({ default: m.SignIn })));
const SignUp = lazy(() => auth().then((m) => ({ default: m.SignUp })));
const ForgotPassword = lazy(() => auth().then((m) => ({ default: m.ForgotPassword })));
const ResetPassword = lazy(() => auth().then((m) => ({ default: m.ResetPassword })));
const Account = lazy(() => auth().then((m) => ({ default: m.Account })));
const RequireAuth = lazy(() => auth().then((m) => ({ default: m.RequireAuth })));
const cases = () => import('./pages/Cases');
const CasesPage = lazy(() => cases().then((m) => ({ default: m.CasesPage })));
const CaseArticlePage = lazy(() => cases().then((m) => ({ default: m.CaseArticlePage })));

/** Stesse pagine in inglese (/) e in italiano (/it). */
const PAGES: [string, React.ReactNode][] = [
  ['', <Home />],
  ['/architecture/:slug', <ModulePage />],
  ['/cases', <CasesPage />],
  ['/cases/:slug', <CaseArticlePage />],
  ['/signin', <SignIn />],
  ['/signup', <SignUp />],
  ['/forgot-password', <ForgotPassword />],
  ['/reset-password', <ResetPassword />],
  ['/account', <RequireAuth><Account /></RequireAuth>],
  ['/privacy', <Privacy />],
  ['/data-policy', <DataPolicy />],
];

function SkipLink() {
  const { t } = useI18n();
  return <a href="#main" className="sr-only z-[60] rounded bg-ivory px-3 py-2 text-void focus:not-sr-only focus:fixed focus:left-3 focus:top-3">{t.skip}</a>;
}

export function App() {
  const location = useLocation();
  return (
    <MotionConfig reducedMotion="user">
      <AuthProvider>
        <SkipLink />
        <ScrollManager />
        <Navbar />
        <AnimatePresence mode="wait">
          <motion.main
            id="main"
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
          >
            <Suspense fallback={<div className="min-h-[100svh] bg-void" />}>
            <Routes location={location}>
              {PAGES.flatMap(([path, el]) => [
                <Route key={path || '/'} path={path || '/'} element={el} />,
                <Route key={`/it${path}`} path={`/it${path}`} element={el} />,
              ])}
              <Route path="*" element={<NotFound />} />
            </Routes>
            </Suspense>
          </motion.main>
        </AnimatePresence>
        <Footer />
      </AuthProvider>
    </MotionConfig>
  );
}
