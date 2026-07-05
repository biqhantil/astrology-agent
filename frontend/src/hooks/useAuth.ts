/* ── Auth hook: anonymous login, token management ────── */

import { useState, useEffect, useCallback } from 'react';
import { get, post, setToken, getToken, clearToken } from '../api/client';
import type {
  AnonymousLoginResponse,
  UserPublic,
  SessionResponse,
} from '../types';

interface AuthState {
  /** JWT access token, or null if not authenticated */
  token: string | null;
  /** Decoded /me user data, or null before loaded */
  user: UserPublic | null;
  /** Loading state for initial auth check */
  loading: boolean;
  /** Error message, if any */
  error: string | null;
}

interface AuthActions {
  /** Mint a new anonymous session */
  loginAnonymous: () => Promise<void>;
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
 * On mount, checks sessionStorage for an existing JWT and validates
 * it via ``GET /v1/auth/session``.
 */
export function useAuth(): UseAuthReturn {
  const [token, setTokenState] = useState<string | null>(getToken());
  const [user, setUser] = useState<UserPublic | null>(null);
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
        // Validate token by hitting session endpoint
        const session = await get<SessionResponse>('/v1/auth/session');
        if (session.user_id) {
          // Fetch user profile
          const userData = await get<UserPublic>('/v1/me');
          setUser(userData);
          setTokenState(existing);
        }
      } catch {
        // Token invalid/expired — clear it
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

      // Fetch user profile
      const userData = await get<UserPublic>('/v1/me');
      setUser(userData);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Anonymous login failed';
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
  }, []);

  const checkSession = useCallback(async (): Promise<boolean> => {
    const existing = getToken();
    if (!existing) return false;
    try {
      await get<SessionResponse>('/v1/auth/session');
      return true;
    } catch {
      clearToken();
      setTokenState(null);
      setUser(null);
      return false;
    }
  }, []);

  return {
    token,
    user,
    loading,
    error,
    loginAnonymous,
    refreshUser,
    logout,
    checkSession,
  };
}
