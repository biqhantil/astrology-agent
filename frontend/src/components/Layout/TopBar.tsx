/* ── Top navigation bar ──────────────────────────────── */

import type { FC } from 'react';
import { useAuthContext } from '../../context/AuthContext';

/**
 * Top bar with app branding, user info, and actions.
 *
 * Left: App logo/name
 * Right: User display name or login prompt
 */
const TopBar: FC = () => {
  const { user, loading, logout } = useAuthContext();

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm shrink-0">
      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl" role="img" aria-label="Astrology">
            ♄
          </span>
          <h1 className="text-base font-semibold text-gray-100 tracking-tight hidden sm:block">
            Astrology Agent
          </h1>
        </div>
      </div>

      {/* Right: User */}
      <div className="flex items-center gap-3">
        {loading ? (
          <div className="w-20 h-5 rounded bg-gray-800 animate-pulse" />
        ) : user ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400 hidden sm:inline">
              {user.display_name ?? 'Anonymous User'}
            </span>
            <button
              onClick={logout}
              className="btn-ghost text-xs"
              title="Log out"
            >
              Exit
            </button>
          </div>
        ) : (
          <span className="text-sm text-gray-500">Not connected</span>
        )}
      </div>
    </header>
  );
};

export default TopBar;
