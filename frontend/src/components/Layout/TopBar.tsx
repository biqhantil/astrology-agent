/* ── Top navigation bar ──────────────────────────────── */

import type { FC } from 'react';
import { useAuthContext } from '../../context/AuthContext';
import { clearToken } from '../../api/client';
import { useI18n } from '../../i18n/I18nContext';
import { LOCALES, LOCALE_LABEL, type Locale } from '../../i18n';

const PROVIDER_COLOR: Record<string, string> = {
  dev: 'bg-amber-600/20 text-amber-400',
  google: 'bg-blue-600/20 text-blue-400',
  anonymous: 'bg-gray-600/20 text-gray-400',
};

/**
 * Top bar with branding, language switcher, and auth controls.
 */
const TopBar: FC = () => {
  const { user, loading, authProvider, logout } = useAuthContext();
  const { t, locale, setLocale } = useI18n();

  const providerLabel = (p: string) => {
    if (p === 'dev') return t('auth.providerDev');
    if (p === 'google') return t('auth.providerGoogle');
    if (p === 'anonymous') return t('auth.providerAnon');
    return p;
  };

  const handleReset = () => {
    clearToken();
    window.location.reload();
  };

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-zinc-800/30 bg-black/80 backdrop-blur-sm shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl" role="img" aria-label={t('app.name')}>
            ♄
          </span>
          <h1 className="text-base font-semibold text-zinc-100 tracking-tight hidden sm:block">
            {t('app.name')}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-1.5 text-zinc-500">
          <span className="text-[10px] uppercase tracking-wider hidden sm:inline">
            {t('app.language')}
          </span>
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
            className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-[12px] rounded px-2 py-1 focus:outline-none focus:border-amber-500/40 cursor-pointer"
            aria-label={t('app.language')}
          >
            {LOCALES.map((code) => (
              <option key={code} value={code}>
                {LOCALE_LABEL[code]}
              </option>
            ))}
          </select>
        </label>

        {loading ? (
          <div className="w-20 h-5 rounded bg-zinc-800 animate-pulse" />
        ) : user ? (
          <div className="flex items-center gap-2">
            {authProvider && (
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${PROVIDER_COLOR[authProvider] ?? 'bg-zinc-600/20 text-zinc-400'}`}
              >
                {providerLabel(authProvider)}
              </span>
            )}
            <span className="text-sm text-zinc-400 hidden sm:inline">
              {user.display_name ?? t('app.anonymousUser')}
            </span>
            <button
              onClick={handleReset}
              className="btn-ghost text-[10px]"
              title={t('app.resetTitle')}
            >
              {t('app.reset')}
            </button>
            <button onClick={logout} className="btn-ghost text-xs" title={t('app.logoutTitle')}>
              {t('app.exit')}
            </button>
          </div>
        ) : (
          <span className="text-sm text-zinc-500">{t('app.notConnected')}</span>
        )}
      </div>
    </header>
  );
};

export default TopBar;
