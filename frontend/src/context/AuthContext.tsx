/* ── Auth React Context ──────────────────────────────── */

import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useAuth, type UseAuthReturn } from '../hooks/useAuth';

const AuthContext = createContext<UseAuthReturn | null>(null);

interface AuthProviderProps {
  children: ReactNode;
  /** Auto-login anonymously on mount if no token exists (default: true) */
  autoLogin?: boolean;
}

/**
 * Provides authentication state and actions to the entire app.
 *
 * On mount, if ``autoLogin`` is true and no token is found in sessionStorage,
 * it automatically mints an anonymous session.
 */
export function AuthProvider({ children, autoLogin = true }: AuthProviderProps) {
  const auth = useAuth();

  // Auto-login anonymously if no token exists
  useEffect(() => {
    if (autoLogin && !auth.loading && !auth.token && !auth.error) {
      auth.loginAnonymous();
    }
  }, [autoLogin, auth.loading, auth.token, auth.error, auth.loginAnonymous]);

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
