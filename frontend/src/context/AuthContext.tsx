/* ── Auth React Context ──────────────────────────────── */

import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useAuth, type UseAuthReturn } from '../hooks/useAuth';

const AuthContext = createContext<UseAuthReturn | null>(null);

interface AuthProviderProps {
  children: ReactNode;
  /** Auto-login anonymously on mount if no token exists (default: true) */
  autoLogin?: boolean;
  /** Use the dev preset user instead of anonymous (default reads VITE_AUTH_DEV_MODE) */
  devMode?: boolean;
}

/**
 * Provides authentication state and actions to the entire app.
 *
 * Auth strategy (first-match wins):
 * 1. If a valid token already exists in sessionStorage, restore the session.
 * 2. If ``devMode`` is true, log in as the dev preset user.
 * 3. If ``autoLogin`` is true, mint an anonymous session.
 *
 * ``devMode`` defaults to ``VITE_AUTH_DEV_MODE`` env var (``"true"`` / ``"false"``).
 * Set ``VITE_AUTH_DEV_MODE=false`` to disable the dev preset and force
 * production-like auth flow.
 */
export function AuthProvider({
  children,
  autoLogin = true,
  devMode = import.meta.env.VITE_AUTH_DEV_MODE !== 'false',
}: AuthProviderProps) {
  const auth = useAuth();

  const shouldDevLogin = devMode && autoLogin;
  const shouldAnonymous = !devMode && autoLogin;

  // Auto-login as dev preset or anonymous if no token exists
  useEffect(() => {
    if (auth.loading || auth.token || auth.error) return;

    if (shouldDevLogin) {
      auth.loginDev();
    } else if (shouldAnonymous) {
      auth.loginAnonymous();
    }
  }, [
    shouldDevLogin,
    shouldAnonymous,
    auth.loading,
    auth.token,
    auth.error,
    auth.loginDev,
    auth.loginAnonymous,
  ]);

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth context.
 * Must be used within an ``AuthProvider``.
 */
export function useAuthContext(): UseAuthReturn {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return ctx;
}
