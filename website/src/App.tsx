import { AnimatePresence, motion, MotionConfig } from 'framer-motion';
import { Route, Routes, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ScrollManager } from './components/ScrollManager';
import { AuthProvider } from './lib/auth';
import { Home } from './pages/Home';
import { lazy, Suspense } from 'react';

// Le pagine secondarie si caricano solo quando servono.
const ModulePage = lazy(() => import('./pages/ModulePage').then((m) => ({ default: m.ModulePage })));
const NotFound = lazy(() => import('./pages/NotFound').then((m) => ({ default: m.NotFound })));
const auth = () => import('./pages/Auth');
const SignIn = lazy(() => auth().then((m) => ({ default: m.SignIn })));
const SignUp = lazy(() => auth().then((m) => ({ default: m.SignUp })));
const ForgotPassword = lazy(() => auth().then((m) => ({ default: m.ForgotPassword })));
const ResetPassword = lazy(() => auth().then((m) => ({ default: m.ResetPassword })));
const Account = lazy(() => auth().then((m) => ({ default: m.Account })));
const RequireAuth = lazy(() => auth().then((m) => ({ default: m.RequireAuth })));

export function App() {
  const location = useLocation();
  return (
    <MotionConfig reducedMotion="user">
      <AuthProvider>
        <a href="#main" className="sr-only z-[60] rounded bg-ivory px-3 py-2 text-void focus:not-sr-only focus:fixed focus:left-3 focus:top-3">Skip to content</a>
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
              <Route path="/" element={<Home />} />
              <Route path="/architecture/:slug" element={<ModulePage />} />
              <Route path="/signin" element={<SignIn />} />
              <Route path="/signup" element={<SignUp />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/account" element={<RequireAuth><Account /></RequireAuth>} />
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
