/* ── Auth hook: anonymous, dev, google auth ──────────── */

import { useState, useEffect, useCallback } from 'react';
import { get, post, setToken, getToken, clearToken } from '../api/client';
import type {
  AnonymousLoginResponse,
  DevLoginResponse,
  GoogleLoginResponse,
  UserPublic,
  SessionResponse,
  AuthProvider,
} from '../types';

interface AuthState {
  /** JWT access token, or null if not authenticated */
  token: string | null;
  /** Decoded /me user data, or null before loaded */
  user: UserPublic | null;
  /** Which provider was used to authenticate */
  authProvider: AuthProvider | null;
  /** Loading state for initial auth check */
  loading: boolean;
  /** Error message, if any */
  error: string | null;
}

interface AuthActions {
  /** Mint a new anonymous session */
  loginAnonymous: () => Promise<void>;
  /** Log in as the dev preset user (only works when AUTH_DEV_MODE_ENABLED) */
  loginDev: () => Promise<void>;
  /** Authenticate with a Google credential token */
  loginGoogle: (credential: string) => Promise<void>;
  /** Refresh user data from /v1/me */
  refreshUser: () => Promise<void>;
  /** Clear the session */
  logout: () => void;
  /** Check if the current token is still valid */
  checkSession: () => Promise<boolean>;
}

export type UseAuthReturn = AuthState & AuthActions;

/**
 * Hook for authentication state and actions.
 *
 * Supports three auth providers:
 * - ``anonymous`` — auto-created on first visit
 * - ``dev`` — fixed preset user for local development (configurable)
 * - ``google`` — Google Identity Services (production / mocked in dev)
 *
 * On mount, checks sessionStorage for an existing JWT and validates
 * it via ``GET /v1/auth/session``.
 */
export function useAuth(): UseAuthReturn {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [user, setUser] = useState<UserPublic | null>(null);
  const [authProvider, setAuthProvider] = useState<AuthProvider | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // On mount, validate existing token and fetch user
  useEffect(() => {
    const init = async () => {
      const existing = getToken();
      if (!existing) {
        setLoading(false);
        return;
      }
      try {
        const session = await get<SessionResponse>('/v1/auth/session');
        if (session.user_id) {
          const userData = await get<UserPublic>('/v1/me');
          setUser(userData);
          setTokenState(existing);
          setAuthProvider((session.auth_provider ?? 'anonymous') as AuthProvider);
        }
      } catch {
        clearToken();
        setTokenState(null);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const loginAnonymous = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await post<AnonymousLoginResponse>('/v1/auth/anonymous');
      setToken(res.access_token);
      setTokenState(res.access_token);
      setAuthProvider('anonymous');

      const userData = await get<UserPublic>('/v1/me');
      setUser(userData);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Anonymous login failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const loginDev = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await post<DevLoginResponse>('/v1/auth/dev-login');
      setToken(res.access_token);
      setTokenState(res.access_token);
      setAuthProvider('dev');

      // Update local user state with dev identity
      setUser({
        id: res.user_id,
        display_name: res.display_name,
        locale: 'en',
        created_at: new Date().toISOString(),
        last_active_at: new Date().toISOString(),
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Dev login failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const loginGoogle = useCallback(async (credential: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await post<GoogleLoginResponse>('/v1/auth/google', { credential });
      setToken(res.access_token);
      setTokenState(res.access_token);
      setAuthProvider('google');

      setUser({
        id: res.user_id,
        display_name: res.display_name,
        email: res.email,
        locale: 'en',
        created_at: new Date().toISOString(),
        last_active_at: new Date().toISOString(),
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Google login failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await get<UserPublic>('/v1/me');
      setUser(userData);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to refresh user';
      setError(msg);
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setUser(null);
    setAuthProvider(null);
  }, []);

  const checkSession = useCallback(async (): Promise<boolean> => {
    const existing = getToken();
    if (!existing) return false;
    try {
      const session = await get<SessionResponse>('/v1/auth/session');
      setAuthProvider((session.auth_provider ?? 'anonymous') as AuthProvider);
      return true;
    } catch {
      clearToken();
      setTokenState(null);
      setUser(null);
      setAuthProvider(null);
      return false;
    }
  }, []);

  return {
    token,
    user,
    authProvider,
    loading,
    error,
    loginAnonymous,
    loginDev,
    loginGoogle,
    refreshUser,
    logout,
    checkSession,
  };
}
